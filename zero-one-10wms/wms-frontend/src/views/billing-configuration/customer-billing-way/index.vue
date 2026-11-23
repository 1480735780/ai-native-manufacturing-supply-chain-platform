<script lang="ts" setup>
import DictCrudTable from "../components/DictCrudTable.vue";

import { customerBillingWayApi } from "@/apis/billing/index";
definePage({
	meta: {
		menuType: "page",
		text: "客户计费方式",
		icon: "IconSetting",
	},
});

const api = customerBillingWayApi;

const columns = [
		{ prop: "code", label: "编码", minWidth: 160 },
		{ prop: "name", label: "名称", minWidth: 180 },
		{ prop: "cus_sta_del", label: "停用", width: 100 },
		{ prop: "create_name", label: "创建人", width: 120 },
		{ prop: "create_date", label: "创建日期", width: 170 },
	];
</script>

<template>
	<DictCrudTable
		title="客户计费方式"
		tip="客户计费方式（客户状态）字典维护"
		:api="api"
		:columns="columns"
		:search-fields="['code', 'name']"
		filename="客户计费方式.xlsx"
	/>
</template>

<style lang="scss" scoped></style>
