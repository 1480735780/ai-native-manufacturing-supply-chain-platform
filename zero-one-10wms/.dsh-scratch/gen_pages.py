# -*- coding: utf-8 -*-
import os

BASE = "wms-frontend/src/views/ware-config/"

# (目录, 页面标题text, 图标, 接口导入, options构造)
pages = [
    ("order-type", "订单类型", "Tickets", """
	listOrderTypes, addOrderType, updateOrderType, deleteOrderType, deleteOrderTypeBatch,
	importOrderType, exportOrderType,
""", """{
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
}"""),
    ("buss-type", "业务类型", "Collection", """
	listBussTypes, addBussType, updateBussType, deleteBussType, deleteBussTypeBatch,
	importBussType, exportBussType,
""", """{
	title: "业务类型",
	columns: [
		{ label: "业务类型代码", prop: "buss_type_code", width: 180 },
		{ label: "业务类型名称", prop: "buss_type_name" },
	],
	queryFields: [
		{ prop: "buss_type_code", label: "业务类型代码" },
		{ prop: "buss_type_name", label: "业务类型名称" },
	],
	addFields: [
		{ prop: "buss_type_code", label: "业务类型代码" },
		{ prop: "buss_type_name", label: "业务类型名称" },
	],
	editFields: [
		{ prop: "id", label: "唯一标识" },
		{ prop: "buss_type_code", label: "业务类型代码" },
		{ prop: "buss_type_name", label: "业务类型名称" },
	],
	listApi: listBussTypes,
	addApi: addBussType,
	updateApi: updateBussType,
	deleteApi: deleteBussType,
	deleteBatchApi: deleteBussTypeBatch,
	importApi: importBussType,
	exportApi: exportBussType.bind(null, "buss-type.xlsx"),
	exportFileName: "业务类型",
}"""),
    ("act-type", "作业类型", "Operation", """
	listActTypes, addActType, updateActType, deleteActType, deleteActTypeBatch,
	importActType, exportActType,
""", """{
	title: "作业类型",
	columns: [
		{ label: "作业类型代码", prop: "act_type_code", width: 160 },
		{ label: "作业类型名称", prop: "act_type_name" },
		{ label: "业务环节", prop: "oper_step_code", width: 140 },
	],
	queryFields: [
		{ prop: "act_type_code", label: "作业类型代码" },
		{ prop: "act_type_name", label: "作业类型名称" },
		{ prop: "oper_step_code", label: "业务环节代码" },
	],
	addFields: [
		{ prop: "act_type_code", label: "作业类型代码" },
		{ prop: "act_type_name", label: "作业类型名称" },
		{ prop: "oper_step_code", label: "业务环节代码" },
	],
	editFields: [
		{ prop: "id", label: "唯一标识" },
		{ prop: "act_type_code", label: "作业类型代码" },
		{ prop: "act_type_name", label: "作业类型名称" },
		{ prop: "oper_step_code", label: "业务环节代码" },
	],
	listApi: listActTypes,
	addApi: addActType,
	updateApi: updateActType,
	deleteApi: deleteActType,
	deleteBatchApi: ids => deleteActTypeBatch(ids.join(",")),
	importApi: importActType,
	exportApi: exportActType.bind(null, "act-type.xlsx"),
	exportFileName: "作业类型",
}"""),
    ("business-link", "业务环节", "Connection", """
	listBusinessLinks, addBusinessLink, updateBusinessLink, deleteBusinessLink,
	importBusinessLink, exportBusinessLink,
""", """{
	title: "业务环节",
	columns: [
		{ label: "业务环节代码", prop: "oper_step_code", width: 180 },
		{ label: "业务环节名称", prop: "oper_step_name" },
	],
	queryFields: [
		{ prop: "oper_step_code", label: "业务环节代码" },
		{ prop: "oper_step_name", label: "业务环节名称" },
	],
	addFields: [
		{ prop: "oper_step_code", label: "业务环节代码" },
		{ prop: "oper_step_name", label: "业务环节名称" },
	],
	editFields: [
		{ prop: "oper_step_code", label: "业务环节代码" },
		{ prop: "oper_step_name", label: "业务环节名称" },
	],
	listApi: listBusinessLinks,
	addApi: addBusinessLink,
	updateApi: updateBusinessLink,
	deleteApi: deleteBusinessLink,
	importApi: importBusinessLink,
	exportApi: exportBusinessLink.bind(null, "business-link.xlsx"),
	exportFileName: "业务环节",
}"""),
    ("operation-type", "操作类型", "SetUp", """
	listOperationTypes, addOperationType, updateOperationType, deleteOperationType,
	deleteOperationTypeBatch, importOperationType, exportOperationType,
""", """{
	title: "操作类型",
	columns: [
		{ label: "操作类型代码", prop: "code", width: 180 },
		{ label: "操作类型名称", prop: "name" },
	],
	queryFields: [
		{ prop: "code", label: "操作类型代码" },
		{ prop: "name", label: "操作类型名称" },
	],
	addFields: [
		{ prop: "code", label: "操作类型代码" },
		{ prop: "name", label: "操作类型名称" },
	],
	editFields: [
		{ prop: "id", label: "唯一标识" },
		{ prop: "code", label: "操作类型代码" },
		{ prop: "name", label: "操作类型名称" },
	],
	listApi: listOperationTypes,
	addApi: addOperationType,
	updateApi: updateOperationType,
	deleteApi: deleteOperationType,
	deleteBatchApi: deleteOperationTypeBatch,
	importApi: importOperationType,
	exportApi: exportOperationType.bind(null, "operation-type.xlsx"),
	exportFileName: "操作类型",
}"""),
    ("lad-mod", "提货方式", "Van", """
	listLadMods, addLadMod, updateLadMod, deleteLadMod, deleteLadModBatch,
	importLadMod, exportLadMod,
""", """{
	title: "提货方式",
	rowKey: "id",
	columns: [
		{ label: "提货方式代码", prop: "code", width: 180 },
		{ label: "提货方式名称", prop: "name" },
	],
	queryFields: [
		{ prop: "code", label: "提货方式代码" },
		{ prop: "name", label: "提货方式名称" },
	],
	addFields: [
		{ prop: "code", label: "提货方式代码" },
		{ prop: "name", label: "提货方式名称" },
	],
	editFields: [
		{ prop: "id", label: "唯一标识" },
		{ prop: "code", label: "提货方式代码" },
		{ prop: "name", label: "提货方式名称" },
	],
	listApi: listLadMods,
	addApi: addLadMod,
	updateApi: updateLadMod,
	deleteApi: deleteLadMod,
	deleteBatchApi: deleteLadModBatch,
	importApi: importLadMod,
	exportApi: exportLadMod,
	exportFileName: "提货方式",
}"""),
    ("recv-g-way", "接货方式", "Receiving", """
	listRecvGWays, addRecvGWay, updateRecvGWay, deleteRecvGWay, deleteRecvGWayBatch,
	importRecvGWay, exportRecvGWay,
""", """{
	title: "接货方式",
	columns: [
		{ label: "接货方式代码", prop: "del_mode_code", width: 180 },
		{ label: "接货方式名称", prop: "del_mode_name" },
	],
	queryFields: [
		{ prop: "del_mode_code", label: "接货方式代码" },
		{ prop: "del_mode_name", label: "接货方式名称" },
	],
	addFields: [
		{ prop: "del_mode_code", label: "接货方式代码" },
		{ prop: "del_mode_name", label: "接货方式名称" },
	],
	editFields: [
		{ prop: "id", label: "唯一标识" },
		{ prop: "del_mode_code", label: "接货方式代码" },
		{ prop: "del_mode_name", label: "接货方式名称" },
	],
	listApi: listRecvGWays,
	addApi: addRecvGWay,
	updateApi: updateRecvGWay,
	deleteApi: deleteRecvGWay,
	deleteBatchApi: deleteRecvGWayBatch,
	importApi: importRecvGWay,
	exportApi: exportRecvGWay.bind(null, "recv-g-way.xlsx"),
	exportFileName: "接货方式",
}"""),
    ("library", "库位类型", "Grid", """
	listLibraries, addLibrary, updateLibrary, deleteLibrary,
	importLibrary, exportLibrary,
""", """{
	title: "库位类型",
	columns: [
		{ label: "库位类型代码", prop: "bin_type_code", width: 180 },
		{ label: "库位类型名称", prop: "bin_type_name" },
	],
	queryFields: [
		{ prop: "bin_type_code", label: "库位类型代码" },
		{ prop: "bin_type_name", label: "库位类型名称" },
	],
	addFields: [
		{ prop: "bin_type_code", label: "库位类型代码" },
		{ prop: "bin_type_name", label: "库位类型名称" },
	],
	editFields: [
		{ prop: "id", label: "唯一标识" },
		{ prop: "bin_type_code", label: "库位类型代码" },
		{ prop: "bin_type_name", label: "库位类型名称" },
	],
	listApi: listLibraries,
	addApi: addLibrary,
	updateApi: updateLibrary,
	deleteApi: deleteLibrary,
	importApi: importLibrary,
	exportApi: exportLibrary.bind(null, "library.xlsx"),
	exportFileName: "库位类型",
}"""),
    ("temperature", "温度属性", "Sunny", """
	listTemperatures, addTemperature, updateTemperature, deleteTemperature,
	importTemperature, exportTemperature,
""", """{
	title: "温度属性",
	columns: [
		{ label: "温层代码", prop: "deg_type_code", width: 180 },
		{ label: "温层名称", prop: "deg_type_name" },
	],
	queryFields: [
		{ prop: "deg_type_code", label: "温层代码" },
		{ prop: "deg_type_name", label: "温层名称" },
	],
	addFields: [
		{ prop: "deg_type_code", label: "温层代码" },
		{ prop: "deg_type_name", label: "温层名称" },
	],
	editFields: [
		{ prop: "deg_type_code", label: "温层代码" },
		{ prop: "deg_type_name", label: "温层名称" },
	],
	listApi: listTemperatures,
	addApi: addTemperature,
	updateApi: updateTemperature,
	deleteApi: deleteTemperature,
	importApi: importTemperature,
	exportApi: exportTemperature.bind(null, "temperature.xlsx"),
	exportFileName: "温度属性",
}"""),
]

for slug, title, icon, imports, options in pages:
    # order-type 已有旧页面，直接重写为统一范式
    content = '''<script lang="ts" setup>
import { %s } from "@/apis/ware-config/index.js";
import DictPage from "../components/DictPage.vue";
import type { DictPageOptions } from "../composables/use-dict-page";
import %s from "@element-plus/icons-vue";

definePage({
	meta: {
		menuType: "page",
		text: "%s",
		icon: %s,
	},
});

const options: DictPageOptions = %s;
</script>

<template>
	<DictPage :options="options" />
</template>
''' % (imports.strip(), icon, title, icon, options.strip())
    d = os.path.join(BASE, slug)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.vue"), "w", encoding="utf-8", newline="\n").write(content)
    print("生成", slug + "/index.vue")
