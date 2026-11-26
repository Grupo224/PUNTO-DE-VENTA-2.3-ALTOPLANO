# Copyright (c) 2026, Grupo Altoplano and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _

STATUS_TRANSITIONS = {
	"Pendiente": ["En preparación", "Cancelada"],
	"En preparación": ["Lista", "Cancelada"],
	"Lista": ["Entregada", "Cancelada"],
}


@frappe.whitelist()
def send_to_kitchen(payload):
	"""Crea una Comanda incremental (solo lo nuevo desde el ultimo envio).

	Si trae session_name, sincroniza la cuenta de la mesa y envia unicamente
	los deltas (ADD/VOID). Sin session_name, envia todo el carrito (mostrador).
	Idempotente por request_id.
	"""
	data = _parse(payload)
	request_id = data.get("request_id") or frappe.generate_hash(length=12)

	existing = frappe.db.get_value("Comanda", {"request_id": request_id}, "name")
	if existing:
		return frappe.get_doc("Comanda", existing).as_dict()

	company = data.get("company")
	if not company:
		frappe.throw(_("Company is required"))

	from pos_restaurant.restaurant_orders import (
		_upsert,
		_normalize,
		pending_deltas,
		mark_sent,
	)

	session_name = data.get("session_name")
	session = None
	if session_name:
		session = frappe.get_doc("Table Session", session_name)
		_upsert(session, _normalize(data.get("items")))
		session.save()
		items_to_send = pending_deltas(session)
	else:
		items_to_send = [
			{
				"line_id": it.get("line_id"),
				"item_code": it.get("item_code"),
				"item_name": it.get("item_name")
				or frappe.db.get_value("Item", it.get("item_code"), "item_name"),
				"qty": it.get("qty") or 1,
				"uom": it.get("uom"),
				"preparation_text": it.get("preparation_text") or "",
				"selected_modifiers": it.get("selected_modifiers") or [],
				"action": "ADD",
			}
			for it in (data.get("items") or [])
			if it.get("item_code")
		]

	if not items_to_send:
		return {"name": None, "status": "Sin cambios", "message": _("Nada nuevo por enviar")}

	comanda = frappe.new_doc("Comanda")
	comanda.company = company
	comanda.pos_profile = data.get("pos_profile")
	comanda.order_reference = data.get("order_reference") or ""
	comanda.request_id = request_id
	comanda.sales_invoice = data.get("sales_invoice")
	comanda.channel = data.get("channel")
	comanda.destination = data.get("destination")
	comanda.delivery_type = data.get("delivery_type")
	comanda.delivery_partner = data.get("delivery_partner")
	comanda.person = data.get("person")
	if session:
		comanda.table_session = session.name
		comanda.table = session.table
		if not (comanda.destination or "").strip():
			comanda.destination = session.table
		if not (comanda.person or "").strip():
			comanda.person = session.waiter or frappe.session.user

	for it in items_to_send:
		ingredients = _build_ingredients_snapshot(
			it.get("item_code"), it.get("selected_modifiers")
		)
		comanda.append(
			"items",
			{
				"line_id": it.get("line_id"),
				"item_code": it.get("item_code"),
				"item_name": it.get("item_name"),
				"qty": it.get("qty"),
				"action": it.get("action") or "ADD",
				"uom": it.get("uom"),
				"preparation_text": it.get("preparation_text") or "",
				"ingredients": json.dumps(ingredients, ensure_ascii=False),
			},
		)

	comanda.insert()

	if session:
		mark_sent(session, data.get("items"))
		session.save()

	return comanda.as_dict()


