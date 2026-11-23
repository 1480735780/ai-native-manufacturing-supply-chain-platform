<script lang="ts" setup>
import { ref, reactive, computed, onMounted } from "vue";
import { ElMessage } from "element-plus";
import {
	listAbnormalShipment,
	exportAbnormalShipment,
	saveBlob,
} from "@/apis/daily-check/index";

definePage({
	meta: {
		menuType: "page",
		text: "出货异常",
		icon: "IconSetting",
	},
});

interface AbnormalRow {
	create_date?: string;
	create_name?: string;
	update_name?: string;
	ku_wei_bian_ma?: string;
	bin_id?: string;
	bin_id_to?: string;
	cus_code?: string;
	zhong_wen_qch?: string;
	goods_id?: string;
	shp_ming_cheng?: string;
	goods_pro_data?: string;
	base_unit?: string;
	goods_qua?: string;
	goods_quaok?: string;
}

const loading = ref(false);
const exporting = ref(false);
const allRows = ref<AbnormalRow[]>([]);
const pageIndex = ref(1);
const pageSize = ref(10);

const searchForm = reactive({
	create_date: "",
	create_name: "",
	update_name: "",
	ku_wei_bian_ma: "",
	bin_id: "",
	zhong_wen_qch: "",
});

const rows = computed(() => {
	const start = (pageIndex.value - 1) * pageSize.value;
	return allRows.value.slice(start, start + pageSize.value);
});

const total = computed(() => allRows.value.length);

function formatDateTime(value?: string) {
	if (!value) return "";
	return value.replace("T", " ");
}

function diff(row: AbnormalRow) {
	const qua = Number(row.goods_qua);
	const quaok = Number(row.goods_quaok);
	if (Number.isNaN(qua) || Number.isNaN(quaok)) return "";
	return qua - quaok;
}

function loadData() {
	loading.value = true;
	listAbnormalShipment(
		{ pageIndex: 1, pageSize: 1000, ...searchForm },
		(data: any) => {
			allRows.value = Array.isArray(data) ? data : (data.rows ?? []);
			pageIndex.value = 1;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("出货异常数据加载失败");
		},
	);
}

function handleSearch() {
	loadData();
}

function handleReset() {
	searchForm.create_date = "";
	searchForm.create_name = "";
	searchForm.update_name = "";
	searchForm.ku_wei_bian_ma = "";
	searchForm.bin_id = "";
	searchForm.zhong_wen_qch = "";
	loadData();
}

function handlePageChange(page: number) {
	pageIndex.value = page;
}

function handleSizeChange(size: number) {
	pageSize.value = size;
	pageIndex.value = 1;
}

async function handleExport() {
	exporting.value = true;
	try {
		// 后端导出依赖最近一次列表查询结果，先按当前条件拉取全量
		await new Promise<void>(resolve => {
			listAbnormalShipment(
				{ pageIndex: 1, pageSize: 10000, ...searchForm },
				() => resolve(),
				() => resolve(),
			);
		});
		const blob = await exportAbnormalShipment();
		saveBlob(blob, `出货异常_${Date.now()}.xlsx`);
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
	<section class="abnormal-shipment-root">
		<h2>出货异常</h2>

		<el-form :inline="true" class="filter-bar">
			<el-form-item label="下架日期">
				<el-date-picker
					v-model="searchForm.create_date"
					type="date"
					value-format="YYYY-MM-DD"
					placeholder="选择日期"
					style="width: 150px"
				/>
			</el-form-item>
			<el-form-item label="下架人">
				<el-input v-model="searchForm.create_name" placeholder="下架人" clearable style="width: 120px" />
			</el-form-item>
			<el-form-item label="复核人">
				<el-input v-model="searchForm.update_name" placeholder="复核人" clearable style="width: 120px" />
			</el-form-item>
			<el-form-item label="储位">
				<el-input
					v-model="searchForm.ku_wei_bian_ma"
					placeholder="储位"
					clearable
					style="width: 120px"
				/>
			</el-form-item>
			<el-form-item label="下架托盘">
				<el-input v-model="searchForm.bin_id" placeholder="下架托盘" clearable style="width: 130px" />
			</el-form-item>
			<el-form-item label="客户名称">
				<el-input v-model="searchForm.zhong_wen_qch" placeholder="客户名称" clearable style="width: 160px" />
			</el-form-item>
			<el-form-item>
				<el-button type="primary" @click="handleSearch">查询</el-button>
				<el-button @click="handleReset">重置</el-button>
				<el-button type="warning" :loading="exporting" @click="handleExport">导出数据</el-button>
			</el-form-item>
		</el-form>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%">
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column label="下架日期" width="160">
				<template #default="{ row }">{{ formatDateTime(row.create_date) }}</template>
			</el-table-column>
			<el-table-column prop="create_name" label="下架人" width="100" />
			<el-table-column prop="update_name" label="复核人" width="100" />
			<el-table-column prop="ku_wei_bian_ma" label="储位" width="110" show-overflow-tooltip />
			<el-table-column prop="bin_id" label="下架托盘" width="110" show-overflow-tooltip />
			<el-table-column prop="bin_id_to" label="下架单号" width="150" show-overflow-tooltip />
			<el-table-column prop="cus_code" label="客户编码" width="100" />
			<el-table-column prop="zhong_wen_qch" label="客户名称" min-width="170" show-overflow-tooltip />
			<el-table-column prop="goods_id" label="商品编码" width="110" show-overflow-tooltip />
			<el-table-column prop="shp_ming_cheng" label="商品名称" min-width="130" show-overflow-tooltip />
			<el-table-column prop="goods_pro_data" label="生产日期" width="110" />
			<el-table-column prop="base_unit" label="单位" width="70" />
			<el-table-column prop="goods_qua" label="下架数量" width="100" align="right" />
			<el-table-column prop="goods_quaok" label="复核数量" width="100" align="right" />
			<el-table-column label="差异数量" width="100" align="right">
				<template #default="{ row }">
					<el-tag type="danger">{{ diff(row) }}</el-tag>
				</template>
			</el-table-column>
		</el-table>

		<div class="pagination-bar">
			<el-pagination
				:current-page="pageIndex"
				:page-size="pageSize"
				:page-sizes="[10, 20, 50]"
				:total="total"
				layout="total, sizes, prev, pager, next"
				@current-change="handlePageChange"
				@size-change="handleSizeChange"
			/>
		</div>
	</section>
</template>

<style lang="scss" scoped>
.abnormal-shipment-root {
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
