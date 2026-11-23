<script lang="ts" setup>
import { reactive, ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
	listUpAdjust,
	getUpAdjustDetail,
	updateUpAdjust,
	batchUpdateUpAdjust,
	exportUpAdjust,
	saveBlob,
} from "@/apis/inventory/index";

definePage({
	meta: {
		menuType: "page",
		text: "上架调整",
		icon: "IconSetting",
	},
});

interface UpAdjustRow {
	id?: string;
	create_date?: string;
	goods_qua?: string;
	ku_wei_bian_ma?: string;
	bin_id?: string;
	goods_id?: string;
	goods_name?: string;
	goods_unit?: string;
	base_unit?: string;
	base_goodscount?: string;
	order_id?: string;
	cus_code?: string;
}

const loading = ref(false);
const rows = ref<UpAdjustRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const keyword = ref("");
const selectedRows = ref<UpAdjustRow[]>([]);
const exporting = ref(false);

// 详情抽屉
const detailVisible = ref(false);
const detailLoading = ref(false);
const detailData = ref<Record<string, unknown>>({});

// 编辑弹窗
const editVisible = ref(false);
const editSaving = ref(false);
const editForm = reactive({
	id: "",
	goods_qua: "",
	goods_pro_data: "",
	bin_id: "",
	ku_wei_bian_ma: "",
	base_unit: "",
});

// 批量修改弹窗
const batchVisible = ref(false);
const batchSaving = ref(false);
const batchForm = reactive({
	goods_qua: "",
	goods_pro_data: "",
	bin_id: "",
	ku_wei_bian_ma: "",
	base_unit: "",
});

function loadData() {
	loading.value = true;
	const params: Record<string, unknown> = {
		pageIndex: pageIndex.value,
		pageSize: pageSize.value,
	};
	if (keyword.value) {
		params.goods_name = keyword.value;
	}
	listUpAdjust(
		params,
		(data: any) => {
			rows.value = data.rows ?? [];
			total.value = data.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("上架调整数据加载失败");
		},
	);
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	keyword.value = "";
	pageIndex.value = 1;
	loadData();
}

function handleSelectionChange(selection: UpAdjustRow[]) {
	selectedRows.value = selection;
}

async function handleDetail(row: UpAdjustRow) {
	if (!row.id) {
		ElMessage.warning("该记录缺少唯一标识");
		return;
	}
	detailVisible.value = true;
	detailLoading.value = true;
	getUpAdjustDetail(
		row.id,
		(data: any) => {
			detailData.value = data ?? {};
			detailLoading.value = false;
		},
		() => {
			detailLoading.value = false;
			ElMessage.error("获取上架货物详情失败");
		},
	);
}

function handleEdit(row: UpAdjustRow) {
	if (!row.id) {
		ElMessage.warning("该记录缺少唯一标识，无法修改");
		return;
	}
	editForm.id = row.id ?? "";
	editForm.goods_qua = row.goods_qua ?? "";
	editForm.goods_pro_data = "";
	editForm.bin_id = row.bin_id ?? "";
	editForm.ku_wei_bian_ma = row.ku_wei_bian_ma ?? "";
	editForm.base_unit = row.base_unit ?? "";
	editVisible.value = true;
}

async function handleEditSave() {
	editSaving.value = true;
	try {
		await updateUpAdjust({ ...editForm });
		ElMessage.success("上架货物已修改");
		editVisible.value = false;
		loadData();
	} catch {
		ElMessage.error("修改上架货物失败");
	} finally {
		editSaving.value = false;
	}
}

function openBatch() {
	if (selectedRows.value.length === 0) {
		ElMessage.warning("请先勾选要批量修改的上架货物");
		return;
	}
	batchForm.goods_qua = "";
	batchForm.goods_pro_data = "";
	batchForm.bin_id = "";
	batchForm.ku_wei_bian_ma = "";
	batchForm.base_unit = "";
	batchVisible.value = true;
}

async function handleBatchSave() {
	batchSaving.value = true;
	try {
		const list = selectedRows.value.map((r) => ({
			id: r.id,
			order_id: r.order_id ?? "",
			goods_id: r.goods_id ?? "",
			goods_name: r.goods_name ?? "",
			goods_qua: batchForm.goods_qua || r.goods_qua || "",
			goods_pro_data: batchForm.goods_pro_data || undefined,
			bin_id: batchForm.bin_id || r.bin_id || "",
			ku_wei_bian_ma: batchForm.ku_wei_bian_ma || r.ku_wei_bian_ma || "",
			base_unit: batchForm.base_unit || r.base_unit || "",
		}));
		await batchUpdateUpAdjust({ dtoList: list });
		ElMessage.success(`已批量修改 ${list.length} 条上架货物`);
		batchVisible.value = false;
		loadData();
	} catch {
		ElMessage.error("批量修改上架货物失败");
	} finally {
		batchSaving.value = false;
	}
}

