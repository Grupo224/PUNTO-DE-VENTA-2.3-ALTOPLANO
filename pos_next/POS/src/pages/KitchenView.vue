<template>
	<div class="kds" :class="{ expo: view === 'expo' }">
		<header class="kds-header">
			<div class="brand"><b>ALTOPLANO</b><span>COCINA Y ENTREGA</span></div>
			<nav aria-label="Puesto de trabajo">
				<button :class="{ on: view === 'cook' }" @click="view = 'cook'">Cocina</button>
				<button :class="{ on: view === 'expo' }" @click="view = 'expo'">Caja y entrega</button>
			</nav>
			<span class="net" role="status">{{ net }}</span>
		</header>

		<main>
			<section class="overview">
				<h1>{{ view === 'cook' ? 'Preparar pedidos' : 'Entregar pedidos' }}</h1>
				<div class="meters" aria-label="Ir a una etapa">
					<button v-for="m in meters" :key="m.key" @click="jump(m.key)">
						<strong>{{ m.count }}</strong> {{ m.label }}
					</button>
				</div>
			</section>

			<div class="bar">
				<div class="channels" role="group" aria-label="Filtrar por tipo de entrega">
					<button v-for="c in channelOpts" :key="c.key" :class="{ on: channel === c.key }" @click="channel = c.key">{{ c.label }}</button>
				</div>
				<label class="search"><span>Buscar</span>
					<input v-model="query" type="search" placeholder="Folio, mesa o persona">
				</label>
				<button class="refresh" @click="load">Actualizar</button>
			</div>

			<p class="notice" role="status">{{ notice }}</p>

			<div class="board">
				<section v-for="lane in lanes" :key="lane.key" class="lane" :class="{ full: lane.full }" :data-zone="lane.key">
					<div class="lanetitle"><h2>{{ lane.title }}</h2><span>{{ lane.orders.length }}</span></div>

					<template v-if="lane.grouped">
						<template v-for="(grp, ch) in lane.groups" :key="ch">
							<h3 v-if="grp.length" class="groupname">{{ chLabel(ch) }} · {{ grp.length }}</h3>
							<article v-for="o in grp" :key="o.name" class="card" :data-status="o.status">
								<card-body :order="o" :view="view" @action="advance" />
							</article>
						</template>
					</template>
					<template v-else>
						<article v-for="o in lane.orders" :key="o.name" class="card" :data-status="o.status">
							<card-body :order="o" :view="view" @action="advance" />
						</article>
						<p v-if="!lane.orders.length" class="empty">Sin pedidos en esta etapa.</p>
					</template>
				</section>
			</div>
		</main>

		<dialog ref="confirmEl">
			<form @submit.prevent>
				<h2>Entregar comanda</h2>
				<p class="muted">{{ confirmText }}</p>
				<label class="field"><span>Destino</span>
					<input v-model="handoff.destination" type="text" placeholder="Mesa, mostrador o cliente">
				</label>
				<label class="field"><span>Receptor</span>
					<input v-model="handoff.person" type="text" placeholder="Quién recibe">
				</label>
				<div class="actions">
					<button type="button" @click="closeConfirm">Volver</button>
					<button type="button" class="primary" @click="confirmDelivery">Ya lo entregué</button>
				</div>
			</form>
		</dialog>
	</div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { call } from "@/utils/apiWrapper";

const view = ref("cook");
const channel = ref("");
const query = ref("");
const notice = ref("");
const orders = ref([]);
const loading = ref(false);
const net = ref("Cargando…");
const confirmEl = ref(null);
const pendingOrder = ref(null);
const handoff = ref({ destination: "", person: "" });
let timer = null;

const CH = { Mesa: "table", Pickup: "pickup", Delivery: "delivery" };
const CH_LABEL = { table: "Mesa", pickup: "Pickup", delivery: "Delivery" };
const NEXT = { Pendiente: "En preparación", "En preparación": "Lista", Lista: "Entregada" };
const ACTION = { Pendiente: "Empezar a cocinar", "En preparación": "Marcar lista", Lista: "Confirmar entrega" };

