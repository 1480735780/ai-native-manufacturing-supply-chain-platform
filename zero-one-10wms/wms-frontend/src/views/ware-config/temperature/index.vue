<script lang="ts" setup>
import { listTemperatures, addTemperature, updateTemperature, deleteTemperature,
	importTemperature, exportTemperature, } from "@/apis/ware-config/index.js";
import DictPage from "../components/DictPage.vue";
import type { DictPageOptions } from "../composables/use-dict-page";
import { Sunny } from "@element-plus/icons-vue";

definePage({
	meta: {
		menuType: "page",
		text: "温度属性",
		icon: Sunny,
	},
});

const options: DictPageOptions = {
	title: "温度属性",
	columns: [
		{ label: "温层代码", prop: "deg_type_code", width: 180 },
		{ label: "温层名称", prop: "deg_type_name" },
	],
	queryFields: [
		{ prop: "deg_type_code", label: "温层代码" },
		{ prop: "deg_type_name", label: "温层名称" },
	],
	addFields: [
		{ prop: "deg_type_code", label: "温层代码" },
		{ prop: "deg_type_name", label: "温层名称" },
	],
	editFields: [
		{ prop: "deg_type_code", label: "温层代码" },
		{ prop: "deg_type_name", label: "温层名称" },
	],
	listApi: listTemperatures,
	addApi: addTemperature,
	updateApi: updateTemperature,
	deleteApi: deleteTemperature,
	importApi: importTemperature,
	exportApi: exportTemperature.bind(null, "temperature.xlsx"),
	exportFileName: "温度属性",
};
</script>

<template>
	<DictPage :options="options" />
</template>
