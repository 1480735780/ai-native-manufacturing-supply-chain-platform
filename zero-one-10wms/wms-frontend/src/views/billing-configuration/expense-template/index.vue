<script lang="ts" setup>
import DictCrudTable from "../components/DictCrudTable.vue";

import { costTemplateApi } from "@/apis/billing/index";
definePage({
	meta: {
		menuType: "page",
		text: "费用模板",
		icon: "IconSetting",
	},
});

const api = costTemplateApi;

const columns = [
		{ prop: "code", label: "费用名称", minWidth: 160 },
		{ prop: "cost_jg", label: "价格(RMB)", width: 120 },
		{ prop: "cost_sl", label: "税率", width: 100 },
		{ prop: "cost_zk", label: "折扣", width: 100 },
		{ prop: "cost_bhs", label: "不含税价(RMB)", width: 140 },
		{ prop: "cost_hs", label: "含税价(RMB)", width: 140 },
		{ prop: "free_day", label: "免费天数起", width: 120 },
		{ prop: "free_day2", label: "免费天数止", width: 120 },
		{ prop: "create_name", label: "创建人", width: 120 },
	];
</script>

<template>
	<DictCrudTable
		title="费用模板"
		tip="费用模板维护：费用名称、价格、税率、折扣、含税/不含税价、免费天数"
		:api="api"
		:columns="columns"
		:search-fields="['code']"
		filename="费用模板.xlsx"
	/>
</template>

<style lang="scss" scoped></style>
