# Copyright (c) 2026, Grupo Altoplano and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now


def close_table_on_paid(doc):
    """Cierra la sesion de mesa vinculada a una Sales Invoice POS enviada.

    Idempotente: si la sesion ya esta cerrada, no hace nada. Marca la mesa
    como Limpieza una sola vez, cuando la sesion aun estaba abierta.
    """
    session_name = doc.get("custom_table_session")
    if not session_name:
        return
    if not frappe.db.exists("Table Session", session_name):
        return

    session = frappe.get_doc("Table Session", session_name)
    if session.status == "Cerrada":
        return

    session.status = "Cerrada"
    session.sales_invoice = doc.name
    session.closed_at = now()
    session.save()

    if session.table:
        table = frappe.get_doc("Restaurant Table", session.table)
        if table.current_session == session_name:
            table.status = "Limpieza"
            table.current_session = None
            table.save()

