# Copyright (c) 2026, Grupo Altoplano and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import flt


@frappe.whitelist()
def sync_session_items(session_name, items):
	"""Persiste los items del carrito en la cuenta de la mesa (idempotente)."""
	if isinstance(items, str):
		items = json.loads(items) if items else []
	session = frappe.get_doc("Table Session", session_name)
	incoming = _normalize(items)
	_upsert(session, incoming)
	session.save()
	return session.as_dict()


@frappe.whitelist()
def get_session(session_name):
	"""Lee la cuenta completa de la mesa."""
	return frappe.get_doc("Table Session", session_name).as_dict()


def _normalize(items):
	"""Devuelve dict keyed por line_uid (o line_id) con items validos."""
	out = {}
	for it in items or []:
		uid = it.get("line_uid") or it.get("line_id")
		if not uid or not it.get("item_code"):
			continue
		out[uid] = it
	return out


def _item_name(it):
	return it.get("item_name") or frappe.db.get_value("Item", it.get("item_code"), "item_name")


def _upsert(session, incoming):
	"""Sincroniza items por line_uid sin perder sent_qty. Marca canceladas las removidas ya enviadas."""
	for uid, it in incoming.items():
		row = next((r for r in session.items if r.line_uid == uid), None)
		if row is None:
			session.append("items", {
				"line_uid": uid,
				"item_code": it.get("item_code"),
				"item_name": _item_name(it),
				"qty": flt(it.get("qty") or 0),
				"uom": it.get("uom"),
				"rate": flt(it.get("rate") or 0),
				"notes": it.get("notes") or "",
				"modifiers": json.dumps(it.get("selected_modifiers") or [], ensure_ascii=False),
				"sent_qty": 0,
				"status": "Activa",
			})
		else:
			row.item_code = it.get("item_code")
			row.item_name = _item_name(it)
			row.qty = flt(it.get("qty") or 0)
			row.uom = it.get("uom")
			row.rate = flt(it.get("rate") or 0)
			row.notes = it.get("notes") or ""
			row.modifiers = json.dumps(it.get("selected_modifiers") or [], ensure_ascii=False)
			row.status = "Activa"

	# Remover ausentes sin enviar; cancelar ausentes ya enviados
	to_remove = []
	for row in session.items:
		if row.line_uid in incoming:
			continue
		if flt(row.sent_qty) > 0:
			row.status = "Cancelada"
		else:
			to_remove.append(row)
	for row in to_remove:
		session.items.remove(row)


def pending_deltas(session):
	"""Calcula deltas a cocina: ADD (qty - sent_qty > 0) y VOID (reduccion o cancelacion)."""
	pending = []
	for row in session.items:
		sent = flt(row.sent_qty)
		qty = flt(row.qty)
		delta = qty - sent
		if delta > 0.0001:
			pending.append(_row_delta(row, abs(delta), "ADD"))
		elif delta < -0.0001 and sent > 0:
			pending.append(_row_delta(row, abs(delta), "VOID"))
		elif row.status == "Cancelada" and sent > 0:
			pending.append(_row_delta(row, sent, "VOID"))
	return pending


def _row_delta(row, qty, action):
	mods = row.get("modifiers")
	if isinstance(mods, str):
		try:
			mods = json.loads(mods)
		except ValueError:
			mods = []
	return {
		"line_id": row.line_uid,
		"line_uid": row.line_uid,
		"item_code": row.item_code,
		"item_name": row.item_name,
		"qty": qty,
		"uom": row.uom,
		"preparation_text": row.notes or "",
		"selected_modifiers": mods,
		"action": action,
	}


def mark_sent(session, items):
	"""Actualiza sent_qty tras enviar a cocina."""
	incoming = _normalize(items)
	for row in session.items:
		if row.line_uid in incoming:
			row.sent_qty = flt(incoming[row.line_uid].get("qty") or 0)
			if row.status == "Cancelada":
				row.sent_qty = 0
