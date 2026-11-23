<script lang="ts" setup>
import { listLibraries, addLibrary, updateLibrary, deleteLibrary,
	importLibrary, exportLibrary, } from "@/apis/ware-config/index.js";
import DictPage from "../components/DictPage.vue";
import type { DictPageOptions } from "../composables/use-dict-page";
import { Grid } from "@element-plus/icons-vue";

definePage({
	meta: {
		menuType: "page",
		text: "库位类型",
		icon: Grid,
	},
});

const options: DictPageOptions = {
	title: "库位类型",
	columns: [
		{ label: "库位类型代码", prop: "bin_type_code", width: 180 },
		{ label: "库位类型名称", prop: "bin_type_name" },
	],
	queryFields: [
		{ prop: "bin_type_code", label: "库位类型代码" },
		{ prop: "bin_type_name", label: "库位类型名称" },
	],
	addFields: [
		{ prop: "bin_type_code", label: "库位类型代码" },
		{ prop: "bin_type_name", label: "库位类型名称" },
	],
	editFields: [
		{ prop: "id", label: "唯一标识" },
		{ prop: "bin_type_code", label: "库位类型代码" },
		{ prop: "bin_type_name", label: "库位类型名称" },
	],
	listApi: listLibraries,
	addApi: addLibrary,
	updateApi: updateLibrary,
	deleteApi: deleteLibrary,
	importApi: importLibrary,
	exportApi: exportLibrary.bind(null, "library.xlsx"),
	exportFileName: "库位类型",
};
</script>

<template>
	<DictPage :options="options" />
</template>
