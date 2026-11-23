<script lang="ts" setup>
import { listActTypes, addActType, updateActType, deleteActType, deleteActTypeBatch,
	importActType, exportActType, } from "@/apis/ware-config/index.js";
import DictPage from "../components/DictPage.vue";
import type { DictPageOptions } from "../composables/use-dict-page";
import { Operation } from "@element-plus/icons-vue";

definePage({
	meta: {
		menuType: "page",
		text: "作业类型",
		icon: Operation,
	},
});

const options: DictPageOptions = {
	title: "作业类型",
	columns: [
		{ label: "作业类型代码", prop: "act_type_code", width: 160 },
		{ label: "作业类型名称", prop: "act_type_name" },
		{ label: "业务环节", prop: "oper_step_code", width: 140 },
	],
	queryFields: [
		{ prop: "act_type_code", label: "作业类型代码" },
		{ prop: "act_type_name", label: "作业类型名称" },
		{ prop: "oper_step_code", label: "业务环节代码" },
	],
	addFields: [
		{ prop: "act_type_code", label: "作业类型代码" },
		{ prop: "act_type_name", label: "作业类型名称" },
		{ prop: "oper_step_code", label: "业务环节代码" },
	],
	editFields: [
		{ prop: "id", label: "唯一标识" },
		{ prop: "act_type_code", label: "作业类型代码" },
		{ prop: "act_type_name", label: "作业类型名称" },
		{ prop: "oper_step_code", label: "业务环节代码" },
	],
	listApi: listActTypes,
	addApi: addActType,
	updateApi: updateActType,
	deleteApi: deleteActType,
	deleteBatchApi: ids => deleteActTypeBatch(ids.join(",")),
	importApi: importActType,
	exportApi: exportActType.bind(null, "act-type.xlsx"),
	exportFileName: "作业类型",
};
</script>

<template>
	<DictPage :options="options" />
</template>
