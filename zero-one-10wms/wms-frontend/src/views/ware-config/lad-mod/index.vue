<script lang="ts" setup>
import { listLadMods, addLadMod, updateLadMod, deleteLadMod, deleteLadModBatch,
	importLadMod, exportLadMod, } from "@/apis/ware-config/index.js";
import DictPage from "../components/DictPage.vue";
import type { DictPageOptions } from "../composables/use-dict-page";
import { Van } from "@element-plus/icons-vue";

definePage({
	meta: {
		menuType: "page",
		text: "提货方式",
		icon: Van,
	},
});

const options: DictPageOptions = {
	title: "提货方式",
	rowKey: "id",
	columns: [
		{ label: "提货方式代码", prop: "code", width: 180 },
		{ label: "提货方式名称", prop: "name" },
	],
	queryFields: [
		{ prop: "code", label: "提货方式代码" },
		{ prop: "name", label: "提货方式名称" },
	],
	addFields: [
		{ prop: "code", label: "提货方式代码" },
		{ prop: "name", label: "提货方式名称" },
	],
	editFields: [
		{ prop: "id", label: "唯一标识" },
		{ prop: "code", label: "提货方式代码" },
		{ prop: "name", label: "提货方式名称" },
	],
	listApi: listLadMods,
	addApi: addLadMod,
	updateApi: updateLadMod,
	deleteApi: deleteLadMod,
	deleteBatchApi: deleteLadModBatch,
	importApi: importLadMod,
	exportApi: exportLadMod,
	exportFileName: "提货方式",
};
</script>

<template>
	<DictPage :options="options" />
</template>
