<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { listCheck, exportInventoryDifference, saveBlob } from "@/apis/inventory/index";

definePage({
	meta: {
		menuType: "page",
		text: "盘点差异",
		icon: "IconSetting",
	},
});

interface CheckRow {
	id?: string;
	bin_id?: string;
	tin_id?: string;
	goods_id?: string;
	goods_name?: string;
	goods_qua?: string;
	stt_qua?: string;
	goods_unit?: string;
	goods_pro_data?: string;
	cus_code?: string;
	cus_name?: string;
	stt_sta?: string;
}

const loading = ref(false);
const rows = ref<CheckRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const exporting = ref(false);

const query = ref({
	bin_id: "",
	tin_id: "",
	goods_id: "",
	goods_name: "",
});

function diff(row: CheckRow) {
	const book = Number(row.goods_qua ?? 0);
	const real = Number(row.stt_qua ?? 0);
	if (Number.isNaN(book) || Number.isNaN(real)) return "-";
	return String(real - book);
}

function diffClass(row: CheckRow) {
	const value = diff(row);
	if (value === "-" || value === "0") return "";
	return Number(value) > 0 ? "diff-plus" : "diff-minus";
}

function loadData() {
	loading.value = true;
	listCheck(
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
			ElMessage.error("盘点差异数据加载失败");
		},
	);
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	query.value = { bin_id: "", tin_id: "", goods_id: "", goods_name: "" };
	pageIndex.value = 1;
	loadData();
}

async function handleExport() {
	exporting.value = true;
	try {
		const blob = await exportInventoryDifference(query.value);
		saveBlob(blob, "盘点差异数据.xlsx");
	} catch {
		ElMessage.error("导出盘点差异数据失败");
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
	<section class="inventory-diff-root">
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
				<el-form-item>
					<el-button type="primary" @click="handleSearch">查询</el-button>
					<el-button @click="handleReset">重置</el-button>
					<el-button :loading="exporting" @click="handleExport">导出差异</el-button>
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
			<el-table-column label="差异数量" width="100" align="right">
				<template #default="{ row }">
					<span :class="diffClass(row)">{{ diff(row) }}</span>
				</template>
			</el-table-column>
			<el-table-column prop="goods_unit" label="单位" width="70" />
			<el-table-column prop="goods_pro_data" label="生产日期" width="110" />
			<el-table-column prop="cus_code" label="客户编码" width="100" />
			<el-table-column prop="cus_name" label="客户名称" min-width="160" show-overflow-tooltip />
			<el-table-column prop="stt_sta" label="盘点状态" width="100" />
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
.inventory-diff-root {
	width: 100%;

	.diff-plus {
		color: #f56c6c;
		font-weight: 600;
	}

	.diff-minus {
		color: #67c23a;
		font-weight: 600;
	}
}
</style>
