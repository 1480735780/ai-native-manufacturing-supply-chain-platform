<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { listReviewStt, reviewStt, exportReviewStt, saveBlob } from "@/apis/inventory/index";

definePage({
	meta: {
		menuType: "page",
		text: "复盘",
		icon: "IconSetting",
	},
});

interface ReviewRow {
	id?: string;
	bin_id?: string;
	tin_id?: string;
	goods_id?: string;
	goods_name?: string;
	goods_qua?: string;
	stt_qua?: string;
	goods_unit?: string;
	goods_pro_date?: string;
	goods_batch?: string;
	cus_name?: string;
	cus_code?: string;
	cus?: string;
	stt_sta?: string;
	stt_type?: string;
	create_name?: string;
}

const loading = ref(false);
const rows = ref<ReviewRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const exporting = ref(false);

const query = ref({
	bin_id: "",
	tin_id: "",
	goods_id: "",
	goods_name: "",
	stt_sta: "",
});

function diff(row: ReviewRow) {
	const book = Number(row.goods_qua ?? 0);
	const report = Number(row.stt_qua ?? 0);
	if (Number.isNaN(book) || Number.isNaN(report)) return "-";
	return String(report - book);
}

function loadData() {
	loading.value = true;
	listReviewStt(
		{
			pageIndex: pageIndex.value,
			pageSize: pageSize.value,
			...query.value,
		},
		(data: any) => {
			rows.value = data.rows ?? [];
			total.value = data.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("复盘数据加载失败");
		},
	);
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	query.value = { bin_id: "", tin_id: "", goods_id: "", goods_name: "", stt_sta: "" };
	pageIndex.value = 1;
	loadData();
}

async function handleReview(row: ReviewRow) {
	if (row.stt_sta !== "已完成") {
		ElMessage.warning("仅“已完成”状态的盘点记录可以复盘（回退到计划中重做）");
		return;
	}
	try {
		await ElMessageBox.confirm(
			"复盘会将该盘点任务回退到“计划中”状态重新盘点，确定继续吗？",
			"复盘确认",
			{
				confirmButtonText: "确定复盘",
				cancelButtonText: "取消",
				type: "warning",
			},
		);
	} catch {
		return;
	}
	try {
		await reviewStt({ ...row });
		ElMessage.success("复盘成功，任务已回退到计划中");
		loadData();
	} catch {
		ElMessage.error("复盘失败");
	}
}

async function handleExport() {
	exporting.value = true;
	try {
		const blob = await exportReviewStt(query.value);
		saveBlob(blob, "复盘数据.xlsx");
	} catch {
		ElMessage.error("导出复盘数据失败");
	} finally {
		exporting.value = false;
	}
}

function handlePageChange(val: number) {
	pageIndex.value = val;
	loadData();
}

function handleSizeChange(val: number) {
	pageSize.value = val;
	pageIndex.value = 1;
	loadData();
}

onMounted(() => {
	loadData();
});
</script>

<template>
	<section class="double-quotation-root">
		<el-card shadow="never" class="query-card">
			<el-form :model="query" inline label-width="80px">
				<el-form-item label="储位">
					<el-input v-model="query.bin_id" clearable placeholder="请输入储位" style="width: 140px" />
				</el-form-item>
				<el-form-item label="托盘">
					<el-input v-model="query.tin_id" clearable placeholder="请输入托盘" style="width: 140px" />
				</el-form-item>
				<el-form-item label="商品编码">
					<el-input v-model="query.goods_id" clearable placeholder="请输入商品编码" style="width: 150px" />
				</el-form-item>
				<el-form-item label="商品名称">
					<el-input v-model="query.goods_name" clearable placeholder="请输入商品名称" style="width: 150px" />
				</el-form-item>
				<el-form-item label="盘点状态">
					<el-select v-model="query.stt_sta" clearable placeholder="全部" style="width: 130px">
						<el-option label="计划中" value="计划中" />
						<el-option label="已完成" value="已完成" />
						<el-option label="已过账" value="已过账" />
					</el-select>
				</el-form-item>
				<el-form-item>
					<el-button type="primary" @click="handleSearch">查询</el-button>
					<el-button @click="handleReset">重置</el-button>
					<el-button :loading="exporting" @click="handleExport">导出</el-button>
				</el-form-item>
			</el-form>
		</el-card>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%">
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="bin_id" label="储位" width="110" show-overflow-tooltip />
			<el-table-column prop="tin_id" label="托盘" width="110" show-overflow-tooltip />
			<el-table-column prop="goods_id" label="商品编码" width="110" show-overflow-tooltip />
			<el-table-column prop="goods_name" label="商品名称" min-width="130" show-overflow-tooltip />
			<el-table-column prop="goods_qua" label="账面数量" width="100" align="right" />
			<el-table-column prop="stt_qua" label="盘点数量" width="100" align="right" />
			<el-table-column label="差异" width="90" align="right">
				<template #default="{ row }">{{ diff(row) }}</template>
			</el-table-column>
			<el-table-column prop="goods_unit" label="单位" width="70" />
			<el-table-column prop="goods_pro_date" label="生产日期" width="110" />
			<el-table-column prop="goods_batch" label="批次" width="110" show-overflow-tooltip />
			<el-table-column prop="cus_code" label="客户编码" width="100" />
			<el-table-column prop="cus_name" label="客户名称" min-width="160" show-overflow-tooltip />
			<el-table-column prop="stt_type" label="盘点类型" width="100" />
			<el-table-column prop="stt_sta" label="盘点状态" width="100" />
			<el-table-column prop="create_name" label="创建人" width="100" />
			<el-table-column label="操作" width="90" fixed="right">
				<template #default="{ row }">
					<el-button link type="primary" :disabled="row.stt_sta !== '已完成'" @click="handleReview(row)">
						复盘
					</el-button>
				</template>
			</el-table-column>
		</el-table>

		<el-pagination
			style="margin-top: 16px; justify-content: flex-end"
			v-model:current-page="pageIndex"
			v-model:page-size="pageSize"
			:page-sizes="[10, 20, 50]"
			layout="total, sizes, prev, pager, next, jumper"
			:total="total"
			@size-change="handleSizeChange"
			@current-change="handlePageChange"
		/>
	</section>
</template>

<style lang="scss" scoped>
.double-quotation-root {
	width: 100%;
}
</style>
