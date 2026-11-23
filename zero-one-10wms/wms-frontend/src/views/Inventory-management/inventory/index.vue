<script lang="ts" setup>
import { reactive, ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { FormInstance } from "element-plus";
import { listCheck, updateCheckTask, deleteSttTask, exportCheck, saveBlob } from "@/apis/inventory/index";

definePage({
	meta: {
		menuType: "page",
		text: "盘点",
		icon: "IconSetting",
	},
});

interface CheckRow {
	id?: string;
	create_name?: string;
	create_date?: string;
	bin_id?: string;
	tin_id?: string;
	goods_id?: string;
	goods_name?: string;
	goods_qua?: string;
	goods_unit?: string;
	goods_pro_data?: string;
	goods_batch?: string;
	stt_qua?: string;
	cus_name?: string;
	cus_code?: string;
	stt_sta?: string;
	stt_type?: string;
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
	cus_code: "",
	stt_sta: "",
});

// 编辑弹窗
const editVisible = ref(false);
const editSaving = ref(false);
const editFormRef = ref<FormInstance>();
const editForm = reactive({
	id: "",
	stt_qua: "",
	goods_qua: "",
	goods_batch: "",
	goods_pro_data: "",
	bin_id: "",
	tin_id: "",
	stt_sta: "",
});

function statusType(value?: string) {
	if (value === "已完成") return "success";
	if (value === "盘点中" || value === "计划中") return "warning";
	if (value === "已删除") return "danger";
	return "info";
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
			ElMessage.error("盘点数据加载失败");
		},
	);
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	query.value = { bin_id: "", tin_id: "", goods_id: "", goods_name: "", cus_code: "", stt_sta: "" };
	pageIndex.value = 1;
	loadData();
}

function handleEdit(row: CheckRow) {
	if (!row.id) {
		ElMessage.warning("该记录缺少唯一标识，无法编辑");
		return;
	}
	editForm.id = row.id ?? "";
	editForm.stt_qua = row.stt_qua ?? "";
	editForm.goods_qua = row.goods_qua ?? "";
	editForm.goods_batch = row.goods_batch ?? "";
	editForm.goods_pro_data = row.goods_pro_data ?? "";
	editForm.bin_id = row.bin_id ?? "";
	editForm.tin_id = row.tin_id ?? "";
	editForm.stt_sta = row.stt_sta ?? "";
	editVisible.value = true;
}

async function handleEditSave() {
	editSaving.value = true;
	try {
		await updateCheckTask({ ...editForm });
		ElMessage.success("盘点任务已更新");
		editVisible.value = false;
		loadData();
	} catch {
		ElMessage.error("更新盘点任务失败");
	} finally {
		editSaving.value = false;
	}
}

async function handleDelete(row: CheckRow) {
	if (!row.id) {
		ElMessage.warning("该记录缺少唯一标识，无法删除");
		return;
	}
	try {
		await ElMessageBox.confirm("确定删除该盘点任务吗？删除后不可恢复。", "删除盘点任务", {
			confirmButtonText: "删除",
			cancelButtonText: "取消",
			type: "warning",
		});
	} catch {
		return;
	}
	try {
		await deleteSttTask(row.id);
		ElMessage.success("盘点任务已删除");
		loadData();
	} catch {
		ElMessage.error("删除盘点任务失败");
	}
}

