<script lang="ts" setup>
import { listOrderTypes, addOrderType, updateOrderType, deleteOrderType, deleteOrderTypeBatch,
	importOrderType, exportOrderType, } from "@/apis/ware-config/index.js";
import DictPage from "../components/DictPage.vue";
import type { DictPageOptions } from "../composables/use-dict-page";
import { Tickets } from "@element-plus/icons-vue";

definePage({
	meta: {
		menuType: "page",
		text: "订单类型",
		icon: Tickets,
	},
});

const options: DictPageOptions = {
	title: "订单类型",
	columns: [
		{ label: "订单类型代码", prop: "order_type_code", width: 180 },
		{ label: "订单类型名称", prop: "order_type_name" },
	],
	queryFields: [
		{ prop: "order_type_code", label: "订单类型代码" },
		{ prop: "order_type_name", label: "订单类型名称" },
	],
	addFields: [
		{ prop: "order_type_code", label: "订单类型代码" },
		{ prop: "order_type_name", label: "订单类型名称" },
	],
	editFields: [
		{ prop: "id", label: "唯一标识" },
		{ prop: "order_type_code", label: "订单类型代码" },
		{ prop: "order_type_name", label: "订单类型名称" },
	],
	listApi: listOrderTypes,
	addApi: addOrderType,
	updateApi: updateOrderType,
	deleteApi: deleteOrderType,
	deleteBatchApi: ids => deleteOrderTypeBatch(ids.join(",")),
	importApi: importOrderType,
	exportApi: exportOrderType.bind(null, "order-type.xlsx"),
	exportFileName: "订单类型",
};
</script>

<template>
	<DictPage :options="options" />
</template>