const channelOpts = [
	{ key: "", label: "Todos" },
	{ key: "Mesa", label: "Mesa" },
	{ key: "Pickup", label: "Pickup" },
	{ key: "Delivery", label: "Delivery" },
];

function stageSince(o) {
	let ts = o.creation;
	if (o.status === "En preparación") ts = o.started_at;
	else if (o.status === "Lista") ts = o.ready_at;
	else if (o.status === "Entregada") ts = o.delivered_at;
	if (!ts) return 0;
	const d = new Date(String(ts).replace(" ", "T"));
	return Number.isNaN(d.getTime()) ? 0 : Math.floor((Date.now() - d.getTime()) / 60000);
}

const active = computed(() => orders.value.filter((o) => o.status !== "Entregada" && o.status !== "Cancelada"));
const deliveredToday = computed(() => {
	const t = new Date();
	return orders.value.filter((o) => {
		if (o.status !== "Entregada") return false;
		const d = new Date(String(o.delivered_at || o.modified || o.creation).replace(" ", "T"));
		return !Number.isNaN(d.getTime()) && d.toDateString() === t.toDateString();
	});
});

const meters = computed(() => {
	if (view.value === "cook") {
		return [
			{ key: "queued", label: "Por preparar", count: active.value.filter((o) => o.status === "Pendiente").length },
			{ key: "working", label: "Cocinando", count: active.value.filter((o) => o.status === "En preparación").length },
			{ key: "ready", label: "Listas", count: active.value.filter((o) => o.status === "Lista").length },
		];
	}
	return [
		{ key: "ready", label: "Por entregar", count: active.value.filter((o) => o.status === "Lista").length },
		{ key: "tracking", label: "En cocina", count: active.value.filter((o) => o.status === "Pendiente" || o.status === "En preparación").length },
		{ key: "done", label: "Entregadas", count: deliveredToday.value.length },
	];
});

function visible() {
	const q = query.value.trim().toLowerCase();
	const list = active.value.filter((o) => (!channel.value || o.channel === channel.value) && [o.name, o.destination, o.person].join(" ").toLowerCase().includes(q));
	return list.sort((a, b) => stageSince(a) - stageSince(b) || String(a.name).localeCompare(String(b.name)));
}

const lanes = computed(() => {
	const list = visible();
	const cook = view.value === "cook";
	if (cook) {
		return [
			{ key: "queued", title: "Por preparar", full: false, grouped: false, orders: list.filter((o) => o.status === "Pendiente"), groups: {} },
			{ key: "working", title: "En preparación", full: false, grouped: false, orders: list.filter((o) => o.status === "En preparación"), groups: {} },
			{ key: "ready", title: "Listas para el pase", full: true, grouped: false, orders: list.filter((o) => o.status === "Lista"), groups: {} },
		];
	}
	const ready = list.filter((o) => o.status === "Lista");
	const tracking = list.filter((o) => o.status === "Pendiente" || o.status === "En preparación");
	const groups = { table: [], pickup: [], delivery: [] };
	for (const o of ready) groups[CH[o.channel] || "table"].push(o);
	return [
		{ key: "ready", title: "Listas para entregar", full: false, grouped: true, orders: ready, groups },
		{ key: "tracking", title: "Seguimiento de cocina", full: false, grouped: false, orders: tracking, groups: {} },
		{ key: "done", title: "Entregadas del turno", full: true, grouped: false, orders: deliveredToday.value, groups: {} },
	];
});

async function load() {
	if (loading.value) return;
	loading.value = true;
	try {
		const board = await call("pos_restaurant.api.get_kitchen_board", {
			statuses: ["Pendiente", "En preparación", "Lista", "Entregada"],
		});
		orders.value = board || [];
		net.value = "Sincronizado · " + new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
	} catch (e) {
		net.value = "Sin actualizar";
		notice.value = e?.messages?.join(", ") || e?.message || String(e);
	} finally {
		loading.value = false;
	}
}

