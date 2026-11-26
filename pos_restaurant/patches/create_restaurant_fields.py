# Copyright (c) 2026, pos-restaurant and contributors
# For license information, please see license.txt

import frappe

CUSTOM_FIELDS = [
	{"dt": "POS Profile", "fieldname": "custom_restaurant_mode", "label": "Restaurant Mode", "fieldtype": "Check", "insert_after": "disabled"},
	{"dt": "POS Profile", "fieldname": "tip_account", "label": "Cuenta de propina", "fieldtype": "Link", "options": "Account"},
	{"dt": "Item", "fieldname": "custom_kitchen_item", "label": "Kitchen Item", "fieldtype": "Check", "insert_after": "is_sales_item"},
	{"dt": "Item", "fieldname": "custom_preparation_options", "label": "Preparation Options", "fieldtype": "Code", "options": "JSON", "insert_after": "custom_kitchen_item", "description": "JSON array of preparation toggles"},
	{"dt": "Item", "fieldname": "custom_restaurant_modifier_groups", "label": "Restaurant Modifier Groups", "fieldtype": "Table", "options": "Restaurant Item Modifier Group", "insert_after": "custom_preparation_options"},
	{"dt": "Sales Invoice", "fieldname": "custom_tip_amount", "label": "Propina", "fieldtype": "Currency"},
	{"dt": "Sales Invoice", "fieldname": "custom_table", "label": "Mesa", "fieldtype": "Link", "options": "Restaurant Table"},
	{"dt": "Sales Invoice", "fieldname": "custom_table_session", "label": "Sesion de mesa", "fieldtype": "Link", "options": "Table Session"},
	{"dt": "Sales Invoice Item", "fieldname": "custom_restaurant_modifiers", "label": "Restaurant Modifiers", "fieldtype": "Code", "options": "JSON", "insert_after": "item_name"},
]


def execute():
	for cf in CUSTOM_FIELDS:
		if not frappe.db.exists("Custom Field", {"dt": cf["dt"], "fieldname": cf["fieldname"]}):
			frappe.get_doc({"doctype": "Custom Field", **cf}).insert()