async function handleExport() {
	exporting.value = true;
	try {
		const params: Record<string, unknown> = {};
		if (keyword.value) params.goods_name = keyword.value;
		const blob = await exportUpAdjust(params);
		saveBlob(blob, "上架调整数据.xlsx");
	} catch {
		ElMessage.error("导出上架调整数据失败");
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
	<section class="shelf-adjustment-root">
		<el-card shadow="never" class="query-card">
			<el-form :model="{ keyword }" inline>
				<el-form-item label="商品名称">
					<el-input v-model="keyword" clearable placeholder="请输入商品名称" style="width: 180px" />
				</el-form-item>
				<el-form-item>
					<el-button type="primary" @click="handleSearch">查询</el-button>
					<el-button @click="handleReset">重置</el-button>
				</el-form-item>
			</el-form>
		</el-card>

		<div class="tool-bar">
			<el-button type="primary" @click="openBatch">
				批量修改{{ selectedRows.length ? `（${selectedRows.length}）` : "" }}
			</el-button>
			<el-button :loading="exporting" @click="handleExport">导出</el-button>
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
			<el-table-column prop="create_date" label="创建日期" width="170" />
			<el-table-column prop="ku_wei_bian_ma" label="储位" width="120" show-overflow-tooltip />
			<el-table-column prop="bin_id" label="托盘" width="120" show-overflow-tooltip />
			<el-table-column prop="goods_id" label="商品编码" width="120" show-overflow-tooltip />
			<el-table-column prop="goods_name" label="商品名称" min-width="160" show-overflow-tooltip />
			<el-table-column prop="goods_qua" label="数量" width="90" align="right" />
			<el-table-column prop="goods_unit" label="单位" width="80" />
			<el-table-column prop="base_goodscount" label="基本数量" width="100" align="right" />
			<el-table-column prop="base_unit" label="基本单位" width="90" />
			<el-table-column prop="order_id" label="关联单号" min-width="150" show-overflow-tooltip />
			<el-table-column prop="cus_code" label="客户编码" width="110" />
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

		<el-drawer v-model="detailVisible" title="上架货物详情" size="400px">
			<div v-loading="detailLoading">
				<el-descriptions :column="1" border>
					<el-descriptions-item v-for="(value, key) in detailData" :key="key" :label="String(key)">
						{{ value ?? "-" }}
					</el-descriptions-item>
				</el-descriptions>
			</div>
		</el-drawer>

		<el-dialog v-model="editVisible" title="修改上架货物" width="480px">
			<el-form :model="editForm" label-width="90px">
				<el-form-item label="货物ID">
					<el-input v-model="editForm.id" disabled />
				</el-form-item>
				<el-form-item label="数量">
					<el-input v-model="editForm.goods_qua" clearable />
				</el-form-item>
				<el-form-item label="生产日期">
					<el-input v-model="editForm.goods_pro_data" clearable placeholder="留空则不修改" />
				</el-form-item>
				<el-form-item label="托盘">
					<el-input v-model="editForm.bin_id" clearable />
				</el-form-item>
				<el-form-item label="储位">
					<el-input v-model="editForm.ku_wei_bian_ma" clearable />
				</el-form-item>
				<el-form-item label="基本单位">
					<el-input v-model="editForm.base_unit" clearable />
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="editVisible = false">取消</el-button>
				<el-button type="primary" :loading="editSaving" @click="handleEditSave">保存</el-button>
			</template>
		</el-dialog>

		<el-dialog v-model="batchVisible" title="批量修改上架货物" width="480px">
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
				<el-form-item label="生产日期">
					<el-input v-model="batchForm.goods_pro_data" clearable placeholder="统一生产日期" />
				</el-form-item>
				<el-form-item label="托盘">
					<el-input v-model="batchForm.bin_id" clearable placeholder="统一托盘" />
				</el-form-item>
				<el-form-item label="储位">
					<el-input v-model="batchForm.ku_wei_bian_ma" clearable placeholder="统一储位" />
				</el-form-item>
				<el-form-item label="基本单位">
					<el-input v-model="batchForm.base_unit" clearable placeholder="统一基本单位" />
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
.shelf-adjustment-root {
	width: 100%;

	.tool-bar {
		display: flex;
		align-items: center;
		gap: 16px;
		margin: 12px 0;
	}
}
</style>
