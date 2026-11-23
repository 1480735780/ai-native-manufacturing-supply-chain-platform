<script lang="ts" setup>
import { listBussTypes, addBussType, updateBussType, deleteBussType, deleteBussTypeBatch,
	importBussType, exportBussType, } from "@/apis/ware-config/index.js";
import DictPage from "../components/DictPage.vue";
import type { DictPageOptions } from "../composables/use-dict-page";
import { Collection } from "@element-plus/icons-vue";

definePage({
	meta: {
		menuType: "page",
		text: "业务类型",
		icon: Collection,
	},
});

const options: DictPageOptions = {
	title: "业务类型",
	columns: [
		{ label: "业务类型代码", prop: "buss_type_code", width: 180 },
		{ label: "业务类型名称", prop: "buss_type_name" },
	],
	queryFields: [
		{ prop: "buss_type_code", label: "业务类型代码" },
		{ prop: "buss_type_name", label: "业务类型名称" },
	],
	addFields: [
		{ prop: "buss_type_code", label: "业务类型代码" },
		{ prop: "buss_type_name", label: "业务类型名称" },
	],
	editFields: [
		{ prop: "id", label: "唯一标识" },
		{ prop: "buss_type_code", label: "业务类型代码" },
		{ prop: "buss_type_name", label: "业务类型名称" },
	],
	listApi: listBussTypes,
	addApi: addBussType,
	updateApi: updateBussType,
	deleteApi: deleteBussType,
	deleteBatchApi: deleteBussTypeBatch,
	importApi: importBussType,
	exportApi: exportBussType.bind(null, "buss-type.xlsx"),
	exportFileName: "业务类型",
};
</script>

<template>
	<DictPage :options="options" />
</template>
