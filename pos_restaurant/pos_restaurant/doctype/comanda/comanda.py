# Copyright (c) 2026, Grupo Altoplano and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now


STATUS_TRANSITIONS = {
	"Pendiente": ["En preparación", "Cancelada"],
	"En preparación": ["Lista", "Cancelada"],
	"Lista": ["Entregada", "Cancelada"],
}


class Comanda(Document):
	def validate(self):
		self._validate_transition()
		self._set_timestamps()
		self._sync_summary()

	def _validate_transition(self):
		if self.is_new():
			return
		previous = self.get_doc_before_save()
		if not previous:
			return
		old = previous.get("status")
		new = self.status
		if old == new:
			return
		allowed = STATUS_TRANSITIONS.get(old, [])
		if new not in allowed:
			frappe.throw(_("Transición no permitida: {0} → {1}").format(old, new))

	def _set_timestamps(self):
		previous = self.get_doc_before_save() if not self.is_new() else None
		old = previous.get("status") if previous else None
		if old == self.status:
			return
		ts = now()
		if self.status == "En preparación" and not self.started_at:
			self.started_at = ts
		elif self.status == "Lista" and not self.ready_at:
			self.ready_at = ts
		elif self.status == "Entregada" and not self.delivered_at:
			self.delivered_at = ts

	def _sync_summary(self):
		items = self.get("items") or []
		names = [i.item_name for i in items if getattr(i, "item_name", None)]
		self.item_count = len(items)
		self.items_summary = ", ".join(names) if names else None