function isBlocked(o) {
	if (NEXT[o.status] !== "Entregada") return false;
	return !(o.destination && o.destination.trim()) || !(o.person && o.person.trim());
}

function advance(o) {
	if (loading.value) return;
	if (NEXT[o.status] === "Entregada") {
		pendingOrder.value = o;
		handoff.value = { destination: o.destination || "", person: o.person || "" };
		confirmText.value = o.name;
		confirmEl.value?.showModal();
		return;
	}
	doAdvance(o);
}

async function doAdvance(o) {
	try {
		await call("pos_restaurant.api.set_comanda_status", { name: o.name, status: NEXT[o.status] });
		notice.value = o.name + " · " + NEXT[o.status];
	} catch (e) {
		notice.value = e?.messages?.join(", ") || e?.message || String(e);
	}
	await load();
}

async function confirmDelivery() {
	const o = pendingOrder.value;
	pendingOrder.value = null;
	confirmEl.value?.close();
	if (!o) return;
	try {
		await call("pos_restaurant.api.update_comanda_handoff", {
			name: o.name,
			destination: handoff.value.destination,
			person: handoff.value.person,
		});
	} catch (e) {
		notice.value = e?.messages?.join(", ") || e?.message || String(e);
	}
	await doAdvance(o);
}

function closeConfirm() {
	pendingOrder.value = null;
	confirmEl.value?.close();
}

const confirmText = ref("");

function jump(key) {
	const el = document.querySelector("[data-zone='" + key + "']");
	if (el) {
		el.scrollIntoView({ block: "start" });
		el.focus({ preventScroll: true });
	}
}

function chLabel(ch) {
	return CH_LABEL[ch] || ch;
}

function routeClass(channel) {
	return "route " + (CH[channel] || "table");
}

function routeName(channel) {
	return channel || "—";
}

function age(o) {
	return stageSince(o) + " min";
}

function baseText(it) {
	return (it.ingredients || []).filter((i) => i.type === "base").map((i) => i.label).join(", ");
}
function omitText(it) {
	return (it.ingredients || []).filter((i) => i.type === "remove").map((i) => i.label).join(", ");
}
function extraText(it) {
	return (it.ingredients || []).filter((i) => i.type === "add").map((i) => i.label).join(", ");
}

onMounted(() => {
	load();
	timer = setInterval(() => { if (!document.hidden) load(); }, 5000);
});
onUnmounted(() => clearInterval(timer));
</script>

<script>
import { defineComponent, h } from "vue";

