<script lang="ts" setup>
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import {
	listUnloadingFees,
	downloadUnloadingFees,
	saveBlob,
} from "@/apis/cost-management/index";

definePage({
	meta: {
		menuType: "page",
		text: "外包卸货费",
		icon: "IconSetting",
	},
});

interface UnloadingRow {
	fee?: string;
	acceptor?: string;
	acceptDate?: string;
	orderNo?: string;
	goods?: string;
	goodsName?: string;
	unloadingNum?: number;
	unloadingWeight?: number;
	feeRMB?: number;
	price?: number;
}

const loading = ref(false);
const exporting = ref(false);
const rows = ref<UnloadingRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);

const searchForm = reactive({
	acceptor: "",
	orderNo: "",
	goods: "",
	dateRange: [] as string[],
});

function buildQuery() {
	const query: Record<string, any> = {
		acceptor: searchForm.acceptor,
		orderNo: searchForm.orderNo,
		goods: searchForm.goods,
	};
	if (searchForm.dateRange.length === 2) {
		query.acceptDate_begin = `${searchForm.dateRange[0]} 00:00:00`;
		query.acceptDate_end = `${searchForm.dateRange[1]} 23:59:59`;
	}
	return query;
}

function loadData() {
	loading.value = true;
	listUnloadingFees(
		{ pageIndex: pageIndex.value, pageSize: pageSize.value, ...buildQuery() },
		(data: any) => {
			rows.value = data?.rows ?? [];
			total.value = data?.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("外包卸货费加载失败");
		},
	);
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	searchForm.acceptor = "";
	searchForm.orderNo = "";
	searchForm.goods = "";
	searchForm.dateRange = [];
	pageIndex.value = 1;
	loadData();
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
		const blob = await downloadUnloadingFees(buildQuery());
		saveBlob(blob, `外包卸货费_${Date.now()}.xlsx`);
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
	<section class="unloading-fee-root">
		<h2>外包卸货费</h2>

		<el-form :inline="true" class="filter-bar">
			<el-form-item label="验收人">
				<el-input v-model="searchForm.acceptor" placeholder="验收人" clearable style="width: 140px" />
			</el-form-item>
			<el-form-item label="验收日期">
				<el-date-picker
					v-model="searchForm.dateRange"
					type="daterange"
					value-format="YYYY-MM-DD"
					start-placeholder="开始日期"
					end-placeholder="结束日期"
					style="width: 240px"
				/>
			</el-form-item>
			<el-form-item label="单号">
				<el-input v-model="searchForm.orderNo" placeholder="单号" clearable style="width: 160px" />
			</el-form-item>
			<el-form-item label="商品">
				<el-input v-model="searchForm.goods" placeholder="商品" clearable style="width: 140px" />
			</el-form-item>
			<el-form-item>
				<el-button type="primary" @click="handleSearch">查询</el-button>
				<el-button @click="handleReset">重置</el-button>
				<el-button type="warning" :loading="exporting" @click="handleExport">导出数据</el-button>
			</el-form-item>
		</el-form>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%">
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="fee" label="费用" min-width="140" show-overflow-tooltip />
			<el-table-column prop="acceptor" label="验收人" width="110" />
			<el-table-column prop="acceptDate" label="验收日期" width="170" />
			<el-table-column prop="orderNo" label="单号" width="150" show-overflow-tooltip />
			<el-table-column prop="goods" label="商品" width="130" show-overflow-tooltip />
			<el-table-column prop="goodsName" label="商品名称" min-width="150" show-overflow-tooltip />
			<el-table-column prop="unloadingNum" label="卸货数" width="100" align="right" />
			<el-table-column prop="unloadingWeight" label="卸货重量" width="110" align="right" />
			<el-table-column prop="feeRMB" label="费用RMB" width="110" align="right" />
			<el-table-column prop="price" label="单价" width="100" align="right" />
		</el-table>

		<div class="pagination-bar">
			<el-pagination
				:current-page="pageIndex"
				:page-size="pageSize"
				:page-sizes="[10, 20, 50]"
				:total="total"
				layout="total, sizes, prev, pager, next, jumper"
				@current-change="handlePageChange"
				@size-change="handleSizeChange"
			/>
		</div>
	</section>
</template>

<style lang="scss" scoped>
.unloading-fee-root {
	width: 100%;

	.filter-bar {
		margin-top: 12px;
	}

	.pagination-bar {
		display: flex;
		justify-content: flex-end;
		margin-top: 16px;
	}
}
</style>
