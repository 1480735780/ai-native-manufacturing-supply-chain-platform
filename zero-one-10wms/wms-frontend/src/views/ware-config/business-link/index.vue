<script lang="ts" setup>
import { listBusinessLinks, addBusinessLink, updateBusinessLink, deleteBusinessLink,
	importBusinessLink, exportBusinessLink, } from "@/apis/ware-config/index.js";
import DictPage from "../components/DictPage.vue";
import type { DictPageOptions } from "../composables/use-dict-page";
import { Connection } from "@element-plus/icons-vue";

definePage({
	meta: {
		menuType: "page",
		text: "业务环节",
		icon: Connection,
	},
});

const options: DictPageOptions = {
	title: "业务环节",
	columns: [
		{ label: "业务环节代码", prop: "oper_step_code", width: 180 },
		{ label: "业务环节名称", prop: "oper_step_name" },
	],
	queryFields: [
		{ prop: "oper_step_code", label: "业务环节代码" },
		{ prop: "oper_step_name", label: "业务环节名称" },
	],
	addFields: [
		{ prop: "oper_step_code", label: "业务环节代码" },
		{ prop: "oper_step_name", label: "业务环节名称" },
	],
	editFields: [
		{ prop: "oper_step_code", label: "业务环节代码" },
		{ prop: "oper_step_name", label: "业务环节名称" },
	],
	listApi: listBusinessLinks,
	addApi: addBusinessLink,
	updateApi: updateBusinessLink,
	deleteApi: deleteBusinessLink,
	deleteBatchApi: ids => deleteBusinessLink(ids.join(",")),
	importApi: importBusinessLink,
	exportApi: exportBusinessLink.bind(null, "business-link.xlsx"),
	exportFileName: "业务环节",
};
</script>

<template>
	<DictPage :options="options" />
</template>
