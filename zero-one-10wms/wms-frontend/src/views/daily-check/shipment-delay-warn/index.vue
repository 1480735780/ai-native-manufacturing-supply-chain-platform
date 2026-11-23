<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import {
	listShipmentDelay,
	exportShipmentDelay,
	saveBlob,
} from "@/apis/daily-check/index";

definePage({
	meta: {
		menuType: "page",
		text: "进货延时示警",
		icon: "IconSetting",
	},
});

interface ShipmentDelayRow {
	createName?: string;
	createDate?: string;
	supName?: string;
	imData?: string;
	imCarDri?: string;
	imCarMobile?: string;
	imBeizhu?: string;
	imCarNo?: string;
	imSta?: string;
	noticeId?: string;
}

const loading = ref(false);
const exporting = ref(false);
const rows = ref<ShipmentDelayRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);

function formatDateTime(value?: string) {
	if (!value) return "";
	return value.replace("T", " ");
}

function loadData() {
	loading.value = true;
	listShipmentDelay(
		{ pageIndex: pageIndex.value, pageSize: pageSize.value },
		(data: any) => {
			rows.value = data.rows ?? [];
			total.value = data.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("出货延迟预警数据加载失败");
		},
	);
}

function handlePageChange(page: number) {
	pageIndex.value = page;
	loadData();
}

function handleSizeChange(size: number) {
	pageSize.value = size;
	pageIndex.value = 1;
	loadData();
}

async function handleExport() {
	exporting.value = true;
	try {
		const blob = await exportShipmentDelay();
		saveBlob(blob, `进货延时示警_${Date.now()}.xlsx`);
		ElMessage.success("导出成功");
	} catch (err: any) {
		ElMessage.error(err?.message || "导出失败");
	} finally {
		exporting.value = false;
	}
}

onMounted(() => {
	loadData();
});
</script>

<template>
	<section class="shipment-delay-warn-root">
		<h2>进货延时示警</h2>

		<div class="tool-bar">
			<el-button type="primary" @click="loadData">刷新</el-button>
			<el-button type="warning" :loading="exporting" @click="handleExport">导出数据</el-button>
			<span class="tip">计划到货日期已过但仍未到货的进货通知单</span>
		</div>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%">
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="noticeId" label="到货通知单号" width="170" show-overflow-tooltip />
			<el-table-column prop="supName" label="货主" min-width="170" show-overflow-tooltip />
			<el-table-column label="计划日期" width="160">
				<template #default="{ row }">{{ formatDateTime(row.imData) }}</template>
			</el-table-column>
			<el-table-column label="创建时间" width="160">
				<template #default="{ row }">{{ formatDateTime(row.createDate) }}</template>
			</el-table-column>
			<el-table-column prop="createName" label="创建人" width="100" />
			<el-table-column prop="imCarDri" label="司机" width="100" />
			<el-table-column prop="imCarMobile" label="司机电话" width="130" />
			<el-table-column prop="imCarNo" label="车号" width="110" />
			<el-table-column prop="imSta" label="状态" width="100" />
			<el-table-column prop="imBeizhu" label="备注" min-width="160" show-overflow-tooltip />
		</el-table>

		<div class="pagination-bar">
			<el-pagination
				:current-page="pageIndex"
				:page-size="pageSize"
				:page-sizes="[10, 20, 50, 100]"
				:total="total"
				layout="total, sizes, prev, pager, next, jumper"
				@current-change="handlePageChange"
				@size-change="handleSizeChange"
			/>
		</div>
	</section>
</template>

<style lang="scss" scoped>
.shipment-delay-warn-root {
	width: 100%;

	.tool-bar {
		display: flex;
		align-items: center;
		gap: 16px;
		margin: 12px 0;
	}

	.tip {
		color: #909399;
		font-size: 13px;
	}

	.pagination-bar {
		display: flex;
		justify-content: flex-end;
		margin-top: 16px;
	}
}
</style>
