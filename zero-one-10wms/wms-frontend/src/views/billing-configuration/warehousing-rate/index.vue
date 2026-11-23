<script lang="ts" setup>
import DictCrudTable from "../components/DictCrudTable.vue";
import { storageRateApi, getStorageRateDetail } from "@/apis/billing/index";

definePage({
	meta: {
		menuType: "page",
		text: "仓储费率",
		icon: "IconSetting",
	},
});

/** 列表分页只展示关键数据，详情由 detail 接口补全 */
const api = { ...storageRateApi, detail: getStorageRateDetail };

const columns = [
	{ prop: "code", label: "费用名称", minWidth: 160 },
	{ prop: "cost_yj", label: "价格", width: 120 },
	{ prop: "cost_zk", label: "折扣", width: 100 },
	{ prop: "cost_sl", label: "税率", width: 100 },
	{ prop: "cost_bhs", label: "不含税价", width: 130 },
	{ prop: "cost_hsj", label: "含税价", width: 130 },
	{ prop: "create_name", label: "创建人", width: 120 },
	{ prop: "create_date", label: "创建日期", width: 170 },
];
</script>

<template>
	<DictCrudTable
		title="仓储费率"
		tip="仓储费率维护：费用名称、价格、折扣、税率、含税/不含税价（来源：wm_cost_conf）"
		:api="api"
		:columns="columns"
		:search-fields="['code']"
		filename="仓储费率.xlsx"
	/>
</template>

<style lang="scss" scoped></style>
