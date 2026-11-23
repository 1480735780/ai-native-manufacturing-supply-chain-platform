<script lang="ts" setup>
import DictCrudTable from "../components/DictCrudTable.vue";
import {
	listCostMethod,
	addCostMethod,
	modifyCostMethod,
	removeCostMethods,
	exportCostMethods,
	importCostMethods,
	pickPage,
} from "@/apis/billing/index";

definePage({
	meta: {
		menuType: "page",
		text: "计费方式",
		icon: "IconSetting",
	},
});

/** 后端 /cost-config/cost-method/query 无分页参数，做客户端分页兼容 */
const page = async (params: Record<string, any>) => {
	const payload = await listCostMethod({});
	const { rows } = pickPage(payload);
	const code = String(params.pronut_code ?? "").trim();
	const name = String(params.pronut_name ?? "").trim();
	const filtered = rows.filter(
		(r: any) =>
			(!code || String(r.pronut_code ?? "").includes(code)) &&
			(!name || String(r.pronut_name ?? "").includes(name)),
	);
	const size = params.pageSize || 10;
	const start = ((params.pageIndex || 1) - 1) * size;
	return { data: filtered.slice(start, start + size), total: filtered.length };
};

const api = {
	page,
	add: addCostMethod,
	modify: modifyCostMethod,
	remove: removeCostMethods,
	exportExcel: exportCostMethods,
	importExcel: importCostMethods,
};

const columns = [
	{ prop: "pronut_code", label: "计费方式代码", minWidth: 160 },
	{ prop: "pronut_name", label: "计费方式名称", minWidth: 180 },
];
</script>

<template>
	<DictCrudTable
		title="计费方式"
		tip="计费方式基础资料（查询/新增/修改：cost-method；删除/导出/导入：cost-way，同一张 ba_pronut_method）"
		:api="api"
		:columns="columns"
		:search-fields="['pronut_code', 'pronut_name']"
		filename="计费方式.xlsx"
	/>
</template>

<style lang="scss" scoped></style>
