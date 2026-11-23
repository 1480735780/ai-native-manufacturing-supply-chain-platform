<script lang="ts" setup>
import DictCrudTable from "../components/DictCrudTable.vue";
import {
	listCostTypeAll,
	addCostType,
	modifyCostType,
	removeCostTypes,
	exportCostType,
	importCostType,
	pickPage,
} from "@/apis/billing/index";

definePage({
	meta: {
		menuType: "page",
		text: "费用类型",
		icon: "IconSetting",
	},
});

/**
 * 后端 wms-c4-billingtype 仅提供 /cost-type/all 全量列表（无分页接口），
 * 此处做客户端过滤 + 客户端分页。费用类型为小体量字典，无性能风险。
 */
const page = async (params: Record<string, any>) => {
	const payload = await listCostTypeAll({});
	const { rows } = pickPage(payload);
	const codeKw = String(params.cost_code ?? "").trim();
	const nameKw = String(params.cost_name ?? "").trim();
	const typeKw = String(params.cost_type ?? "").trim();
	const filtered = rows.filter(
		(r: any) =>
			(!codeKw || String(r.cost_code ?? "").includes(codeKw)) &&
			(!nameKw || String(r.cost_name ?? "").includes(nameKw)) &&
			(!typeKw || String(r.cost_type ?? "").includes(typeKw)),
	);
	const size = params.pageSize || 10;
	const start = ((params.pageIndex || 1) - 1) * size;
	return { data: filtered.slice(start, start + size), total: filtered.length };
};

const api = {
	page,
	add: addCostType,
	modify: modifyCostType,
	remove: removeCostTypes,
	exportExcel: exportCostType,
	importExcel: importCostType,
};

const columns = [
	{ prop: "cost_code", label: "费用代码", minWidth: 160 },
	{ prop: "cost_name", label: "费用名称", minWidth: 180 },
	{ prop: "cost_type", label: "费用类型", minWidth: 160 },
	{ prop: "create_name", label: "创建人", width: 120 },
	{ prop: "create_date", label: "创建日期", width: 170 },
];
</script>

<template>
	<DictCrudTable
		title="费用类型"
		tip="费用类型基础资料（来源：wms-c4-billingtype；删除经 wms-c4-billingconfig /rm_more）"
		:api="api"
		:columns="columns"
		:search-fields="['cost_code', 'cost_name', 'cost_type']"
		filename="费用类型.xlsx"
	/>
</template>

<style lang="scss" scoped></style>
