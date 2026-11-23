<script lang="ts" setup>
import DictCrudTable from "../components/DictCrudTable.vue";

import { goodsClassApi } from "@/apis/billing/index";
definePage({
	meta: {
		menuType: "page",
		text: "计费商品分类",
		icon: "IconSetting",
	},
});

const api = goodsClassApi;

const columns = [
		{ prop: "code", label: "计费商品类代码", minWidth: 180 },
		{ prop: "name", label: "计费商品类名称", minWidth: 180 },
		{ prop: "create_name", label: "创建人", width: 120 },
		{ prop: "create_date", label: "创建日期", width: 170 },
	];
</script>

<template>
	<DictCrudTable
		title="计费商品分类"
		tip="计费商品类目配置，支持增删改查与导入导出"
		:api="api"
		:columns="columns"
		:search-fields="['code', 'name']"
		filename="计费商品分类.xlsx"
	/>
</template>

<style lang="scss" scoped></style>