@frappe.whitelist()
def get_kitchen_board(pos_profile=None, statuses=None):
	"""List open comandas enriched for the KDS (items, recipe, timestamps)."""
	filters = {"status": ["not in", ["Entregada", "Cancelada"]]}
	if statuses:
		s = _parse(statuses) if isinstance(statuses, str) else statuses
		if s:
			filters["status"] = ["in", s]
	if pos_profile:
		filters["pos_profile"] = pos_profile

	names = frappe.get_all("Comanda", filters=filters, order_by="creation asc", pluck="name")
	result = []
	for name in names:
		doc = frappe.get_doc("Comanda", name)
		items = []
		for it in doc.items:
			ingredients = _parse(it.get("ingredients")) if it.get("ingredients") else []
			items.append(
				{
					"item_code": it.item_code,
					"item_name": it.item_name,
					"qty": it.qty,
					"uom": it.uom,
					"preparation_text": it.preparation_text,
					"ingredients": ingredients,
				}
			)
		result.append(
			{
				"name": doc.name,
				"creation": str(doc.creation),
				"status": doc.status,
				"channel": doc.channel,
				"destination": doc.destination,
				"delivery_type": doc.delivery_type,
				"delivery_partner": doc.delivery_partner,
				"person": doc.person,
				"order_reference": doc.order_reference,
				"sales_invoice": doc.sales_invoice,
				"started_at": str(doc.started_at) if doc.started_at else None,
				"ready_at": str(doc.ready_at) if doc.ready_at else None,
				"delivered_at": str(doc.delivered_at) if doc.delivered_at else None,
				"items": items,
			}
		)
	return result


@frappe.whitelist()
def get_comanda(name):
	return frappe.get_doc("Comanda", name).as_dict()


@frappe.whitelist()
def set_comanda_status(name, status, destination=None, person=None):
	doc = frappe.get_doc("Comanda", name)
	allowed = STATUS_TRANSITIONS.get(doc.status, [])
	if status not in allowed:
		frappe.throw(_("Transición no permitida: {0} → {1}").format(doc.status, status))
	if destination is not None:
		doc.destination = destination
	if person is not None:
		doc.person = person
	doc.status = status
	now = frappe.utils.now()
	if status == "En preparación":
		doc.started_at = now
	elif status == "Lista":
		doc.ready_at = now
	elif status == "Entregada":
		doc.delivered_at = now
		if not (doc.destination or "").strip():
			doc.destination = _default_destination(doc)
		if not (doc.person or "").strip():
			doc.person = _default_person(doc)
	doc.save(ignore_permissions=True)
	return doc.as_dict()


def _default_destination(doc):
	if doc.table:
		return doc.table
	if doc.channel == "Pickup":
		return "Mostrador"
	if doc.channel == "Delivery":
		return doc.delivery_partner or "Cliente"
	return doc.destination or "Mostrador"


def _default_person(doc):
	if doc.table:
		waiter = frappe.db.get_value("Restaurant Table", doc.table, "current_waiter")
		return waiter or frappe.session.user
	return frappe.session.user


@frappe.whitelist()
def update_comanda_handoff(name, destination=None, person=None, delivery_type=None, delivery_partner=None):
	"""Actualiza destino/receptor de una comanda desde el portal de cocina."""
	doc = frappe.get_doc("Comanda", name)
	if destination is not None:
		doc.destination = destination
	if person is not None:
		doc.person = person
	if delivery_type is not None:
		doc.delivery_type = delivery_type
	if delivery_partner is not None:
		doc.delivery_partner = delivery_partner
	doc.save(ignore_permissions=True)
	return doc.as_dict()


@frappe.whitelist()
def get_waiters():
	"""Lista de usuarios activos para asignar como mesero."""
	users = frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User"},
		fields=["name", "full_name"],
		order_by="full_name asc",
	)
	return [{"name": u.name, "full_name": u.full_name or u.name} for u in users]


@frappe.whitelist()
def set_table_waiter(table_name, waiter):
	"""Asigna mesero a la mesa y a su sesión abierta."""
	table = frappe.get_doc("Restaurant Table", table_name)
	table.current_waiter = waiter
	table.save(ignore_permissions=True)
	if table.current_session:
		session = frappe.get_doc("Table Session", table.current_session)
		session.waiter = waiter
		session.save(ignore_permissions=True)
	frappe.db.commit()
	return {"name": table.name, "current_waiter": table.current_waiter}


@frappe.whitelist()
def get_preparation_options(item_code):
	"""Return the preparation toggle options for an item (legacy)."""
	return frappe.db.get_value("Item", item_code, "custom_preparation_options") or ""


