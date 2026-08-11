# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt

PROPERTIES_ITEM_GROUP = "Properties"
ITEM_PREFIX = "PRP-"
DEFAULT_PRICE_LIST = "Standard Selling"


def sync_property_to_shop(doc, method=None):
	"""Hook: Property.after_save"""
	if cint(doc.get("is_group")):
		return
	try:
		if cint(doc.get("publish_on_shop")):
			_publish(doc)
		else:
			_unpublish(doc)
	except Exception:
		frappe.log_error(
			title="PropMS Shop Bridge Error",
			message=frappe.get_traceback(),
		)
		frappe.msgprint(
			_("Property saved, but the shop listing could not be updated. See Error Log for details."),
			alert=True,
		)


def unpublish_property(doc, method=None):
	"""Hook: Property.after_delete"""
	if not _webshop_installed():
		return
	web_item = frappe.db.exists("Website Item", {"item_code": _item_code_for(doc)})
	if not web_item:
		return
	try:
		frappe.delete_doc("Website Item", web_item, force=1, ignore_permissions=True)
	except Exception:
		frappe.log_error(
			title="PropMS Shop Bridge Error",
			message=frappe.get_traceback(),
		)


def _publish(doc):
	if not _webshop_installed():
		return
	_ensure_item_group(PROPERTIES_ITEM_GROUP)
	item = _get_or_create_item(doc)
	_set_selling_price(item.name, doc.get("shop_price"))
	_publish_on_website(item, doc)


def _unpublish(doc):
	if not _webshop_installed():
		return
	web_item = frappe.db.exists("Website Item", {"item_code": _item_code_for(doc)})
	if web_item:
		frappe.db.set_value("Website Item", web_item, "published", 0)


def _item_code_for(doc):
	name = cstr(doc.get("name1")) or cstr(doc.name)
	return "{0}{1}".format(ITEM_PREFIX, name)


def _webshop_installed():
	return bool(
		frappe.db.exists("DocType", "Website Item")
		and frappe.db.exists("DocType", "Webshop Settings")
	)


def _ensure_item_group(item_group):
	if frappe.db.exists("Item Group", item_group):
		return
	try:
		from frappe.utils.nestedset import get_root_of

		parent = get_root_of("Item Group")
	except Exception:
		parent = "All Item Groups"
	doc = frappe.new_doc("Item Group")
	doc.item_group_name = item_group
	doc.parent_item_group = parent or "All Item Groups"
	doc.is_group = 0
	doc.flags.ignore_permissions = True
	doc.insert()


def _get_or_create_item(doc):
	item_code = _item_code_for(doc)
	item = None
	if frappe.db.exists("Item", item_code):
		item = frappe.get_doc("Item", item_code)
	else:
		item = frappe.new_doc("Item")
		item.item_code = item_code
		item.item_name = cstr(doc.get("name1")) or item_code
		item.item_group = PROPERTIES_ITEM_GROUP
		item.is_sales_item = 1
		item.is_stock_item = 0
		item.stock_uom = "Nos"
		item.description = cstr(doc.get("description")) or cstr(item.item_name)
	image = cstr(doc.get("shop_image") or doc.get("photo"))
	if image:
		item.image = image
	item.flags.ignore_permissions = True
	item.save()
	return item


def _set_selling_price(item_code, rate):
	rate = flt(rate)
	if rate <= 0:
		return
	price_list = _get_price_list()
	if frappe.db.exists(
		"Item Price", {"item_code": item_code, "price_list": price_list}
	):
		ip = frappe.get_doc(
			"Item Price", {"item_code": item_code, "price_list": price_list}
		)
		if flt(ip.price_list_rate) != rate:
			ip.price_list_rate = rate
			ip.flags.ignore_permissions = True
			ip.save()
		return
	ip = frappe.new_doc("Item Price")
	ip.item_code = item_code
	ip.price_list = price_list
	ip.price_list_rate = rate
	ip.flags.ignore_permissions = True
	ip.insert()


def _get_price_list():
	price_list = None
	if frappe.db.exists("DocType", "Webshop Settings"):
		price_list = frappe.db.get_single_value("Webshop Settings", "price_list")
	if not price_list and frappe.db.exists("DocType", "E Commerce Settings"):
		price_list = frappe.db.get_single_value("E Commerce Settings", "price_list")
	return price_list or DEFAULT_PRICE_LIST


def _publish_on_website(item, doc):
	existing = frappe.db.exists("Website Item", {"item_code": item.name})
	if existing:
		web_item = frappe.get_doc("Website Item", existing)
	else:
		from webshop.webshop.doctype.website_item.website_item import make_website_item

		web_item = make_website_item(item, save=False)
	web_item.web_item_name = cstr(item.item_name)
	web_item.published = 1
	if doc.get("shop_warehouse"):
		web_item.website_warehouse = doc.get("shop_warehouse")
	if doc.get("description"):
		web_item.web_long_description = cstr(doc.get("description"))
		if not web_item.short_description:
			web_item.short_description = cstr(doc.get("description"))[:280]
	image = cstr(item.image or item.website_image)
	if image:
		web_item.website_image = image
	_ensure_website_item_group_row(web_item, PROPERTIES_ITEM_GROUP)
	web_item.flags.ignore_permissions = True
	web_item.save()


def _ensure_website_item_group_row(web_item, item_group):
	existing = [
		row for row in (web_item.get("website_item_groups") or [])
		if row.item_group == item_group
	]
	if existing:
		return
	web_item.append("website_item_groups", {"item_group": item_group})