const CardBody = defineComponent({
	name: "CardBody",
	props: { order: Object, view: String },
	emits: ["action"],
	methods: {
		stageSince(o) {
			let ts = o.creation;
			if (o.status === "En preparación") ts = o.started_at;
			else if (o.status === "Lista") ts = o.ready_at;
			else if (o.status === "Entregada") ts = o.delivered_at;
			if (!ts) return 0;
			const d = new Date(String(ts).replace(" ", "T"));
			return Number.isNaN(d.getTime()) ? 0 : Math.floor((Date.now() - d.getTime()) / 60000);
		},
		routeClass(channel) { return "route " + ({ Mesa: "table", Pickup: "pickup", Delivery: "delivery" }[channel] || "table"); },
		routeName(channel) { return channel || "—"; },
		baseText(it) { return (it.ingredients || []).filter((i) => i.type === "base").map((i) => i.label).join(", "); },
		omitText(it) { return (it.ingredients || []).filter((i) => i.type === "remove").map((i) => i.label).join(", "); },
		extraText(it) { return (it.ingredients || []).filter((i) => i.type === "add").map((i) => i.label).join(", "); },
		isBlocked(o) {
			const next = { Pendiente: "En preparación", "En preparación": "Lista", Lista: "Entregada" }[o.status];
			if (next !== "Entregada") return false;
			return !(o.destination && o.destination.trim()) || !(o.person && o.person.trim());
		},
		actionLabel(s) { return { Pendiente: "→ Empezar a cocinar", "En preparación": "✓ Marcar lista", Lista: "✓ Confirmar entrega" }[s] || ""; },
	},
	render() {
		const o = this.order;
		const cook = this.view === "cook";
		const age = this.stageSince(o) + " min";
		const blocked = this.isBlocked(o);

		const head = h("div", { class: "cardhead" }, [
			h("span", { class: "folio" }, String(o.name || "")),
			h("span", { class: "time" }, age),
		]);

		const handoff = h("div", { class: "handoff" }, [
			h("span", { class: this.routeClass(o.channel) }, this.routeName(o.channel)),
			h("h3", { class: "dest" }, o.destination || "Destino pendiente"),
		]);

		const recipient = h("p", { class: "recipient" }, [
			h("b", null, "Recibe"),
			" · " + (o.person || "Pendiente de asignar"),
		]);

		const foods = h("div", { class: "foods" }, (o.items || []).map((it) => {
			const changes = [];
			if (this.omitText(it)) changes.push(h("span", { class: "change" }, this.omitText(it)));
			if (this.extraText(it)) changes.push(h("span", { class: "change" }, "Extra · " + this.extraText(it)));
			const recipe = cook ? h("p", { class: "recipe" }, [h("b", null, "Base"), " · " + (this.baseText(it) || "Ingredientes pendientes")]) : null;
			const note = it.preparation_text ? h("p", { class: "notes" }, [h("b", null, "Nota"), " · " + it.preparation_text]) : null;
			return h("div", { class: "food", key: (it.item_code || "") + (it.uom || "") }, [
				h("strong", null, [h("span", { class: "qty" }, it.qty + " × "), it.item_name]),
				recipe, changes, note,
			]);
		}));

		const warning = blocked ? h("p", { class: "warning" }, "Falta destino o receptor; se pedirá al entregar.") : null;

		const label = this.actionLabel(o.status);
		const actions = label
			? h("div", { class: "actions" }, [
				h("button", {
					class: "action-btn " + (o.status === "En preparación" ? "primary" : "start"),
					onClick: () => this.$emit("action", o),
				}, label),
			])
		: null;

		const parts = cook
			? [head, foods, handoff, recipient, warning, actions]
			: [handoff, recipient, head, foods, warning, actions];

		return h("div", null, parts);
	},
});

export default { components: { CardBody } };
</script>