@frappe.whitelist()
def get_modifiers(item_code):
	"""Return structured modifier groups for an item (relational model)."""
	item = frappe.get_doc("Item", item_code)
	groups = []
	for link in item.get("custom_restaurant_modifier_groups") or []:
		if not link.modifier_group:
			continue
		grp = frappe.get_doc("Restaurant Modifier Group", link.modifier_group)
		groups.append(
			{
				"group": grp.name,
				"title": grp.title or grp.name,
				"selection_type": grp.selection_type or "Multiple",
				"is_required": grp.is_required or 0,
				"min_selections": grp.min_selections,
				"max_selections": grp.max_selections,
				"sort_order": link.sort_order or 0,
				"options": [
					{
						"option": o.option_name,
						"price_delta": o.price_delta or 0,
						"default": o.default_selected or 0,
						"ingredient_item": o.ingredient_item,
						"ingredient_qty": o.ingredient_qty,
						"ingredient_uom": o.ingredient_uom,
						"ingredient_effect": o.ingredient_effect or "Add",
					}
					for o in grp.get("options") or []
				],
			}
		)
	return groups


def _build_ingredients_snapshot(item_code, selected_modifiers):
	"""Build recipe snapshot: base ingredients (BOM) + modifiers (add/remove)."""
	ingredients = []
	bom_name = frappe.db.get_value(
		"BOM", {"item": item_code, "is_active": 1, "is_default": 1}, "name"
	)
	if bom_name:
		bom = frappe.get_doc("BOM", bom_name)
		for i in bom.items:
			ing_name = frappe.db.get_value("Item", i.item_code, "item_name") or i.item_code
			ingredients.append({"label": ing_name, "type": "base"})
	for m in selected_modifiers or []:
		effect = m.get("ingredient_effect") or "Add"
		option = m.get("option") or m.get("option_name") or ""
		if effect == "Remove":
			ingredients.append({"label": option, "type": "remove"})
		elif effect == "Add":
			label = option
			pd = m.get("price_delta")
			if pd:
				label = label + " (+$" + str(pd) + ")"
			ingredients.append({"label": label, "type": "add"})
	return ingredients


def _parse(payload):
	if isinstance(payload, str):
		return json.loads(payload)
	return payload or {}

@frappe.whitelist()
def get_rooms(pos_profile=None):
    filters = {"disabled": 0}
    if pos_profile:
        filters["pos_profile"] = pos_profile
    return frappe.get_all("Restaurant Room", filters=filters, fields=["name", "title", "pos_profile", "sort_order"], order_by="sort_order asc")

@frappe.whitelist()
def get_tables(room=None):
    filters = {}
    if room:
        filters["room"] = room
    return frappe.get_all("Restaurant Table", filters=filters, fields=["name", "room", "capacity", "shape", "position_x", "position_y", "status", "current_waiter", "current_guests", "current_session"], order_by="name asc")

@frappe.whitelist()
def open_table(table_name, guests=1, waiter=None):
    table = frappe.get_doc("Restaurant Table", table_name)
    if table.status not in ("Disponible", "Reservada"):
        frappe.throw(_("La mesa {0} no esta disponible").format(table.name))
    pos_profile = frappe.db.get_value("Restaurant Room", table.room, "pos_profile") if table.room else None
    session = frappe.get_doc({
        "doctype": "Table Session",
        "table": table.name,
        "room": table.room,
        "pos_profile": pos_profile,
        "opened_at": frappe.utils.now(),
        "status": "Abierta",
        "waiter": waiter or frappe.session.user,
        "guests": guests or 1,
    })
    session.insert()
    table.status = "Ocupada"
    table.current_waiter = waiter or frappe.session.user
    table.current_guests = guests or 1
    table.current_session = session.name
    table.save()
    return session.as_dict()

@frappe.whitelist()
def set_table_status(table_name, status):
    table = frappe.get_doc("Restaurant Table", table_name)
    table.status = status
    table.save()
    return {"name": table.name, "status": table.status}

@frappe.whitelist()
def close_table(table_name):
    table = frappe.get_doc("Restaurant Table", table_name)
    if table.current_session:
        session = frappe.get_doc("Table Session", table.current_session)
        if session.status == "Abierta":
            session.status = "Cerrada"
            session.closed_at = frappe.utils.now()
            session.save()
    table.status = "Limpieza"
    table.current_session = None
    table.save()
    return {"name": table.name, "status": table.status}
@frappe.whitelist()
def create_room(name, pos_profile=None):
    if frappe.db.exists("Restaurant Room", name):
        frappe.throw(_("El salon {0} ya existe").format(name))
    doc = frappe.get_doc({"doctype": "Restaurant Room", "title": name, "pos_profile": pos_profile})
    doc.name = name
    doc.insert()
    return doc.as_dict()

