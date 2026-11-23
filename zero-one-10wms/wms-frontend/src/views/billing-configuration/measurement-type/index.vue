<script lang="ts" setup>
import DictCrudTable from "../components/DictCrudTable.vue";

import { measurementTypeApi } from "@/apis/billing/index";
definePage({
	meta: {
		menuType: "page",
		text: "计量类型",
		icon: "IconSetting",
	},
});

const api = measurementTypeApi;

const columns = [
		{ prop: "code", label: "计量类型代码", minWidth: 160 },
		{ prop: "name", label: "计量类型名称", minWidth: 180 },
		{ prop: "create_name", label: "创建人", width: 120 },
		{ prop: "create_date", label: "创建日期", width: 170 },
	];
</script>

<template>
	<DictCrudTable
		title="计量类型"
		tip="计量类型字典维护（吨/千克/立方米等）"
		:api="api"
		:columns="columns"
		:search-fields="['code', 'name']"
		filename="计量类型.xlsx"
	/>
</template>

<style lang="scss" scoped></style>