<style scoped>
* { box-sizing: border-box; }
.kds { min-height: 100vh; background: #f6f7f9; color: #161d27; font: 16px/1.45 Inter, "Segoe UI", Arial, sans-serif; }
.kds-header { display: flex; align-items: center; gap: 22px; background: #fcf9f4; border-bottom: 3px solid #193c76; padding: 11px clamp(15px, 4vw, 40px); }
.kds-header .brand b { font-size: 1.1rem; color: #193c76; letter-spacing: .04em; }
.kds-header .brand span { font-size: .72rem; color: #42536b; font-weight: 700; margin-left: 8px; letter-spacing: .12em; }
.kds-header nav { display: flex; gap: 8px; background: #e9edf2; padding: 6px; border-radius: 12px; margin-right: auto; }
.kds-header nav button { min-width: 130px; border: 0; background: transparent; min-height: 46px; padding: 10px 16px; border-radius: 8px; font-weight: 650; cursor: pointer; color: #182944; }
.kds-header nav button.on { background: #193c76; color: #fff; }
.kds-header .net { font-size: .86rem; color: #42536b; font-weight: 600; }
.kds main { max-width: 1580px; margin: auto; padding: 22px clamp(14px, 3vw, 44px); }
.overview { background: #193c76; color: #fff; border-radius: 14px; padding: 20px clamp(16px, 2.4vw, 34px); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
.overview h1 { color: #fff; font-size: clamp(1.65rem, 3vw, 2.8rem); margin: 0; line-height: 1.1; }
.overview h1::before { content: ""; display: block; background: #ff7a00; width: 36px; height: 4px; margin-bottom: 9px; }
.meters { display: flex; gap: 10px; flex-wrap: wrap; }
.meters button { display: flex; align-items: center; gap: 8px; color: #fff; border: 1px solid #849bc0; background: #163468; font-size: 1rem; min-height: 48px; padding: 10px 16px; border-radius: 8px; cursor: pointer; font-weight: 650; }
.meters strong { font-size: 1.5rem; }
.bar { display: flex; align-items: center; gap: 12px; border-block: 1px solid #d3dae2; margin-top: 8px; padding: 12px 0; flex-wrap: wrap; }
.channels { display: flex; gap: 8px; flex-wrap: wrap; }
.channels button { font-weight: 650; min-height: 48px; padding: 10px 16px; border: 1px solid #aab4c0; border-radius: 8px; background: #fff; color: #182944; cursor: pointer; }
.channels button.on { background: #193c76; color: #fff; border-color: #193c76; }
.bar .search { margin-left: auto; display: flex; gap: 8px; align-items: center; }
.bar .search span { font-weight: 600; color: #42536b; font-size: .86rem; }
.bar input { min-height: 46px; padding: 8px 12px; border: 1px solid #aab4c0; border-radius: 8px; font: inherit; }
.refresh { min-height: 46px; padding: 8px 14px; border: 1px solid #aab4c0; border-radius: 8px; background: #fff; color: #182944; cursor: pointer; font-weight: 650; }
.notice { margin: 8px 0; min-height: 1.5em; color: #193c76; font-weight: 600; }
.board { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 22px; align-items: start; margin-top: 12px; }
.lane { min-width: 0; min-height: 138px; border-radius: 12px; padding: 8px 3px 16px; scroll-margin-top: 16px; }
.lane:focus { outline: 2px solid #193c76; }
.lane.full { grid-column: 1 / -1; }
.lanetitle { display: flex; align-items: center; justify-content: space-between; padding: 8px 4px 10px; border-bottom: 3px solid #193c76; margin-bottom: 12px; }
.lane[data-zone="queued"] .lanetitle { border-bottom-color: #2563eb; }
.lane[data-zone="working"] .lanetitle { border-bottom-color: #16a34a; }
.lane[data-zone="ready"] .lanetitle { border-bottom-color: #f59e0b; }
.lane[data-zone="done"] .lanetitle { border-bottom-color: #6b7280; }
.lanetitle h2 { font-size: 1.38rem; color: #193c76; margin: 0; }
.lanetitle span { font-weight: 700; padding: 2px 10px; background: #e3e9f1; border-radius: 15px; }
.card { border: 1px solid #c9d0d9; border-left-width: 6px; background: #fff; border-radius: 12px; margin: 0 0 14px; padding: 18px 20px; overflow-wrap: anywhere; }
.card[data-status="Pendiente"] { border-left-color: #2563eb; }
.card[data-status="En preparación"] { border-left-color: #f59e0b; }
.card[data-status="Lista"] { border-left-color: #16a34a; }
.card[data-status="Entregada"] { border-left-color: #6b7280; }
.card[data-status="Cancelada"] { border-left-color: #dc2626; }
.cardhead { display: flex; align-items: center; justify-content: space-between; }
.folio { font-weight: 700; color: #193c76; font-size: 1rem; }
.time { font-weight: 600; color: #42536b; font-size: 1rem; font-variant-numeric: tabular-nums; }
.handoff { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; margin: 6px 0; }
.route { display: inline-block; background: #193c76; color: #fff; border-radius: 4px; padding: 2px 8px; font-size: 1rem; letter-spacing: .04em; font-weight: 750; }
.route.pickup { background: #ff7a00; color: #101010; }
.route.delivery { background: #343c48; }
.dest { font-size: 1.4rem; margin: 0; line-height: 1.2; }
.recipient { color: #19273c; margin-top: 4px; font-size: 1.12rem; }
.foods { margin-top: 4px; }
.food { padding: 12px 0 2px; border-top: 1px solid #dde2e8; margin-top: 12px; }
.food strong { font-size: clamp(1.45rem, 2.1vw, 2rem); line-height: 1.16; }
.qty { color: #193c76; }
.recipe { font-size: clamp(1.15rem, 1.48vw, 1.45rem); line-height: 1.42; margin: 8px 0 5px; color: #152d50; }
.recipe b { color: #193c76; }
.change { font-weight: 700; color: #762e05; background: #fff0dc; padding: 4px 8px; border-radius: 4px; display: inline-block; margin: 4px 4px 0 0; font-size: clamp(1.15rem, 1.45vw, 1.4rem); }
.notes { border-left: 3px solid #193c76; padding: 6px 10px; background: #f0f4fa; margin: 5px 0; font-weight: 600; font-size: clamp(1.15rem, 1.45vw, 1.4rem); }
.warning { font-weight: 700; color: #762e05; background: #fff0dc; padding: 4px 8px; border-radius: 4px; margin: 8px 0 0; }
.actions { margin-top: 16px; }
.action-btn { width: 100%; min-height: 58px; padding: 12px 20px; border-radius: 10px; font-size: 1.15rem; font-weight: 750; cursor: pointer; border: 1px solid transparent; letter-spacing: .01em; display: flex; align-items: center; justify-content: center; gap: 8px; }
.action-btn.start { background: #193c76; color: #fff; border-color: #193c76; }
.action-btn.primary { background: #ff7a00; color: #151515; border-color: #d0680b; }
.action-btn:hover { filter: brightness(1.06); }
.action-btn:active { transform: scale(.99); }
.action-btn:disabled { opacity: .55; cursor: default; }
.empty { color: #556173; border: 1px dashed #bcc8d7; border-radius: 10px; padding: 20px; }
.groupname { font-size: 1.12rem; color: #193c76; margin: 14px 0 7px; }
.groupname:first-of-type { margin-top: 0; }
.expo .board { grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr); }
.expo .dest { font-size: clamp(1.6rem, 2vw, 2.1rem); }
.expo .recipient { font-size: 1.3rem; }
.expo .food strong { font-size: 1.25rem; }
dialog { width: min(440px, 92vw); border: 1px solid #c6d0dc; border-radius: 13px; padding: 24px; }
dialog::backdrop { background: #14223988; }
dialog p { margin: 10px 0; }
dialog p.muted { color: #42536b; font-size: .92rem; }
dialog .field { display: grid; gap: 6px; margin: 12px 0; }
dialog .field span { font-weight: 650; color: #193c76; }
dialog .field input { min-height: 46px; padding: 8px 12px; border: 1px solid #aab4c0; border-radius: 8px; font: inherit; }
dialog .actions { margin-top: 16px; }
button:focus-visible, input:focus-visible { outline: 3px solid #1959ac; outline-offset: 2px; }
@media (max-width: 800px) {
	.kds-header { gap: 7px; flex-wrap: wrap; }
	.kds-header nav { margin-right: 0; }
	.kds-header .net { margin-left: auto; }
	.bar .search { margin-left: 0; }
	.expo .board { grid-template-columns: 1fr; }
	.board { grid-template-columns: 1fr; }
}
@media (max-width: 460px) {
	.kds-header nav { order: 3; width: 100%; }
	.kds-header nav button { flex: 1; }
	.channels button { flex: 1; padding: 6px; }
	.meters button { padding: 5px 9px; font-size: .91rem; }
	.meters strong { font-size: 1.25rem; }
	.card { padding: 14px; }
}
</style>
