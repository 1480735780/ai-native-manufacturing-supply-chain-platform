<script lang="ts" setup>
import { listOperationTypes, addOperationType, updateOperationType, deleteOperationType,
	deleteOperationTypeBatch, importOperationType, exportOperationType, } from "@/apis/ware-config/index.js";
import DictPage from "../components/DictPage.vue";
import type { DictPageOptions } from "../composables/use-dict-page";
import { SetUp } from "@element-plus/icons-vue";

definePage({
	meta: {
		menuType: "page",
		text: "操作类型",
		icon: SetUp,
	},
});

const options: DictPageOptions = {
	title: "操作类型",
	columns: [
		{ label: "操作类型代码", prop: "code", width: 180 },
		{ label: "操作类型名称", prop: "name" },
	],
	queryFields: [
		{ prop: "code", label: "操作类型代码" },
		{ prop: "name", label: "操作类型名称" },
	],
	addFields: [
		{ prop: "code", label: "操作类型代码" },
		{ prop: "name", label: "操作类型名称" },
	],
	editFields: [
		{ prop: "id", label: "唯一标识" },
		{ prop: "code", label: "操作类型代码" },
		{ prop: "name", label: "操作类型名称" },
	],
	listApi: listOperationTypes,
	addApi: addOperationType,
	updateApi: updateOperationType,
	deleteApi: deleteOperationType,
	deleteBatchApi: deleteOperationTypeBatch,
	importApi: importOperationType,
	exportApi: exportOperationType.bind(null, "operation-type.xlsx"),
	exportFileName: "操作类型",
};
</script>

<template>
	<DictPage :options="options" />
</template>
