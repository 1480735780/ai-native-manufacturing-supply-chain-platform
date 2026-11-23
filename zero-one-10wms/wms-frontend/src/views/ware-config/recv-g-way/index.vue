<script lang="ts" setup>
import { listRecvGWays, addRecvGWay, updateRecvGWay, deleteRecvGWay, deleteRecvGWayBatch,
	importRecvGWay, exportRecvGWay, } from "@/apis/ware-config/index.js";
import DictPage from "../components/DictPage.vue";
import type { DictPageOptions } from "../composables/use-dict-page";
import { TakeawayBox } from "@element-plus/icons-vue";

definePage({
	meta: {
		menuType: "page",
		text: "接货方式",
		icon: TakeawayBox,
	},
});

const options: DictPageOptions = {
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
};
</script>

<template>
	<DictPage :options="options" />
</template>
