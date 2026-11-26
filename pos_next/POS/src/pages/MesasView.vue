<template>
  <div class="cr">
    <header class="cr-header">
      <div class="cr-brand"><span class="cr-mark" aria-hidden="true">▦</span><div><strong>Grupo Altoplano</strong><small>Salones del restaurante</small></div></div>
      <button class="cr-back" @click="goPOS">Volver al POS</button>
    </header>

    <main class="cr-main">
      <div class="cr-heading">
        <h1>{{ modeTitle }}</h1>
        <nav class="cr-nav" aria-label="Tareas del restaurante">
          <button :aria-pressed="mode==='operate'" @click="setMode('operate')">Atender mesas</button>
          <button :aria-pressed="mode==='edit'" @click="setMode('edit')">Acomodar el salón</button>
          <button :aria-pressed="mode==='summary'" @click="setMode('summary')">Ver ocupación</button>
        </nav>
      </div>

      <section class="cr-dash" aria-label="Resumen del salón">
        <div class="cr-dashkpis">
          <button class="cr-dkpi cr-dkpi-mesa" @click="setMode('summary')"><strong>{{ countStatus('Ocupada') }}</strong><span>Ocupadas</span></button>
          <button class="cr-dkpi cr-dkpi-libre" @click="setMode('summary')"><strong>{{ countStatus('Disponible') }}</strong><span>Disponibles</span></button>
          <button class="cr-dkpi cr-dkpi-espera" @click="setMode('summary')"><strong>{{ countStatus('Reservada') }}</strong><span>Reservadas</span></button>
          <button class="cr-dkpi cr-dkpi-limpieza" @click="setMode('summary')"><strong>{{ countStatus('Limpieza') }}</strong><span>Limpieza</span></button>
          <button class="cr-dkpi cr-dkpi-comensales" @click="setMode('summary')"><strong>{{ totalGuests }}</strong><span>Comensales</span></button>
        </div>
        <div class="cr-alerts" v-if="alerts.length">
          <span v-for="a in alerts" :key="a.text" class="cr-alert" :class="'cr-alert-' + a.kind">{{ a.text }}</span>
        </div>
      </section>

      <section class="cr-bar">
        <label class="cr-room">Área
          <select v-model="room" @change="onRoomChange">
            <option v-for="r in rooms" :key="r.id" :value="r.id">{{ r.name }}</option>
          </select>
        </label>
        <span class="cr-counts">{{ tableCount }} mesas en esta área</span>
        <button v-if="mode==='edit'" @click="undo" :disabled="!history.length">Deshacer</button>
        <button v-if="mode==='edit'" class="cr-primary" @click="save" :disabled="!dirty">Guardar plano</button>
        <button v-if="mode!=='edit'" @click="load">Actualizar</button>
      </section>

      <p class="cr-notice" role="status">{{ notice }}</p>

      <div class="cr-layout">
        <section class="cr-board">
          <div class="cr-boardhead">
            <h2>{{ activeRoomName }}</h2>
            <div class="cr-zoom">
              <button @click="zoom(-1)" :disabled="zoomLevel<=1" aria-label="Reducir plano">−</button>
              <button class="cr-fit" @click="zoom(0)">Ajustar</button>
              <button @click="zoom(1)" :disabled="zoomLevel>=3" aria-label="Ampliar plano">+</button>
            </div>
          </div>

          <div class="cr-editbar" v-if="mode==='edit'">
            <button @click="paletteOpen=!paletteOpen" :aria-expanded="paletteOpen">＋ Agregar elemento</button>
            <button v-if="selectedItem" @click="propsOpen=!propsOpen" :aria-expanded="propsOpen">Propiedades</button>
          </div>

          <aside class="cr-palette" v-if="mode==='edit' && paletteOpen">
            <div class="cr-tools">
              <button v-for="(label, kind) in toolNames" :key="kind" class="cr-tool" :data-kind="kind" :aria-pressed="tool===kind" @click="pickTool(kind)">
                <span class="cr-toolicon" aria-hidden="true" v-html="toolIcon(kind)"></span>
                <span class="cr-toollabel">{{ label }}</span>
              </button>
            </div>
            <p>Toca una pieza y luego toca su destino en el plano, o arrastra una pieza existente.</p>
          </aside>

          <div class="cr-canvas" ref="canvasEl" @click="onCanvasClick">
            <svg ref="svgEl" viewBox="0 0 1920 1080" class="cr-map" role="group" aria-label="Plano del salón" @pointerdown="onSvgPointerDown"></svg>
          </div>
        </section>

        <aside class="cr-drawer" v-show="drawerVisible">
          <button class="cr-close" @click="closeDrawer" aria-label="Cerrar panel">Cerrar ×</button>
          <div class="cr-details">
            <template v-if="mode==='edit'">
              <h2>Propiedades</h2>
              <small>{{ selectedTypeName }}</small>
              <label>Nombre<input :value="selectedItem ? selectedItem.name : ''" maxlength="40" @change="onNameChange($event)"></label>
              <label>Área<select :value="selectedItem ? selectedItem.room : room" @change="onRoomChangePiece($event)">
                <option v-for="r in rooms" :key="r.id" :value="r.id">{{ r.name }}</option>
              </select></label>
              <template v-if="selectedItem && selectedItem.type==='table'">
                <label>Lugares<input :value="selectedItem.capacity" type="number" min="1" max="12" @change="onCapChange($event)"></label>
                <label>Forma<select :value="selectedItem.shape" @change="onShapeChange($event)">
                  <option value="rect">Rectangular</option><option value="round">Redonda</option>
                </select></label>
              </template>
              <button class="cr-danger" @click="removeSelected">Quitar del croquis</button>
            </template>
            <template v-else>
              <small>{{ selectedItem ? selectedItem.room : room }}</small>
              <h2>{{ selectedItem ? selectedItem.name : '—' }}</h2>
              <dl v-if="selectedTable">
                <dt>Estado</dt><dd>{{ selectedTable.status }}</dd>
                <dt>Capacidad</dt><dd>{{ selectedTable.capacity }}</dd>
                <dt>Comensales</dt><dd>{{ selectedTable.current_guests || '—' }}</dd>
                <dt>Mesero</dt><dd>{{ selectedTable.current_waiter || '—' }}</dd>
                <dt>Cuenta</dt><dd>{{ selectedTable.current_session ? 'Abierta' : '—' }}</dd>
              </dl>
              <label v-if="selectedTable" class="cr-waiter">Asignar mesero
                <select :value="selectedTable.current_waiter || ''" @change="assignWaiter(selectedTable, $event.target.value)">
                  <option value="">Sin mesero</option>
                  <option v-for="w in waiters" :key="w.name" :value="w.name">{{ w.full_name }}</option>
                </select>
              </label>
              <p v-else-if="selectedItem">{{ selectedTypeName }} del croquis.</p>
              <div class="cr-actions">
                <button v-if="selectedTable && selectedTable.status==='Ocupada'" class="cr-primary" @click="openPOS(selectedTable)">Ver cuenta en POS</button>
                <button v-if="selectedTable && selectedTable.status==='Disponible'" class="cr-primary" @click="openPOS(selectedTable)">Abrir mesa</button>
                <button v-if="selectedTable && selectedTable.status==='Disponible'" @click="reserveDialog(selectedTable)">Reservar</button>
                <button v-if="selectedTable && selectedTable.status==='Reservada'" @click="setStatus(selectedTable, 'Disponible')">Cancelar reserva</button>
                <button v-if="selectedTable && selectedTable.status==='Ocupada'" @click="setStatus(selectedTable, 'Limpieza')">Pasar a limpieza</button>
                <button v-if="selectedTable && selectedTable.status==='Limpieza'" class="cr-primary" @click="setStatus(selectedTable, 'Disponible')">Marcar disponible</button>
              </div>
            </template>
          </div>
        </aside>
      </div>

      <section class="cr-extra" v-if="mode==='summary'">
        <h2>Atención en mesas</h2>

        <div class="cr-lists">
          <div class="cr-listbox" v-if="waitingList.length">
            <h3>En espera · {{ waitingList.length }}</h3>
            <button v-for="t in waitingList" :key="t.name" class="cr-tablerow" @click="openTableFromDashboard(t)">{{ t.name }} · {{ t.room }}<small>{{ t.current_waiter || 'Sin mesero' }} · {{ t.current_guests || 0 }} com.</small></button>
          </div>
          <div class="cr-listbox" v-if="occupiedList.length">
            <h3>En mesa · {{ occupiedList.length }}</h3>
            <button v-for="t in occupiedList" :key="t.name" class="cr-tablerow" @click="openTableFromDashboard(t)">{{ t.name }} · {{ t.room }}<small>{{ t.current_waiter || 'Sin mesero' }} · {{ t.current_guests || 0 }} com.</small></button>
          </div>
        </div>

        <h3>Ocupación por área</h3>
        <div class="cr-rows">
          <button v-for="r in rooms" :key="r.id" class="cr-roomcard" @click="enterRoom(r.id)">
            {{ r.name }}<strong>{{ busyIn(r.id) }} / {{ tablesIn(r.id) }}</strong>mesas ocupadas
          </button>
        </div>
      </section>

      <section class="cr-extra" v-if="mode==='operate'">
        <h2>Mesas del área</h2>
        <input v-model="query" class="cr-find" aria-label="Buscar mesa o mesero" placeholder="Buscar mesa o mesero">
        <div class="cr-rows" v-if="searchResults.length">
          <button v-for="t in searchResults" :key="t.name" class="cr-tablerow" @click="selectTable(t)">
            {{ t.name }} · {{ t.status }}<small>{{ t.current_waiter || 'Sin mesero' }}</small>
          </button>
        </div>
        <p v-else class="cr-muted">Sin coincidencias.</p>
      </section>
    </main>

    <div class="cr-toast" role="status">{{ notice }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { call } from "@/utils/apiWrapper";

const router = useRouter();
const rooms = ref([]);
const tables = ref([]);
const room = ref("");
const mode = ref("operate");
const notice = ref("");
const query = ref("");
const selected = ref(null);
const propsOpen = ref(false);
const paletteOpen = ref(false);
const tool = ref("");
const dirty = ref(false);
const history = ref([]);
const zoomLevel = ref(1);
const furniture = ref([]);
const waiters = ref([]);

const svgEl = ref(null);
const canvasEl = ref(null);

const FURN_KEY = "altoplano.croquis.furniture.v2";
const TONES = { free: "#f5f5e9", busy: "#fbd4af", reserved: "#d9eaf5", clean: "#e0e2df" };
const STATUS2KEY = { Disponible: "free", Ocupada: "busy", Reservada: "reserved", Limpieza: "clean" };
const KEY2LABEL = { free: "Disponible", busy: "Ocupada", reserved: "Reservada", clean: "Limpieza" };
const SHAPE2KEY = { Rectangular: "rect", Cuadrada: "rect", Redonda: "round", Ovalada: "round" };
const KEY2SHAPE = { rect: "Rectangular", round: "Redonda" };
const toolNames = { table: "Mesa", wall: "Muro", door: "Puerta", cash: "Caja", bar: "Barra", kitchen: "Cocina", bath: "Baños", plant: "Jardinera" };
const typeNames = { table: "Mesa", wall: "Muro", door: "Puerta", cash: "Caja", bar: "Barra", kitchen: "Cocina", bath: "Baños", plant: "Jardinera" };

function shapeSVG(kind) {
  const s = {
    wall: '<rect x="-120" y="-12" width="240" height="24" fill="url(#cr-hatch)"/>',
    door: '<path d="M-64 0v-76a76 76 0 0 1 76 76" fill="none"/><path d="M-64 0h76" stroke-dasharray="8 6"/>',
    cash: '<path d="M-112 30v-60h36V-10h188v68H-112Z" fill="#ebdfc8"/><rect x="-14" y="-54" width="58" height="36" rx="4"/><path d="M14 -18v10m-20 0h40"/>',
    bar: '<rect x="-126" y="-56" width="252" height="50" rx="6" fill="#e4d8c7"/><circle cx="-80" cy="22" r="20"/><circle cy="22" r="20"/><circle cx="80" cy="22" r="20"/>',
    kitchen: '<rect x="-116" y="-52" width="232" height="92" rx="6" fill="#e4e7dc"/><rect x="-96" y="-40" width="76" height="66"/><circle cx="-58" cy="-8" r="18"/><path d="M6 -34h88M6 -16h88M6 2h88M6 20h88"/>',
    bath: '<rect x="-88" y="-54" width="176" height="96" rx="8"/><path d="M0 -52v94"/><ellipse cx="-42" cy="-2" rx="18" ry="28"/><ellipse cx="42" cy="-2" rx="18" ry="28"/>',
    plant: '<rect x="-68" y="-34" width="136" height="68" rx="10" fill="#d6dbc8"/><path d="M-46 16q-32-60 18-22q28-48 24 2q40-44 30 2q44-30 30 12" fill="#afbd9c"/>'
  };
  return s[kind] || s.wall;
}

function tableArt(it) {
  const n = it.capacity || 4;
  const r = it.shape === "round" ? 76 : 104;
  let chairs = "";
  for (let i = 0; i < n; i++) {
    const a = 2 * Math.PI * (i + 0.5) / n;
    const cx = Math.cos(a) * r, cy = Math.sin(a) * 68;
    const deg = a * 180 / Math.PI + 90;
    chairs += '<rect x="-18" y="-10" width="36" height="20" rx="8" transform="translate(' + cx + ' ' + cy + ') rotate(' + deg + ')" fill="#eee8dd"/>';
  }
  const fill = TONES[it.key] || "#fffaf1";
  const body = it.shape === "round" ? '<ellipse rx="74" ry="60"' : '<rect x="-96" y="-52" width="192" height="104" rx="16"';
  return chairs + body + ' fill="' + fill + '" stroke="#384137" stroke-width="4"/>';
}

function toolIcon(kind) {
  const shapes = {
    wall: '<rect x="-60" y="-6" width="120" height="12" fill="#d7d8cf"/>',
    door: '<path d="M-32 0v-38a38 38 0 0 1 38 38" fill="none"/><path d="M-32 0h38" stroke-dasharray="4 3"/>',
    cash: '<path d="M-56 15v-30h18V-5h94v34H-56Z" fill="#ebdfc8"/><rect x="-7" y="-27" width="29" height="18" rx="2"/><path d="M7 -9v5m-10 0h20"/>',
    bar: '<rect x="-63" y="-28" width="126" height="25" rx="3" fill="#e4d8c7"/><circle cx="-40" cy="11" r="10"/><circle cy="11" r="10"/><circle cx="40" cy="11" r="10"/>',
    kitchen: '<rect x="-58" y="-26" width="116" height="46" rx="3" fill="#e4e7dc"/><rect x="-48" y="-20" width="38" height="33"/><circle cx="-29" cy="-4" r="9"/><path d="M3 -17h44M3 -8h44M3 1h44M3 10h44"/>',
    bath: '<rect x="-44" y="-27" width="88" height="48" rx="4"/><path d="M0 -26v47"/><ellipse cx="-21" cy="-1" rx="9" ry="14"/><ellipse cx="21" cy="-1" rx="9" ry="14"/>',
    plant: '<rect x="-34" y="-17" width="68" height="34" rx="5" fill="#d6dbc8"/><path d="M-23 8q-16-30 9-11q14-24 12 1q20-22 15 1q22-15 15 6" fill="#afbd9c"/>'
  };
  let art;
  if (kind === "table") {
    art = "";
    for (let i = 0; i < 4; i++) {
      const a = 2 * Math.PI * (i + 0.5) / 4;
      const cx = Math.cos(a) * 52, cy = Math.sin(a) * 34;
      const deg = a * 180 / Math.PI + 90;
      art += '<rect x="-9" y="-5" width="18" height="10" rx="4" transform="translate(' + cx + ' ' + cy + ') rotate(' + deg + ')" fill="#eee8dd"/>';
    }
    art += '<rect x="-48" y="-26" width="96" height="52" rx="8" fill="#f5f5e9" stroke="#384137" stroke-width="2"/>';
  } else {
    art = shapes[kind] || shapes.wall;
  }
  return '<svg viewBox="-72 -48 144 96" aria-hidden="true" width="52" height="36"><g fill="#fff" stroke="#414a3f" stroke-width="4">' + art + '</g></svg>';
}

const modeTitle = computed(() => ({ operate: "Atender mesas", edit: "Acomodar el salón", summary: "Atención en mesas" })[mode.value]);
const activeRoomName = computed(() => { const r = rooms.value.find(x => x.id === room.value); return r ? r.name : "Salones"; });
const tableCount = computed(() => tables.value.filter(t => t.room === room.value).length);
const searchResults = computed(() => {
  const q = query.value.trim().toLowerCase();
  return tables.value.filter(t => t.room === room.value && (!q || (t.name + " " + (t.current_waiter || "")).toLowerCase().includes(q)));
});
const tablesIn = (rid) => tables.value.filter(t => t.room === rid).length;
const busyIn = (rid) => tables.value.filter(t => t.room === rid && t.status === "Ocupada").length;
const countStatus = (status) => tables.value.filter(t => t.status === status).length;
const totalGuests = computed(() => tables.value.reduce((s, t) => s + (Number(t.current_guests) || 0), 0));
const waitingList = computed(() => tables.value.filter(t => t.status === "Reservada"));
const occupiedList = computed(() => tables.value.filter(t => t.status === "Ocupada"));
const alerts = computed(() => {
  const a = [];
  const clean = tables.value.filter(t => t.status === "Limpieza").length;
  if (clean > 0) a.push({ kind: "warn", text: clean + " mesa(s) por liberar" });
  const occNoWaiter = tables.value.filter(t => t.status === "Ocupada" && !t.current_waiter).length;
  if (occNoWaiter > 0) a.push({ kind: "danger", text: occNoWaiter + " mesa(s) ocupada(s) sin mesero" });
  const reserved = tables.value.filter(t => t.status === "Reservada").length;
  if (reserved > 0) a.push({ kind: "info", text: reserved + " reserva(s) en espera" });
  return a;
});

// items unificados (mesas del backend + mobiliario local)
const items = computed(() => {
  const list = [];
  for (const t of tables.value) {
    if (t.room !== room.value) continue;
    list.push({ id: t.name, type: "table", room: t.room, name: t.name, capacity: t.capacity, shape: SHAPE2KEY[t.shape] || "rect", key: STATUS2KEY[t.status] || "free", status: t.status, x: pctToX(t.position_x), y: pctToY(t.position_y), rotation: 0 });
  }
  for (const f of furniture.value) {
    if (f.room !== room.value) continue;
    list.push(f);
  }
  return list;
});

const selectedItem = computed(() => items.value.find(i => i.id === selected.value) || null);
const selectedTable = computed(() => { const s = selected.value; return s ? (tables.value.find(t => t.name === s) || null) : null; });
const selectedTypeName = computed(() => selectedItem.value ? (typeNames[selectedItem.value.type] || "Elemento") : "Elemento");
const drawerVisible = computed(() => mode.value !== "summary" && propsOpen.value && !!selectedItem.value);

function pctToX(p) { return 60 + (Number(p || 50) / 100) * 1800; }
function pctToY(p) { return 60 + (Number(p || 50) / 100) * 960; }
function xToPct(x) { return (x - 60) / 1800 * 100; }
function yToPct(y) { return (y - 60) / 960 * 100; }

function toast(m) { notice.value = m; setTimeout(() => { notice.value = ""; }, 4500); }

async function load() {
  try {
    rooms.value = (await call("pos_restaurant.api.get_rooms", {})) || [];
    tables.value = (await call("pos_restaurant.api.get_tables", {})) || [];
    try { waiters.value = (await call("pos_restaurant.api.get_waiters", {})) || []; } catch (e) { waiters.value = []; }
    if (rooms.value.length && !room.value) room.value = rooms.value[0].name;
    furniture.value = loadFurniture();
  } catch (e) { toast("No se pudieron cargar las mesas"); }
}

function loadFurniture() {
  try {
    const raw = localStorage.getItem(FURN_KEY);
    return raw ? JSON.parse(raw) : seedFurniture();
  } catch (e) { return []; }
}
function saveFurniture() {
  try { localStorage.setItem(FURN_KEY, JSON.stringify(furniture.value)); } catch (e) {}
}
function uid() { return (globalThis.crypto && crypto.randomUUID) ? crypto.randomUUID() : "f" + Date.now().toString(36) + Math.random().toString(36).slice(2); }
function seedFurniture() {
  const seed = [];
  const first = rooms.value[0] ? rooms.value[0].name : "Salon Principal";
  if (first) {
    seed.push({ id: uid(), type: "cash", name: "Caja central", room: first, x: 960, y: 900, rotation: 0 });
    seed.push({ id: uid(), type: "kitchen", name: "Cocina", room: first, x: 260, y: 220, rotation: 0 });
    seed.push({ id: uid(), type: "bath", name: "Baños", room: first, x: 250, y: 520, rotation: 0 });
    seed.push({ id: uid(), type: "bar", name: "Barra", room: first, x: 260, y: 820, rotation: 0 });
    seed.push({ id: uid(), type: "wall", name: "División", room: first, x: 440, y: 260, rotation: 90 });
    seed.push({ id: uid(), type: "wall", name: "División", room: first, x: 440, y: 700, rotation: 90 });
    seed.push({ id: uid(), type: "door", name: "Paso", room: first, x: 450, y: 470, rotation: 0 });
    seed.push({ id: uid(), type: "plant", name: "Jardinera", room: first, x: 1560, y: 880, rotation: 0 });
  }
  for (const r of rooms.value.slice(1)) {
    seed.push({ id: uid(), type: "bar", name: "Estación de servicio", room: r.name, x: 1400, y: 800, rotation: 0 });
    seed.push({ id: uid(), type: "plant", name: "Jardinera", room: r.name, x: 320, y: 240, rotation: 0 });
  }
  return seed;
}

function setMode(m) {
  if (mode.value === "edit" && dirty.value && m !== "edit" && !confirm("Guarda el croquis o deshaz los cambios antes de salir.")) return;
  mode.value = m; selected.value = null; propsOpen.value = false; paletteOpen.value = false; tool.value = "";
}
function onRoomChange() { selected.value = null; propsOpen.value = false; tool.value = ""; }
function enterRoom(rid) { room.value = rid; mode.value = "operate"; selected.value = null; propsOpen.value = false; }
function selectTable(t) { selected.value = t.name; propsOpen.value = true; }
function openTableFromDashboard(t) { enterRoom(t.room); selectTable(t); }
function pickTool(k) { tool.value = tool.value === k ? "" : k; }
function closeDrawer() { propsOpen.value = false; selected.value = null; }
function zoom(dir) { if (dir === 0) zoomLevel.value = 1; else zoomLevel.value = Math.max(1, Math.min(3, zoomLevel.value + dir * 0.5)); }

function svgPoint(e) {
  const pt = new DOMPoint(e.clientX, e.clientY);
  const m = svgEl.value && svgEl.value.getScreenCTM();
  return m ? pt.matrixTransform(m.inverse()) : pt;
}

function renderSvg() {
  if (!svgEl.value) return;
  const defs = '<defs><pattern id="cr-hatch" width="14" height="14" patternUnits="userSpaceOnUse"><rect width="14" height="14" fill="#d7d8cf"/><path d="M0 14l14-14" stroke="#626959"/></pattern></defs>';
  const perimeter = '<path d="M900 1020H60V60H1860V1020H1020" fill="none" stroke="#353e34" stroke-width="12"/><path d="M900 1020v-60a60 60 0 0 1 120 0v60" fill="none" stroke="#8c9286" stroke-width="3"/><text x="960" y="1050" text-anchor="middle" fill="#6f513c" font-size="26">↑ Entrada</text>';
  let body = "";
  for (const it of items.value) {
    const sel = it.id === selected.value;
    const outline = sel ? '<rect class="cr-outline" x="-136" y="-100" width="272" height="220" rx="16" fill="rgba(255,230,207,0.35)" stroke="#c45112" stroke-dasharray="10 6"></rect>' : "";
    const art = it.type === "table" ? tableArt(it) : shapeSVG(it.type);
    const labelY = it.type === "table" ? 6 : 92;
    const statusLine = it.type === "table" ? '<text y="38" font-size="20">' + esc(KEY2LABEL[it.key] || "") + '</text>' : "";
    body += '<g class="cr-piece" data-id="' + esc(it.id) + '" transform="translate(' + it.x + ' ' + it.y + ')" cursor="pointer" style="touch-action:none;user-select:none;-webkit-user-select:none">' + outline + '<g transform="rotate(' + (it.rotation || 0) + ')" fill="#fffdf7" stroke="#384137" stroke-width="4">' + art + '</g><g text-anchor="middle" fill="#20281f" font-weight="700" style="paint-order:stroke;stroke:#fffaf2;stroke-width:6px"><text y="' + labelY + '" font-size="28">' + esc(shortName(it.name)) + '</text>' + statusLine + '</g></g>';
  }
  // rotor de rotación (solo mobiliario, no mesa)
  if (mode.value === "edit" && selectedItem.value && selectedItem.value.type !== "table") {
    const p = selectedItem.value;
    body += '<g class="cr-rotor" data-id="' + esc(p.id) + '" transform="translate(' + (p.x + 108) + ' ' + (p.y - 88) + ')" cursor="grab" style="touch-action:none"><circle r="44" fill="#ffffff" stroke="#193c76" stroke-width="4"/><text text-anchor="middle" y="12" fill="#193c76" font-weight="bold" font-size="40">⟳</text></g>';
  }
  svgEl.value.innerHTML = defs + perimeter + body;
  svgEl.value.setAttribute("preserveAspectRatio", "xMidYMid meet");
  const z = (zoomLevel.value * 100) + "%";
  svgEl.value.style.width = z;
  svgEl.value.style.height = z;
}

function shortName(n) { return (n && n.length > 18) ? n.slice(0, 17) + "…" : (n || ""); }
function esc(v) { return String(v == null ? "" : v).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }

// ---- interacción: arrastrar, girar, colocar ----
let drag = null;
function onSvgPointerDown(e) {
  if (e.button !== 0) return;
  const rotor = e.target.closest(".cr-rotor");
  if (mode.value === "edit" && rotor) { startRotate(e, rotor); return; }
  const piece = e.target.closest(".cr-piece");
  if (mode.value === "edit" && piece) { startMove(e, piece); return; }
}
function startMove(e, pieceEl) {
  const id = pieceEl.dataset.id;
  const it = items.value.find(i => i.id === id);
  if (!it) return;
  e.preventDefault();
  const pt = svgPoint(e);
  drag = { kind: "move", it, startX: e.clientX, startY: e.clientY, dx: pt.x - it.x, dy: pt.y - it.y, moved: false, pointerId: e.pointerId, el: pieceEl };
  if (pieceEl.setPointerCapture) pieceEl.setPointerCapture(e.pointerId);
}
function startRotate(e, rotorEl) {
  const id = rotorEl.dataset.id;
  const it = items.value.find(i => i.id === id);
  if (!it) return;
  e.preventDefault();
  drag = { kind: "rotate", it, startX: e.clientX, startY: e.clientY, moved: true, pointerId: e.pointerId, el: rotorEl, origin: it.rotation || 0 };
  if (rotorEl.setPointerCapture) rotorEl.setPointerCapture(e.pointerId);
}
function rotateAngle(e) {
  const p = drag.it;
  const pt = svgPoint(e);
  return (Math.atan2(pt.y - p.y, pt.x - p.x) * 180 / Math.PI + 90 + 360) % 360;
}
function onPointerMove(e) {
  if (!drag || e.pointerId !== drag.pointerId) return;
  if (drag.kind === "rotate") {
    const val = Math.round(rotateAngle(e));
    drag.it.rotation = ((val % 360) + 360) % 360;
    renderSvg();
    return;
  }
  const dx = e.clientX - drag.startX, dy = e.clientY - drag.startY;
  if (!drag.moved && Math.hypot(dx, dy) < 5) return;
  drag.moved = true;
  const pt = svgPoint(e);
  const raw = { x: pt.x - drag.dx, y: pt.y - drag.dy };
  const pos = clampCoord(raw, drag.it.type === "table");
  // mover visualmente sin mutar modelo
  drag.el.setAttribute("transform", "translate(" + pos.x + " " + pos.y + ")");
  drag.pos = pos;
}
function clampCoord(pt, isTable) {
  if (isTable) return { x: Math.max(pctToX(8), Math.min(pctToX(92), Math.round(pt.x / 5) * 5)), y: Math.max(pctToY(12), Math.min(pctToY(85), Math.round(pt.y / 5) * 5)) };
  return { x: Math.max(60, Math.min(1860, Math.round(pt.x / 5) * 5)), y: Math.max(60, Math.min(1020, Math.round(pt.y / 5) * 5)) };
}
function onPointerUp(e) {
  if (!drag || e.pointerId !== drag.pointerId) return;
  const d = drag; drag = null;
  if (d.kind === "rotate") { dirty.value = true; return; }
  if (!d.moved || !d.pos) return;
  if (d.it.type === "table") {
    const pctX = Math.round(xToPct(d.pos.x) * 10) / 10, pctY = Math.round(yToPct(d.pos.y) * 10) / 10;
    const t = tables.value.find(x => x.name === d.it.id);
    if (t) { t.position_x = pctX; t.position_y = pctY; }
    call("pos_restaurant.api.update_table", { name: d.it.id, x: pctX, y: pctY }).catch(() => toast("No se pudo mover la mesa"));
    selected.value = d.it.id;
  } else {
    pushHistory();
    d.it.x = d.pos.x; d.it.y = d.pos.y;
    dirty.value = true;
    selected.value = d.it.id;
  }
  renderSvg();
}

function onCanvasClick(e) {
  const node = e.target.closest("[data-id]");
  if (node) {
    const id = node.dataset.id;
    selected.value = id;
    if (mode.value !== "edit") propsOpen.value = true;
    tool.value = "";
    renderSvg();
    return;
  }
  if (mode.value === "edit" && tool.value) {
    const pt = svgPoint(e);
    if (pt.x >= 60 && pt.x <= 1860 && pt.y >= 60 && pt.y <= 1020) addPieceAt(tool.value, pt);
  }
}

function addPieceAt(kind, pt) {
  const isTable = kind === "table";
  const pos = clampCoord(pt, isTable);
  if (isTable) { newTableDialog(pos); return; }
  pushHistory();
  let n = 1, name;
  do { name = typeNames[kind] + " " + String(n++).padStart(2, "0"); } while (furniture.value.some(i => i.name === name));
  const p = { id: uid(), type: kind, name, room: room.value, x: pos.x, y: pos.y, rotation: 0 };
  furniture.value.push(p);
  dirty.value = true; selected.value = p.id;
  renderSvg();
  toast("Elemento agregado.");
}

function newTableDialog(pos) {
  const name = prompt("Nombre de la mesa (ej. M-08):", "");
  if (name == null || !name.trim()) return;
  const cap = Number(prompt("Capacidad (1-12):", "4"));
  if (!Number.isInteger(cap) || cap < 1 || cap > 12) return toast("Capacidad entre 1 y 12.");
  const pctX = Math.round(xToPct(pos.x) * 10) / 10, pctY = Math.round(yToPct(pos.y) * 10) / 10;
  call("pos_restaurant.api.create_table", { name: name.trim(), room: room.value, capacity: cap, shape: "rect", x: pctX, y: pctY })
    .then(() => { load(); toast("Mesa agregada."); })
    .catch(() => toast("No se pudo agregar la mesa."));
}

function pushHistory() { history.value.push(JSON.parse(JSON.stringify(furniture.value))); if (history.value.length > 50) history.value.shift(); }
function undo() {
  const prev = history.value.pop();
  if (!prev) return;
  furniture.value = prev;
  dirty.value = history.value.length > 0;
  renderSvg();
  toast("Cambio deshecho.");
}
function save() { saveFurniture(); dirty.value = false; history.value = []; toast("Croquis guardado."); }

function onNameChange(e) {
  const p = selectedItem.value;
  const name = e.target.value.trim();
  if (!name) { renderSvg(); return; }
  if (p.type === "table") { toast("El nombre de la mesa se edita desde el maestro de mesas."); renderSvg(); return; }
  if (furniture.value.some(i => i.id !== p.id && i.name === name)) { toast("Usa un nombre único."); renderSvg(); return; }
  p.name = name; dirty.value = true; renderSvg();
}
function onRoomChangePiece(e) {
  const p = selectedItem.value;
  if (p.type === "table") { toast("Traslada la mesa desde el maestro."); return; }
  p.room = e.target.value; dirty.value = true; renderSvg();
}
function onCapChange(e) {
  const p = selectedItem.value;
  const n = Number(e.target.value);
  if (!Number.isInteger(n) || n < 1 || n > 12) { renderSvg(); return toast("Capacidad entre 1 y 12."); }
  call("pos_restaurant.api.update_table", { name: p.name, capacity: n }).then(() => load());
}
function onShapeChange(e) {
  const p = selectedItem.value;
  call("pos_restaurant.api.update_table", { name: p.name, shape: KEY2SHAPE[e.target.value] }).then(() => load());
}
function removeSelected() {
  const p = selectedItem.value;
  if (!p) return;
  if (p.type === "table") { removeTable(p.name); return; }
  pushHistory();
  furniture.value = furniture.value.filter(i => i.id !== p.id);
  selected.value = null; dirty.value = true; renderSvg();
  toast("Elemento quitado.");
}
async function removeTable(name) {
  if (confirm("¿Eliminar la mesa " + name + " del croquis?")) {
    await call("pos_restaurant.api.remove_table", { name });
    await load(); selected.value = null;
  }
}

async function assignWaiter(t, waiter) {
  try {
    await call("pos_restaurant.api.set_table_waiter", { table_name: t.name, waiter });
    await load();
    toast("Mesero asignado.");
  } catch (e) { toast("No se pudo asignar el mesero."); }
}
async function openPOS(t) {
  try {
    let session = t.current_session;
    if (!session) {
      const s = await call("pos_restaurant.api.open_table", { table_name: t.name, guests: t.current_guests || 1 });
      session = s.name;
    }
    router.push({ path: "/", query: { table: t.name, session: session, room: t.room, waiter: t.current_waiter || "" } });
  } catch (e) { toast("No se pudo abrir la mesa"); }
}
function reserveDialog(t) {
  const guests = prompt("¿Cuántos comensales?", t.current_guests || 1);
  if (guests == null) return;
  const n = Number(guests);
  if (!Number.isInteger(n) || n < 1 || n > (t.capacity || 40)) return toast("Indica entre 1 y " + (t.capacity || 40) + " comensales.");
  call("pos_restaurant.api.set_table_status", { table_name: t.name, status: "Reservada" }).then(() => load());
  toast("Mesa reservada.");
}
async function setStatus(t, status) {
  if (status === "Limpieza" && !confirm("¿Terminó el servicio? Confirma el cobro en el POS antes de liberar la mesa.")) return;
  await call("pos_restaurant.api.set_table_status", { table_name: t.name, status });
  await load(); selected.value = null;
}
function goPOS() { router.push("/"); }

// reactividad: re-render del SVG y del drawer cuando cambia el estado relevante
import { watch } from "vue";
watch([items, selected, mode, zoomLevel, propsOpen, rooms, room], () => { renderSvg(); });

function bind() {
  document.addEventListener("pointermove", onPointerMove, { passive: false });
  document.addEventListener("pointerup", onPointerUp);
  document.addEventListener("pointercancel", () => { drag = null; });
}
function unbind() {
  document.removeEventListener("pointermove", onPointerMove);
  document.removeEventListener("pointerup", onPointerUp);
}

onMounted(() => { load(); renderSvg(); bind(); });
onUnmounted(() => { unbind(); });
</script>

<style scoped>
.cr { height: 100vh; height: 100dvh; min-height: 0; overflow: hidden; display: flex; flex-direction: column; background: #fff; color: #101010; font: 16px/1.45 Inter, Geist, "Segoe UI", sans-serif; }
.cr * { box-sizing: border-box; }
.cr button, .cr input, .cr select { font: inherit; color: inherit; min-height: 44px; border: 1px solid #c8ced6; border-radius: 8px; background: #fff; padding: 7px 12px; max-width: 100%; }
.cr button { cursor: pointer; font-weight: 600; }
.cr button:hover:not(:disabled) { border-color: #193c76; }
.cr button:disabled { opacity: .45; cursor: default; }
.cr button.cr-primary { background: #ff7a00; border-color: #ff7a00; color: #101010; }
.cr button[aria-pressed="true"] { background: #193c76; color: #fff; border-color: #193c76; }
.cr :focus-visible { outline: 3px solid #0073a3; outline-offset: 2px; }
.cr-header { flex: 0 0 auto; background: #fbf8f2; color: #193c76; border-bottom: 1px solid #dce1e6; padding: 8px clamp(12px, 1.5vw, 32px); display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.cr-brand { display: flex; align-items: center; gap: 12px; }
.cr-mark { display: grid; place-items: center; width: 40px; height: 40px; border-radius: 10px; background: #193c76; color: #fff; font-size: 22px; }
.cr-brand strong { display: block; color: #193c76; font-size: 1.02rem; }
.cr-brand small { color: #485564; font-size: .8rem; }
.cr-main { flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; overflow: hidden; width: 100%; max-width: none; margin: 0 auto; padding: 10px clamp(12px, 1.5vw, 24px) 14px; }
.cr-heading { flex: 0 0 auto; display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 8px; }
.cr-heading h1 { font: 650 clamp(1.3rem, 2vw, 1.9rem)/1.1 Inter, Geist, "Segoe UI", sans-serif; color: #193c76; margin: 0; }
.cr-nav { display: flex; gap: 2px; background: #f3f5f7; border-radius: 10px; padding: 3px; }
.cr-nav button { background: transparent; border-color: transparent; }
.cr-nav button[aria-pressed="true"] { background: #193c76; color: #fff; }
.cr-bar { flex: 0 0 auto; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; border-block: 1px solid #dce1e6; padding: 6px 0; }
.cr-bar .cr-counts { color: #485564; margin-right: auto; }
.cr-room { display: flex; align-items: center; gap: 8px; }
.cr-notice { flex: 0 0 auto; min-height: 1.2em; margin: 4px 0; color: #193c76; }
.cr-dash { flex: 0 0 auto; display: flex; flex-direction: column; gap: 8px; padding: 8px 0 2px; }
.cr-dashkpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; }
.cr-dkpi { cursor: pointer; text-align: left; border: 1px solid #dce1e6; border-radius: 12px; padding: 12px 14px; background: #fff; font-weight: 600; }
.cr-dkpi strong { display: block; font-size: 1.9rem; line-height: 1; color: #193c76; }
.cr-dkpi span { color: #485564; font-size: .85rem; font-weight: 650; }
.cr-dkpi-mesa { border-top: 4px solid #ff7a00; }
.cr-dkpi-libre { border-top: 4px solid #16a34a; }
.cr-dkpi-espera { border-top: 4px solid #9333ea; }
.cr-dkpi-limpieza { border-top: 4px solid #2563eb; }
.cr-dkpi-comensales { border-top: 4px solid #0ea5e9; }
.cr-alerts { display: flex; flex-wrap: wrap; gap: 8px; }
.cr-alert { font-weight: 650; font-size: .88rem; padding: 6px 12px; border-radius: 8px; border: 1px solid transparent; }
.cr-alert-danger { background: #fee2e2; color: #b91c1c; border-color: #fecaca; }
.cr-alert-warn { background: #fef3c7; color: #92400e; border-color: #fde68a; }
.cr-alert-info { background: #dbeafe; color: #1e40af; border-color: #bfdbfe; }
.cr-layout { flex: 1 1 auto; min-height: 0; display: flex; align-items: stretch; gap: 14px; }
.cr-board { flex: 1 1 auto; min-width: 0; min-height: 0; display: flex; flex-direction: column; background: #fff; border: 1px solid #dce1e6; border-radius: 12px; overflow: hidden; }
.cr-boardhead { flex: 0 0 auto; display: flex; align-items: center; justify-content: space-between; padding: 8px 14px; }
.cr-boardhead h2 { color: #193c76; margin: 0; font-size: 1.15rem; }
.cr-zoom { display: flex; align-items: center; gap: 8px; }
.cr-zoom button { min-width: 44px; }
.cr-zoom .cr-fit { margin-inline: 4px; padding-inline: 14px; }
.cr-editbar { flex: 0 0 auto; padding: 0 14px 8px; display: flex; gap: 6px; flex-wrap: wrap; }
.cr-palette { flex: 0 0 auto; margin: 0 12px 8px; padding: 8px; background: #f7f8fa; border-radius: 8px; }
.cr-palette p { margin: 6px 2px 0; color: #485564; font-size: .85rem; }
.cr-tools { display: flex; flex-wrap: wrap; gap: 8px; }
.cr-tool { display: flex; flex-direction: column; align-items: center; gap: 6px; min-width: 74px; padding: 8px 6px; }
.cr-toolicon { display: grid; place-items: center; height: 38px; }
.cr-toollabel { font-size: .82rem; font-weight: 600; }
.cr-canvas { flex: 1 1 auto; min-height: 0; overflow: auto; overscroll-behavior: contain; -webkit-overflow-scrolling: touch; background-color: #fbfcfd; background-image: linear-gradient(#cfd5db44 1px, transparent 1px), linear-gradient(90deg, #cfd5db44 1px, transparent 1px); background-size: 24px 24px; border-block: 1px solid #dce1e6; }
.cr-map { display: block; width: 100%; height: 100%; max-width: none; }
.cr-piece { cursor: pointer; touch-action: none; user-select: none; -webkit-user-select: none; }
.cr-piece .cr-outline { fill: #ffe6cf55; stroke: #c45112; stroke-dasharray: 5 3; }
.cr-rotor { cursor: grab; touch-action: none; user-select: none; }
.cr-rotor circle { fill: #fff; stroke: #193c76; stroke-width: 2; }
.cr-rotor text { fill: #193c76; font: bold 22px sans-serif; }
.cr-drawer { width: 250px; max-width: 100%; min-height: 0; overflow: auto; background: #fff; border: 1px solid #dce1e6; border-radius: 12px; padding: 14px; flex-shrink: 0; }
.cr-close { float: right; font-size: .84rem; }
.cr-details h2 { color: #193c76; margin: 6px 0 4px; }
.cr-details small { color: #485564; letter-spacing: .06em; }
.cr-details label { display: grid; gap: 4px; margin: 10px 0; font-size: .9rem; }
.cr-details label.cr-waiter { border-top: 1px solid #dce1e6; padding-top: 10px; }
.cr-details dl { display: grid; grid-template-columns: 1fr auto; gap: 8px; margin: 10px 0; }
.cr-details dt { color: #485564; }
.cr-details dd { margin: 0; font-weight: 650; }
.cr-actions { display: flex; flex-direction: column; gap: 6px; margin-top: 10px; }
.cr-danger { border-color: #c0553a; color: #a4411f; }
.cr-extra { flex: 0 0 auto; margin-top: 10px; overflow: auto; max-height: 45vh; background: #fff; border: 1px solid #dce1e6; border-radius: 12px; padding: 12px 16px; }
.cr-extra h2 { color: #193c76; margin: 0 0 12px; }
.cr-rows { display: flex; gap: 10px; flex-wrap: wrap; }
.cr-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; margin-bottom: 16px; }
.cr-kpi { border: 1px solid #dce1e6; border-radius: 12px; padding: 14px 16px; background: #fff; }
.cr-kpi strong { display: block; font-size: 2rem; line-height: 1; color: #193c76; }
.cr-kpi span { color: #485564; font-size: .85rem; }
.cr-kpi-mesa { border-top: 3px solid #ff7a00; }
.cr-kpi-espera { border-top: 3px solid #9333ea; }
.cr-kpi-libre { border-top: 3px solid #16a34a; }
.cr-kpi-limpieza { border-top: 3px solid #2563eb; }
.cr-kpi-comensales { border-top: 3px solid #0ea5e9; }
.cr-lists { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-bottom: 18px; }
.cr-listbox { border: 1px solid #dce1e6; border-radius: 12px; padding: 12px; }
.cr-listbox h3 { margin: 0 0 8px; color: #193c76; }
.cr-listbox .cr-tablerow { width: 100%; text-align: left; margin-bottom: 4px; }
.cr-extra h3 { margin: 14px 0 8px; color: #193c76; }
.cr-roomcard { text-align: left; flex: 1; min-width: 160px; }
.cr-roomcard strong { display: block; font-size: 1.6rem; color: #193c76; }
.cr-tablerow { display: flex; flex-direction: column; gap: 2px; text-align: left; }
.cr-tablerow small { color: #485564; }
.cr-find { width: 100%; max-width: 360px; }
.cr-muted { color: #485564; }
.cr-toast { position: fixed; bottom: 14px; right: 14px; max-width: 90vw; background: #193c76; color: #fff; padding: 10px 16px; border-radius: 8px; z-index: 20; }
.cr-toast:empty { display: none; }
@media (max-width: 760px) {
  .cr { height: auto; min-height: 100vh; overflow: visible; }
  .cr-main { overflow: visible; }
  .cr-layout { flex: none; }
  .cr-heading { margin-bottom: 12px; }
  .cr-nav { max-width: 100%; }
  .cr-nav button { font-size: .83rem; padding: 5px 8px; }
  .cr-layout { flex-direction: column; }
  .cr-board { min-height: 420px; }
  .cr-canvas { min-height: 320px; }
  .cr-board, .cr-drawer { width: 100%; }
  .cr-drawer { order: 2; }
  .cr-tools { display: grid; grid-template-columns: repeat(3, 1fr); }
  .cr-kpis { grid-template-columns: repeat(2, 1fr); }
  .cr-lists { grid-template-columns: 1fr; }
  .cr-bar { gap: 5px; }
  .cr-boardhead { padding: 8px 12px; }
  .cr-extra { max-height: none; }
}
</style>
