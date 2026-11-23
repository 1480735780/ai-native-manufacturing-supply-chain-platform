<script lang="ts" setup>
import DictCrudTable from "../components/DictCrudTable.vue";
import {
	listCostAttributePage,
	addCostAttribute,
	modifyCostAttribute,
	removeCostAttribute,
	exportCostAttribute,
	importCostAttribute,
} from "@/apis/billing/index";

definePage({
	meta: {
		menuType: "page",
		text: "客户计费属性",
		icon: "IconSetting",
	},
});

const api = {
	page: listCostAttributePage,
	add: addCostAttribute,
	modify: modifyCostAttribute,
	remove: removeCostAttribute,
	exportExcel: exportCostAttribute,
	importExcel: importCostAttribute,
};

const columns = [
	{ prop: "code", label: "客户计费属性代码", minWidth: 180 },
	{ prop: "name", label: "客户计费属性名称", minWidth: 180 },
	{ prop: "create_name", label: "创建人", width: 120 },
	{ prop: "create_date", label: "创建日期", width: 170 },
];
</script>

<template>
	<DictCrudTable
		title="客户计费属性"
		tip="客户计费属性基础资料，支持增删改查与导入导出"
		:api="api"
		:columns="columns"
		:search-fields="['code', 'name']"
		filename="客户计费属性.xlsx"
	/>
</template>

<style lang="scss" scoped></style>
