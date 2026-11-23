<script lang="ts" setup>
import { reactive, ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import {
	listRemovalAdjust,
	getRemovalDetail,
	updateRemoval,
	batchUpdateRemoval,
	exportRemoval,
	saveBlob,
} from "@/apis/inventory/index";

definePage({
	meta: {
		menuType: "page",
		text: "下架调整",
		icon: "IconSetting",
	},
});

interface RemovalRow {
	id?: string;
	order_id?: string;
	goods_id?: string;
	goods_name?: string;
	goods_qua?: string;
	goods_quaok?: string;
}

const loading = ref(false);
const rows = ref<RemovalRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const selectedRows = ref<RemovalRow[]>([]);
const exporting = ref(false);

const query = ref({
	order_id: "",
	goods_id: "",
	goods_name: "",
});

// 详情抽屉
const detailVisible = ref(false);
const detailLoading = ref(false);
const detailData = ref<Record<string, unknown>>({});

// 编辑弹窗
const editVisible = ref(false);
const editSaving = ref(false);
const editForm = reactive({
	id: "",
	order_id: "",
	goods_id: "",
	goods_name: "",
	goods_qua: "",
	goods_quaok: "",
	bin_id_from: "",
	ku_wei_bian_ma: "",
	base_unit: "",
	goods_pro_data: "",
});

// 批量修改弹窗
const batchVisible = ref(false);
const batchSaving = ref(false);
const batchForm = reactive({
	goods_qua: "",
	goods_quaok: "",
	base_unit: "",
	goods_pro_data: "",
	bin_id_from: "",
	ku_wei_bian_ma: "",
});

function loadData() {
	loading.value = true;
	listRemovalAdjust(
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
			ElMessage.error("下架调整数据加载失败");
		},
	);
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	query.value = { order_id: "", goods_id: "", goods_name: "" };
	pageIndex.value = 1;
	loadData();
}

function handleSelectionChange(selection: RemovalRow[]) {
	selectedRows.value = selection;
}

async function handleDetail(row: RemovalRow) {
	detailVisible.value = true;
	detailLoading.value = true;
	getRemovalDetail(
		{
			order_id: row.order_id ?? "",
			goods_id: row.goods_id ?? "",
			goods_name: row.goods_name ?? "",
		},
		(data: any) => {
			detailData.value = data ?? {};
			detailLoading.value = false;
		},
		() => {
			detailLoading.value = false;
			ElMessage.error("获取下架货物详情失败");
		},
	);
}

function handleEdit(row: RemovalRow) {
	if (!row.id) {
		ElMessage.warning("该记录缺少唯一标识，无法修改");
		return;
	}
	editForm.id = row.id ?? "";
	editForm.order_id = row.order_id ?? "";
	editForm.goods_id = row.goods_id ?? "";
	editForm.goods_name = row.goods_name ?? "";
	editForm.goods_qua = row.goods_qua ?? "";
	editForm.goods_quaok = row.goods_quaok ?? "";
	editForm.bin_id_from = "";
	editForm.ku_wei_bian_ma = "";
	editForm.base_unit = "";
	editForm.goods_pro_data = "";
	editVisible.value = true;
}

async function handleEditSave() {
	editSaving.value = true;
	try {
		await updateRemoval({ ...editForm });
		ElMessage.success("下架货物已修改");
		editVisible.value = false;
		loadData();
	} catch {
		ElMessage.error("修改下架货物失败");
	} finally {
		editSaving.value = false;
	}
}

function openBatch() {
	if (selectedRows.value.length === 0) {
		ElMessage.warning("请先勾选要批量修改的下架货物");
		return;
	}
	batchForm.goods_qua = "";
	batchForm.goods_quaok = "";
	batchForm.base_unit = "";
	batchForm.goods_pro_data = "";
	batchForm.bin_id_from = "";
	batchForm.ku_wei_bian_ma = "";
	batchVisible.value = true;
}

async function handleBatchSave() {
	batchSaving.value = true;
	try {
		const list = selectedRows.value
			.filter((r) => r.id)
			.map((r) => ({
				id: r.id,
				goods_qua: batchForm.goods_qua || undefined,
				goods_quaok: batchForm.goods_quaok || undefined,
				base_unit: batchForm.base_unit || undefined,
				goods_pro_data: batchForm.goods_pro_data || undefined,
				bin_id_from: batchForm.bin_id_from || undefined,
				ku_wei_bian_ma: batchForm.ku_wei_bian_ma || undefined,
			}));
		await batchUpdateRemoval({ dtoList: list });
		ElMessage.success(`已批量修改 ${list.length} 条下架货物`);
		batchVisible.value = false;
		loadData();
	} catch {
		ElMessage.error("批量修改下架货物失败");
	} finally {
		batchSaving.value = false;
	}
}