@frappe.whitelist()
def remove_room(name):
    frappe.delete_doc("Restaurant Room", name)
    return {"deleted": name}

SHAPE_MAP = {"rect": "Rectangular", "square": "Cuadrada", "round": "Redonda", "oval": "Ovalada", "Rectangular": "Rectangular", "Cuadrada": "Cuadrada", "Redonda": "Redonda", "Ovalada": "Ovalada"}

@frappe.whitelist()
def create_table(name, room, capacity=4, shape="rect", x=50, y=50):
    if frappe.db.exists("Restaurant Table", name):
        frappe.throw(_("La mesa {0} ya existe").format(name))
    doc = frappe.get_doc({"doctype": "Restaurant Table", "room": room, "capacity": capacity, "shape": SHAPE_MAP.get(shape, "Rectangular"), "position_x": x, "position_y": y, "status": "Disponible"})
    doc.name = name
    doc.insert()
    return doc.as_dict()

@frappe.whitelist()
def update_table(name, capacity=None, shape=None, x=None, y=None):
    doc = frappe.get_doc("Restaurant Table", name)
    if capacity is not None:
        doc.capacity = capacity
    if shape:
        doc.shape = SHAPE_MAP.get(shape, shape)
    if x is not None:
        doc.position_x = x
    if y is not None:
        doc.position_y = y
    doc.save()
    return doc.as_dict()

@frappe.whitelist()
def remove_table(name):
    frappe.delete_doc("Restaurant Table", name)
    return {"deleted": name}
@frappe.whitelist()
def quick_checkout(items, payment_mode="Efectivo", table=None, table_session=None, pos_profile=None, tip_amount=0):
    import json
    from frappe.utils import flt
    if isinstance(items, str):
        items = json.loads(items)
    if not pos_profile:
        frappe.throw(_("POS Profile es requerido"))
    pp = frappe.get_cached_doc("POS Profile", pos_profile)
    company = pp.company
    warehouse = pp.warehouse
    customer = pp.get("customer") or _walkin_customer()

    doc = frappe.new_doc("Sales Invoice")
    doc.is_pos = 1
    doc.company = company
    doc.pos_profile = pos_profile
    doc.customer = customer
    doc.update_stock = 1

    from pos_next.api.items import get_item_details as _gd
    for it in items:
        code = it.get("item_code")
        qty = flt(it.get("qty") or 1)
        if not code:
            continue
        d = _gd(code, pos_profile, customer=customer, qty=qty)
        doc.append("items", {
            "item_code": code,
            "qty": qty,
            "rate": flt(d.get("price_list_rate") or d.get("rate") or 0),
            "uom": d.get("uom") or d.get("stock_uom"),
            "warehouse": warehouse,
            "conversion_factor": 1,
        })

    if not doc.items:
        frappe.throw(_("No hay productos"))

    tip_amount = flt(tip_amount)
    if tip_amount > 0:
        tip_account = pp.get("tip_account")
        if not tip_account:
            frappe.throw(_("Configura la Cuenta de propina en el POS Profile para registrar la propina"))
        doc.append("taxes", {
            "charge_type": "Actual",
            "account_head": tip_account,
            "description": "Propina",
            "tax_amount": tip_amount,
        })

    doc.insert(ignore_permissions=True)

    if payment_mode:
        from pos_next.api.invoices import get_payment_account
        account_info = get_payment_account(payment_mode, company)
        account = account_info.get("account") if isinstance(account_info, dict) else account_info
        doc.append("payments", {
            "mode_of_payment": payment_mode,
            "amount": flt(doc.grand_total),
            "account": account,
        })

    if table:
        doc.custom_table = table
    if table_session:
        doc.custom_table_session = table_session

    doc.save(ignore_permissions=True)
    doc.submit()
    return {"name": doc.name, "grand_total": doc.grand_total, "status": doc.status}

def _walkin_customer():
    cust = frappe.db.get_value("Customer", {}, "name", order_by="creation asc")
    if not cust:
        cust = frappe.get_doc({"doctype": "Customer", "customer_name": "Consumidor Final", "customer_group": "All Customer Groups", "territory": "All Territories"}).insert(ignore_permissions=True).name
    return cust
