<script lang="ts" setup>
import { ref, reactive, computed, onMounted } from "vue";
import { ElMessage } from "element-plus";
import {
	listReceivedUnsold,
	exportReceivedUnsold,
	saveBlob,
} from "@/apis/daily-check/index";

definePage({
	meta: {
		menuType: "page",
		text: "收货未上架",
		icon: "IconSetting",
	},
});

interface ReceivedUnsoldRow {
	kucunsta?: string;
	bin_id?: string;
	tin_id?: string;
	cus_code?: string;
	zhong_wen_qch?: string;
	goods_id?: string;
	shp_ming_cheng?: string;
	qm_ok_quat?: string;
	shl_dan_wei?: string;
	pro_data?: string;
	create_date?: string;
	bzhi_qi?: string;
}

const loading = ref(false);
const exporting = ref(false);
const allRows = ref<ReceivedUnsoldRow[]>([]);
const pageIndex = ref(1);
const pageSize = ref(10);

const searchForm = reactive({
	bin_id: "",
	tin_id: "",
	cus_code: "",
	zhong_wen_qch: "",
	goods_id: "",
	shp_ming_cheng: "",
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

function statusText(value?: string) {
	if (value === "N") return "未上架";
	if (value === "I") return "上架中";
	if (value === "Y") return "已上架";
	return value ?? "";
}

function loadData() {
	loading.value = true;
	listReceivedUnsold(
		{ pageIndex: 1, pageSize: 1000, ...searchForm },
		(data: any) => {
			allRows.value = Array.isArray(data) ? data : (data.rows ?? []);
			pageIndex.value = 1;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("收货未上架数据加载失败");
		},
	);
}

function handleSearch() {
	loadData();
}

function handleReset() {
	searchForm.bin_id = "";
	searchForm.tin_id = "";
	searchForm.cus_code = "";
	searchForm.zhong_wen_qch = "";
	searchForm.goods_id = "";
	searchForm.shp_ming_cheng = "";
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
			listReceivedUnsold(
				{ pageIndex: 1, pageSize: 10000, ...searchForm },
				() => resolve(),
				() => resolve(),
			);
		});
		const blob = await exportReceivedUnsold();
		saveBlob(blob, `收货未上架_${Date.now()}.xlsx`);
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
	<section class="received-unsold-root">
		<h2>收货未上架</h2>

		<el-form :inline="true" class="filter-bar">
			<el-form-item label="储位">
				<el-input v-model="searchForm.bin_id" placeholder="储位" clearable style="width: 120px" />
			</el-form-item>
			<el-form-item label="托盘">
				<el-input v-model="searchForm.tin_id" placeholder="托盘" clearable style="width: 120px" />
			</el-form-item>
			<el-form-item label="客户编码">
				<el-input v-model="searchForm.cus_code" placeholder="客户编码" clearable style="width: 130px" />
			</el-form-item>
			<el-form-item label="客户名称">
				<el-input v-model="searchForm.zhong_wen_qch" placeholder="客户名称" clearable style="width: 160px" />
			</el-form-item>
			<el-form-item label="商品编码">
				<el-input v-model="searchForm.goods_id" placeholder="商品编码" clearable style="width: 130px" />
			</el-form-item>
			<el-form-item label="商品名称">
				<el-input
					v-model="searchForm.shp_ming_cheng"
					placeholder="商品名称"
					clearable
					style="width: 150px"
				/>
			</el-form-item>
			<el-form-item>
				<el-button type="primary" @click="handleSearch">查询</el-button>
				<el-button @click="handleReset">重置</el-button>
				<el-button type="warning" :loading="exporting" @click="handleExport">导出数据</el-button>
			</el-form-item>
		</el-form>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%">
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column label="库存状态" width="100">
				<template #default="{ row }">
					<el-tag type="warning">{{ statusText(row.kucunsta) }}</el-tag>
				</template>
			</el-table-column>
			<el-table-column prop="bin_id" label="储位" width="110" show-overflow-tooltip />
			<el-table-column prop="tin_id" label="托盘" width="110" show-overflow-tooltip />
			<el-table-column prop="cus_code" label="客户编码" width="100" />
			<el-table-column prop="zhong_wen_qch" label="客户名称" min-width="170" show-overflow-tooltip />
			<el-table-column prop="goods_id" label="商品编码" width="110" show-overflow-tooltip />
			<el-table-column prop="shp_ming_cheng" label="商品名称" min-width="130" show-overflow-tooltip />
			<el-table-column prop="qm_ok_quat" label="数量" width="90" align="right" />
			<el-table-column prop="shl_dan_wei" label="单位" width="70" />
			<el-table-column prop="pro_data" label="生产日期" width="110" />
			<el-table-column label="收货日期" width="160">
				<template #default="{ row }">{{ formatDateTime(row.create_date) }}</template>
			</el-table-column>
			<el-table-column prop="bzhi_qi" label="保质期(天)" width="100" align="right" />
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
.received-unsold-root {
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
