<template>
	<div
		v-if="modelValue"
		class="fixed inset-0 z-[200] flex items-end sm:items-center justify-center bg-black/40"
		@click.self="close"
	>
		<div class="w-full sm:max-w-md bg-white rounded-t-2xl sm:rounded-2xl shadow-xl max-h-[90vh] flex flex-col">
			<div class="flex items-center justify-between px-4 py-3 border-b border-gray-200">
				<h3 class="text-base font-bold text-gray-900 truncate">
					{{ item?.item_name || item?.item_code }}
				</h3>
				<button
					type="button"
					@click="close"
					class="text-gray-600 hover:text-gray-600 p-1 touch-manipulation"
					:aria-label="__('Cerrar')"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
				</button>
			</div>

			<div class="flex-1 overflow-y-auto px-4 py-3 space-y-4">
				<div v-if="loading" class="text-center text-sm text-gray-600 py-6">{{ __("Cargando opciones…") }}</div>

				<div v-else-if="!groups.length" class="text-center text-sm text-gray-600 py-6">{{ __("Sin opciones para este producto.") }}</div>

				<div v-for="grp in groups" :key="grp.group" class="space-y-2">
					<div class="flex items-center justify-between">
						<p class="text-xs font-semibold text-gray-600 uppercase tracking-wide">
							{{ grp.title }}
							<span v-if="grp.is_required" class="text-red-500">*</span>
						</p>
						<p v-if="grp.selection_type === 'Single'" class="text-[10px] text-gray-600">{{ __("Elige uno") }}</p>
					</div>

					<div v-if="grp.selection_type === 'Multiple'" class="space-y-1.5">
						<label
							v-for="opt in grp.options"
							:key="opt.option"
							class="flex items-center justify-between gap-2 bg-gray-50 rounded-lg px-3 py-2 cursor-pointer"
						>
							<div class="flex items-center gap-2 flex-1 min-w-0">
								<input
									type="checkbox"
									:checked="multipleSelected(grp.group, opt.option)"
									@change="toggleMultiple(grp, opt)"
									class="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
								/>
								<span class="text-sm text-gray-800 truncate">{{ opt.option }}</span>
							</div>
							<span v-if="opt.price_delta" class="text-xs font-semibold text-emerald-600 flex-shrink-0">+${{ opt.price_delta }}</span>
						</label>
					</div>

					<div v-else class="space-y-1.5">
						<label
							v-for="opt in grp.options"
							:key="opt.option"
							class="flex items-center justify-between gap-2 bg-gray-50 rounded-lg px-3 py-2 cursor-pointer"
						>
							<div class="flex items-center gap-2 flex-1 min-w-0">
								<input
									type="radio"
									:name="'mod-' + grp.group"
									:checked="singleSelected(grp.group, opt.option)"
									@change="selectSingle(grp, opt)"
									class="w-4 h-4 text-blue-600 focus:ring-blue-500"
								/>
								<span class="text-sm text-gray-800 truncate">{{ opt.option }}</span>
							</div>
							<span v-if="opt.price_delta" class="text-xs font-semibold text-emerald-600 flex-shrink-0">+${{ opt.price_delta }}</span>
						</label>
					</div>
				</div>

				<div>
					<p class="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">{{ __("Comentario") }}</p>
					<textarea
						v-model="note"
						rows="2"
						class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
						:placeholder="__('Ej. sin picante, bien cocido…')"
					></textarea>
				</div>
			</div>

			<div class="px-4 py-3 border-t border-gray-200 flex gap-2">
				<button
					type="button"
					@click="close"
					class="flex-1 py-2.5 rounded-lg text-sm font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 active:scale-[0.98] touch-manipulation"
				>{{ __("Cancelar") }}</button>
				<button
					type="button"
					@click="save"
					class="flex-1 py-2.5 rounded-lg text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 active:scale-[0.98] touch-manipulation"
				>{{ __("Guardar") }}</button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, watch } from "vue";
import { call } from "@/utils/apiWrapper";

const props = defineProps({
	modelValue: { type: Boolean, default: false },
	item: { type: Object, default: null },
});
const emit = defineEmits(["update:modelValue", "save"]);

const loading = ref(false);
const groups = ref([]);
const note = ref("");
const selections = ref({});

watch(
	() => props.item,
	async (item) => {
		if (!item) return;
		note.value = item.kitchen_note || "";
		selections.value = selectionsFromItem(item);
		await loadModifiers(item);
	},
	{ immediate: true }
);

function selectionsFromItem(item) {
	const out = {};
	for (const m of item.selected_modifiers || []) {
		if (!m || !m.group) continue;
		if (m.selection_type === "Single") {
			out[m.group] = m.option;
		} else {
			if (!out[m.group]) out[m.group] = [];
			out[m.group].push(m.option);
		}
	}
	return out;
}

async function loadModifiers(item) {
	loading.value = true;
	try {
		groups.value = (await call("pos_restaurant.api.get_modifiers", { item_code: item.item_code })) || [];
		applyDefaults();
	} catch (e) {
		console.error("get_modifiers error", e);
		groups.value = [];
	} finally {
		loading.value = false;
	}
}

function applyDefaults() {
	const next = { ...selections.value };
	for (const grp of groups.value) {
		if (next[grp.group] !== undefined) continue;
		if (grp.selection_type === "Single") {
			const def = grp.options.find((o) => o.default);
			if (def) next[grp.group] = def.option;
		} else {
			const defs = grp.options.filter((o) => o.default).map((o) => o.option);
			if (defs.length) next[grp.group] = defs;
		}
	}
	selections.value = next;
}

function multipleSelected(group, option) {
	return (selections.value[group] || []).includes(option);
}

function toggleMultiple(grp, opt) {
	const cur = selections.value[grp.group] || [];
	selections.value = {
		...selections.value,
		[grp.group]: cur.includes(opt.option) ? cur.filter((o) => o !== opt.option) : [...cur, opt.option],
	};
}

function singleSelected(group, option) {
	return selections.value[group] === option;
}

function selectSingle(grp, opt) {
	selections.value = { ...selections.value, [grp.group]: opt.option };
}

function buildSelected() {
	const out = [];
	for (const grp of groups.value) {
		const sel = selections.value[grp.group];
		if (!sel) continue;
		const names = Array.isArray(sel) ? sel : [sel];
		for (const name of names) {
			const opt = grp.options.find((o) => o.option === name);
			if (!opt) continue;
			out.push({
				group: grp.group,
				selection_type: grp.selection_type,
				option: opt.option,
				price_delta: opt.price_delta || 0,
				ingredient_item: opt.ingredient_item || null,
				ingredient_qty: opt.ingredient_qty || 0,
				ingredient_uom: opt.ingredient_uom || null,
				ingredient_effect: opt.ingredient_effect || "Add",
			});
		}
	}
	return out;
}

function close() {
	emit("update:modelValue", false);
}

function save() {
	emit("save", { selected_modifiers: buildSelected(), kitchen_note: note.value.trim() });
	close();
}
</script>