async function handleExport() {
	exporting.value = true;
	try {
		const blob = await exportRemoval(query.value);
		saveBlob(blob, "下架调整数据.xlsx");
	} catch {
		ElMessage.error("导出下架调整数据失败");
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
	<section class="takedown-adjustment-root">
		<el-card shadow="never" class="query-card">
			<el-form :model="query" inline label-width="90px">
				<el-form-item label="原始单据号">
					<el-input v-model="query.order_id" clearable placeholder="请输入原始单据号" style="width: 160px" />
				</el-form-item>
				<el-form-item label="商品编码">
					<el-input v-model="query.goods_id" clearable placeholder="请输入商品编码" style="width: 140px" />
				</el-form-item>
				<el-form-item label="商品名称">
					<el-input v-model="query.goods_name" clearable placeholder="请输入商品名称" style="width: 150px" />
				</el-form-item>
				<el-form-item>
					<el-button type="primary" @click="handleSearch">查询</el-button>
					<el-button @click="handleReset">重置</el-button>
					<el-button :loading="exporting" @click="handleExport">导出</el-button>
				</el-form-item>
			</el-form>
		</el-card>

		<div class="tool-bar">
			<el-button type="primary" @click="openBatch">
				批量修改{{ selectedRows.length ? `（${selectedRows.length}）` : "" }}
			</el-button>
			<el-button @click="loadData">刷新</el-button>
		</div>

		<el-table
			v-loading="loading"
			:data="rows"
			border
			stripe
			style="width: 100%"
			@selection-change="handleSelectionChange"
		>
			<el-table-column type="selection" width="45" />
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="id" label="调整单ID" min-width="180" show-overflow-tooltip />
			<el-table-column prop="order_id" label="关联单号" min-width="160" show-overflow-tooltip />
			<el-table-column prop="goods_id" label="商品编码" width="150" show-overflow-tooltip />
			<el-table-column prop="goods_name" label="商品名称" min-width="180" show-overflow-tooltip />
			<el-table-column prop="goods_qua" label="数量" width="100" align="right" />
			<el-table-column label="操作" width="130" fixed="right">
				<template #default="{ row }">
					<el-button link type="primary" @click="handleDetail(row)">详情</el-button>
					<el-button link type="primary" @click="handleEdit(row)">修改</el-button>
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

		<el-drawer v-model="detailVisible" title="下架货物详情" size="400px">
			<div v-loading="detailLoading">
				<el-descriptions :column="1" border>
					<el-descriptions-item v-for="(value, key) in detailData" :key="key" :label="String(key)">
						{{ value ?? "-" }}
					</el-descriptions-item>
				</el-descriptions>
			</div>
		</el-drawer>

		<el-dialog v-model="editVisible" title="修改下架货物" width="480px">
			<el-form :model="editForm" label-width="90px">
				<el-form-item label="货物ID">
					<el-input v-model="editForm.id" disabled />
				</el-form-item>
				<el-form-item label="数量">
					<el-input v-model="editForm.goods_qua" clearable />
				</el-form-item>
				<el-form-item label="完成数量">
					<el-input v-model="editForm.goods_quaok" clearable />
				</el-form-item>
				<el-form-item label="来源储位">
					<el-input v-model="editForm.bin_id_from" clearable placeholder="留空则不修改" />
				</el-form-item>
				<el-form-item label="目的储位">
					<el-input v-model="editForm.ku_wei_bian_ma" clearable placeholder="留空则不修改" />
				</el-form-item>
				<el-form-item label="基本单位">
					<el-input v-model="editForm.base_unit" clearable placeholder="留空则不修改" />
				</el-form-item>
				<el-form-item label="生产日期">
					<el-input v-model="editForm.goods_pro_data" clearable placeholder="留空则不修改" />
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="editVisible = false">取消</el-button>
				<el-button type="primary" :loading="editSaving" @click="handleEditSave">保存</el-button>
			</template>
		</el-dialog>

		<el-dialog v-model="batchVisible" title="批量修改下架货物" width="480px">
			<el-alert
				type="info"
				:closable="false"
				:title="`将对选中的 ${selectedRows.length} 条记录应用以下修改（留空保持原值）`"
				style="margin-bottom: 16px"
			/>
			<el-form :model="batchForm" label-width="90px">
				<el-form-item label="数量">
					<el-input v-model="batchForm.goods_qua" clearable placeholder="统一数量" />
				</el-form-item>
				<el-form-item label="完成数量">
					<el-input v-model="batchForm.goods_quaok" clearable placeholder="统一完成数量" />
				</el-form-item>
				<el-form-item label="基本单位">
					<el-input v-model="batchForm.base_unit" clearable placeholder="统一基本单位" />
				</el-form-item>
				<el-form-item label="生产日期">
					<el-input v-model="batchForm.goods_pro_data" clearable placeholder="统一生产日期" />
				</el-form-item>
				<el-form-item label="来源储位">
					<el-input v-model="batchForm.bin_id_from" clearable placeholder="统一来源储位" />
				</el-form-item>
				<el-form-item label="目的储位">
					<el-input v-model="batchForm.ku_wei_bian_ma" clearable placeholder="统一目的储位" />
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="batchVisible = false">取消</el-button>
				<el-button type="primary" :loading="batchSaving" @click="handleBatchSave">保存</el-button>
			</template>
		</el-dialog>
	</section>
</template>

<style lang="scss" scoped>
.takedown-adjustment-root {
	width: 100%;

	.tool-bar {
		display: flex;
		align-items: center;
		gap: 16px;
		margin: 12px 0;
	}
}
</style>
