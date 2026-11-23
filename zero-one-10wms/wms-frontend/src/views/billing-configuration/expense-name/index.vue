<script lang="ts" setup>
import DictCrudTable from "../components/DictCrudTable.vue";
import {
	listCostNamePage,
	addCostName,
	modifyCostName,
	removeCostNames,
	exportCostName,
	importCostName,
} from "@/apis/billing/index";

definePage({
	meta: {
		menuType: "page",
		text: "费用名称",
		icon: "IconSetting",
	},
});

const api = {
	page: listCostNamePage,
	add: addCostName,
	modify: modifyCostName,
	remove: removeCostNames,
	exportExcel: exportCostName,
	importExcel: importCostName,
};

const columns = [
	{ prop: "cost_code", label: "费用编码", minWidth: 160 },
	{ prop: "cost_name", label: "费用名称", minWidth: 180 },
	{ prop: "cost_type_code", label: "费用类型编码", minWidth: 150 },
	{ prop: "create_name", label: "创建人", width: 120 },
	{ prop: "create_date", label: "创建日期", width: 170 },
];
</script>

<template>
	<DictCrudTable
		title="费用名称"
		tip="费用名称基础资料；按「费用类型编码」过滤即为按费用类型查询的名称列表（来源：wms-c4-billingconfig）"
		:api="api"
		:columns="columns"
		:search-fields="['cost_code', 'cost_name', 'cost_type_code']"
		filename="费用名称.xlsx"
	/>
</template>

<style lang="scss" scoped></style>