async function handleExport() {
	exporting.value = true;
	try {
		const blob = await exportCheck(query.value);
		saveBlob(blob, "盘点任务列表.xlsx");
	} catch {
		ElMessage.error("导出失败");
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
	<section class="inventory-root">
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
				<el-form-item label="客户编码">
					<el-input v-model="query.cus_code" clearable placeholder="请输入客户编码" style="width: 140px" />
				</el-form-item>
				<el-form-item label="盘点状态">
					<el-select v-model="query.stt_sta" clearable placeholder="全部" style="width: 130px">
						<el-option label="未盘点" value="未盘点" />
						<el-option label="盘点中" value="盘点中" />
						<el-option label="已完成" value="已完成" />
					</el-select>
				</el-form-item>
				<el-form-item>
					<el-button type="primary" @click="handleSearch">查询</el-button>
					<el-button @click="handleReset">重置</el-button>
				</el-form-item>
			</el-form>
		</el-card>

		<div class="tool-bar">
			<el-button :loading="exporting" @click="handleExport">导出盘点任务</el-button>
			<el-button @click="loadData">刷新</el-button>
		</div>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%">
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="bin_id" label="储位" width="110" show-overflow-tooltip />
			<el-table-column prop="tin_id" label="托盘" width="110" show-overflow-tooltip />
			<el-table-column prop="goods_id" label="商品编码" width="110" show-overflow-tooltip />
			<el-table-column prop="goods_name" label="商品名称" min-width="130" show-overflow-tooltip />
			<el-table-column prop="goods_qua" label="账面数量" width="100" align="right" />
			<el-table-column prop="stt_qua" label="盘点数量" width="100" align="right" />
			<el-table-column prop="goods_unit" label="单位" width="70" />
			<el-table-column prop="goods_pro_data" label="生产日期" width="110" />
			<el-table-column prop="goods_batch" label="批次" width="110" show-overflow-tooltip />
			<el-table-column prop="cus_code" label="客户编码" width="100" />
			<el-table-column prop="cus_name" label="客户名称" min-width="160" show-overflow-tooltip />
			<el-table-column prop="stt_type" label="盘点类型" width="100" />
			<el-table-column label="盘点状态" width="100">
				<template #default="{ row }">
					<el-tag :type="statusType(row.stt_sta)">{{ row.stt_sta || "-" }}</el-tag>
				</template>
			</el-table-column>
			<el-table-column prop="create_name" label="创建人" width="100" />
			<el-table-column prop="create_date" label="创建日期" width="160" />
			<el-table-column label="操作" width="130" fixed="right">
				<template #default="{ row }">
					<el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
					<el-button link type="danger" @click="handleDelete(row)">删除</el-button>
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

		<el-dialog v-model="editVisible" title="编辑盘点任务" width="520px">
			<el-form ref="editFormRef" :model="editForm" label-width="90px">
				<el-form-item label="任务ID">
					<el-input v-model="editForm.id" disabled />
				</el-form-item>
				<el-form-item label="账面数量">
					<el-input v-model="editForm.goods_qua" clearable placeholder="账面数量（留空则不修改）" />
				</el-form-item>
				<el-form-item label="盘点数量">
					<el-input v-model="editForm.stt_qua" clearable placeholder="实盘数量（留空则不修改）" />
				</el-form-item>
				<el-form-item label="批次">
					<el-input v-model="editForm.goods_batch" clearable placeholder="批次（留空则不修改）" />
				</el-form-item>
				<el-form-item label="生产日期">
					<el-input v-model="editForm.goods_pro_data" clearable placeholder="如 2024-01-01（留空则不修改）" />
				</el-form-item>
				<el-form-item label="储位">
					<el-input v-model="editForm.bin_id" clearable placeholder="储位（留空则不修改）" />
				</el-form-item>
				<el-form-item label="托盘">
					<el-input v-model="editForm.tin_id" clearable placeholder="托盘（留空则不修改）" />
				</el-form-item>
				<el-form-item label="盘点状态">
					<el-input v-model="editForm.stt_sta" clearable placeholder="如 计划中/盘点中/已完成（留空则不修改）" />
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="editVisible = false">取消</el-button>
				<el-button type="primary" :loading="editSaving" @click="handleEditSave">保存</el-button>
			</template>
		</el-dialog>
	</section>
</template>

<style lang="scss" scoped>
.inventory-root {
	width: 100%;

	.tool-bar {
		display: flex;
		align-items: center;
		gap: 16px;
		margin: 12px 0;
	}
}
</style>
