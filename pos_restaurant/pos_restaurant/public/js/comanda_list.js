// Mejora visual del Kanban de Comandas (colores por estado, canal, tiempo y enlaces)
frappe.provide("altoplano.comanda_kanban");

const STATUS_COLORS = {
	"Pendiente": "#2563eb",
	"En preparación": "#f59e0b",
	"Lista": "#16a34a",
	"Entregada": "#6b7280",
	"Cancelada": "#dc2626",
};

const CHANNEL_LABELS = {
	Mesa: { label: "Mesa", color: "#ff7a00" },
	Pickup: { label: "Pickup", color: "#0ea5e9" },
	Delivery: { label: "Delivery", color: "#7c3aed" },
};

function altoplano_minutes_since(ts) {
	if (!ts) return null;
	const d = new Date(String(ts).replace(" ", "T"));
	if (Number.isNaN(d.getTime())) return null;
	return Math.max(0, Math.floor((Date.now() - d.getTime()) / 60000));
}

function altoplano_escape_html(s) {
	return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
		"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
	}[c]));
}

async function altoplano_enhance_kanban() {
	let info = {};
	try {
		const r = await frappe.call("pos_restaurant.api.get_kanban_card_info", {});
		info = r.message || {};
	} catch (e) {
		info = {};
	}

	const decorate = () => {
		document.querySelectorAll(".kanban-card-wrapper[data-name]").forEach((wrap) => {
			if (wrap.dataset.altoplanoDone === "1") return;
			const name = decodeURIComponent(wrap.dataset.name || "");
			const d = info[name];
			if (!d) return;
			wrap.dataset.altoplanoDone = "1";

			const card = wrap.querySelector(".kanban-card");
			if (card) card.style.borderLeft = "5px solid " + (STATUS_COLORS[d.status] || "#94a3b8");

			let meta = wrap.querySelector(".kanban-card-meta");
			if (!meta) {
				meta = document.createElement("div");
				meta.className = "kanban-card-meta";
				const body = wrap.querySelector(".kanban-card-body");
				if (body) body.appendChild(meta);
			}

			const ch = CHANNEL_LABELS[d.channel] || { label: d.channel || "—", color: "#64748b" };
			const stageTs = d.status === "En preparación" ? d.started_at : d.status === "Lista" ? d.ready_at : d.creation;
			const mins = altoplano_minutes_since(stageTs);

			let html = '<div style="display:flex;flex-wrap:wrap;gap:5px;margin-top:7px;">';
			html += '<span style="background:' + ch.color + ';color:#fff;border-radius:4px;padding:1px 7px;font-size:11px;font-weight:700;">' + altoplano_escape_html(ch.label) + "</span>";
			if (d.item_count) html += '<span style="background:#f1f5f9;color:#334155;border-radius:4px;padding:1px 7px;font-size:11px;font-weight:600;">' + d.item_count + " art.</span>";
			if (mins !== null) html += '<span style="background:#fef3c7;color:#92400e;border-radius:4px;padding:1px 7px;font-size:11px;font-weight:700;">⏱ ' + mins + " min</span>";
			html += "</div>";

			const links = [];
			if (d.sales_invoice) links.push('<a href="/app/sales-invoice/' + altoplano_escape_html(d.sales_invoice) + '" style="color:#16a34a;">Factura ' + altoplano_escape_html(d.sales_invoice) + "</a>");
			if (d.table) links.push('<span style="color:#64748b;">Mesa ' + altoplano_escape_html(d.table) + "</span>");
			if (links.length) html += '<div style="font-size:11px;margin-top:4px;display:flex;gap:8px;flex-wrap:wrap;">' + links.join("") + "</div>";

			meta.innerHTML = html;
		});
	};

	decorate();
	new MutationObserver(decorate).observe(document.body, { childList: true, subtree: true });
}

frappe.ready(() => {
	if (frappe.get_route_str().startsWith("List/Comanda/Kanban")) {
		altoplano_enhance_kanban();
	}
});
