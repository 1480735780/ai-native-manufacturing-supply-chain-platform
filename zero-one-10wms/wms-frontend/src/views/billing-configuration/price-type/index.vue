<script lang="ts" setup>
import DictCrudTable from "../components/DictCrudTable.vue";

import { priceTypeApi } from "@/apis/billing/index";
definePage({
	meta: {
		menuType: "page",
		text: "价格类型",
		icon: "IconSetting",
	},
});

const api = priceTypeApi;

const columns = [
		{ prop: "code", label: "价格类型代码", minWidth: 160 },
		{ prop: "name", label: "价格类型名称", minWidth: 180 },
		{ prop: "create_name", label: "创建人", width: 120 },
		{ prop: "create_date", label: "创建日期", width: 170 },
	];
</script>

<template>
	<DictCrudTable
		title="价格类型"
		tip="价格类型字典维护（标准价/协议价/促销价等）"
		:api="api"
		:columns="columns"
		:search-fields="['code', 'name']"
		filename="价格类型.xlsx"
	/>
</template>

<style lang="scss" scoped></style>
