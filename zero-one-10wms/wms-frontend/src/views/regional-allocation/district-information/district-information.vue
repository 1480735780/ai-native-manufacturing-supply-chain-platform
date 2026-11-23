<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { UploadFilled } from "@element-plus/icons-vue";
import {
	listDistrictAreas,
	addDistrictArea,
	updateDistrictArea,
	removeDistrictArea,
	removeDistrictAreasBatch,
	importDistrictAreas,
	exportDistrictAreas,
	districtAreaFileName,
	saveBlob,
} from "@/apis/reference/index";

definePage({
	meta: {
		menuType: "page",
		text: "片区信息",
		icon: "IconSetting",
	},
});

interface Row {
	id?: string;
	area_code?: string;
	area_name?: string;
}

const loading = ref(false);
const rows = ref<Row[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const selectedRows = ref<Row[]>([]);

const query = ref({ area_code: "", area_name: "" });

function loadData() {
	loading.value = true;
	listDistrictAreas(
		{
			pageIndex: pageIndex.value,
			pageSize: pageSize.value,
			area_code: query.value.area_code,
			area_name: query.value.area_name,
		},
		(data: any) => {
			rows.value = data.rows ?? [];
			total.value = data.total || 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("片区信息加载失败");
		},
	);
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	query.value = { area_code: "", area_name: "" };
	handleSearch();
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

function handleSelectionChange(sel: Row[]) {
	selectedRows.value = sel;
}

function fallbackPage() {
	const maxPage = Math.max(1, Math.ceil(total.value / pageSize.value));
	if (pageIndex.value > maxPage) pageIndex.value = maxPage;
	loadData();
}

const dialogVisible = ref(false);
const isEdit = ref(false);
const formRef = ref();
const form = ref({ id: "", area_code: "", area_name: "" });
const rules = {
	area_code: [{ required: true, message: "请输入片区代码", trigger: "blur" }],
	area_name: [{ required: true, message: "请输入片区名称", trigger: "blur" }],
};

function openAdd() {
	isEdit.value = false;
	form.value = { id: "", area_code: "", area_name: "" };
	dialogVisible.value = true;
}

function openEdit(row: Row) {
	isEdit.value = true;
	form.value = { id: row.id ?? "", area_code: row.area_code ?? "", area_name: row.area_name ?? "" };
	dialogVisible.value = true;
}

async function submitForm() {
	await formRef.value?.validate();
	try {
		if (isEdit.value) {
			await updateDistrictArea({ id: form.value.id, area_code: form.value.area_code, area_name: form.value.area_name });
			ElMessage.success("修改成功");
		} else {
			await addDistrictArea({ area_code: form.value.area_code, area_name: form.value.area_name });
			ElMessage.success("录入成功");
		}
		dialogVisible.value = false;
		loadData();
	} catch (err: any) {
		ElMessage.error(err?.message || "操作失败");
	}
}

async function handleDelete(row: Row) {
	await ElMessageBox.confirm(`确定要删除「${row.area_name}」吗？`, "提示", { type: "warning" });
	try {
		await removeDistrictArea(row.id!);
		ElMessage.success("删除成功");
		fallbackPage();
	} catch (err: any) {
		ElMessage.error(err?.message || "删除失败");
	}
}

async function handleBatchDelete() {
	if (selectedRows.value.length === 0) {
		ElMessage.warning("请至少选择一条记录");
		return;
	}
	await ElMessageBox.confirm(`确定要删除选中的 ${selectedRows.value.length} 条记录吗？`, "提示", { type: "warning" });
	try {
		const ids = selectedRows.value.map((r) => r.id!);
		const msg = await removeDistrictAreasBatch(ids);
		ElMessage.success(typeof msg === "string" ? msg : "批量删除成功");
		fallbackPage();
	} catch (err: any) {
		ElMessage.error(err?.message || "批量删除失败");
	}
}

const importVisible = ref(false);
const importFileRef = ref<File | null>(null);

function onImportFileChange(file: any) {
	importFileRef.value = file.raw;
}

async function submitImport() {
	if (!importFileRef.value) {
		ElMessage.warning("请选择 Excel 文件");
		return;
	}
	try {
		const msg = await importDistrictAreas(importFileRef.value);
		ElMessage.success(typeof msg === "string" ? msg : "导入成功");
		importVisible.value = false;
		loadData();
	} catch (err: any) {
		ElMessage.error(err?.message || "导入失败");
	}
}

async function handleExport() {
	try {
		const blob = await exportDistrictAreas();
		saveBlob(new Blob([blob]), districtAreaFileName());
		ElMessage.success("导出成功");
	} catch {
		ElMessage.error("导出失败");
	}
}

onMounted(() => {
	loadData();
});
</script>

<template>
	<section class="district-information-root">
		<div class="query-bar">
			<el-form inline @submit.prevent="handleSearch">
				<el-form-item label="片区代码">
					<el-input v-model="query.area_code" placeholder="请输入代码" clearable @keyup.enter="handleSearch" />
				</el-form-item>
				<el-form-item label="片区名称">
					<el-input v-model="query.area_name" placeholder="请输入名称" clearable @keyup.enter="handleSearch" />
				</el-form-item>
				<el-form-item>
					<el-button type="primary" @click="handleSearch">查询</el-button>
					<el-button @click="handleReset">重置</el-button>
				</el-form-item>
			</el-form>
		</div>

		<div class="tool-bar">
			<el-button type="primary" @click="openAdd">录入</el-button>
			<el-button type="danger" :disabled="selectedRows.length === 0" @click="handleBatchDelete">批量删除</el-button>
			<el-button @click="importVisible = true">导入</el-button>
			<el-button @click="handleExport">导出</el-button>
			<el-button @click="loadData">刷新</el-button>
		</div>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%" @selection-change="handleSelectionChange">
			<el-table-column type="selection" width="48" />
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="area_code" label="片区代码" width="220" />
			<el-table-column prop="area_name" label="片区名称" min-width="220" />
			<el-table-column prop="id" label="ID" min-width="200" show-overflow-tooltip />
			<el-table-column label="操作" width="150" fixed="right">
				<template #default="{ row }">
					<el-button link type="primary" @click="openEdit(row)">修改</el-button>
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

		<el-dialog v-model="dialogVisible" :title="isEdit ? '修改片区信息' : '录入片区信息'" width="460px">
			<el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
				<el-form-item label="片区代码" prop="area_code">
					<el-input v-model="form.area_code" placeholder="请输入代码" />
				</el-form-item>
				<el-form-item label="片区名称" prop="area_name">
					<el-input v-model="form.area_name" placeholder="请输入名称" />
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="dialogVisible = false">取消</el-button>
				<el-button type="primary" @click="submitForm">确定</el-button>
			</template>
		</el-dialog>

		<el-dialog v-model="importVisible" title="导入片区信息" width="480px">
			<el-upload drag action="#" :auto-upload="false" :limit="1" :on-change="onImportFileChange" accept=".xlsx,.xls">
				<el-icon class="el-icon--upload"><upload-filled /></el-icon>
				<div class="el-upload__text">拖拽文件到此处或 <em>点击选择</em></div>
				<template #tip>
					<div class="el-upload__tip">只能上传 Excel 文件，表头行会被自动跳过</div>
				</template>
			</el-upload>
			<template #footer>
				<el-button @click="importVisible = false">取消</el-button>
				<el-button type="primary" @click="submitImport">开始导入</el-button>
			</template>
		</el-dialog>
	</section>
</template>

<style lang="scss" scoped>
.district-information-root {
	width: 100%;

	.query-bar {
		margin: 12px 0;
	}

	.tool-bar {
		display: flex;
		align-items: center;
		gap: 4px;
		margin: 8px 0 12px;
	}
}
</style>
