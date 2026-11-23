<script lang="ts" setup>
import { ref, reactive, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { UploadFile, UploadFiles } from "element-plus";
import {
	listTemperature,
	addTemperature,
	updateTemperature,
	deleteTemperature,
	importTemperature,
	exportTemperature,
	saveBlob,
} from "@/apis/daily-check/index";

definePage({
	meta: {
		menuType: "page",
		text: "温度维护",
		icon: "IconSetting",
	},
});

interface TemperatureRow {
	id?: string;
	wenduDd?: string;
	wenduCjsj?: string;
	wenduZhi?: number;
	wenduBz?: string;
}

const loading = ref(false);
const exporting = ref(false);
const rows = ref<TemperatureRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const selectedRows = ref<TemperatureRow[]>([]);

const dialogVisible = ref(false);
const dialogMode = ref<"add" | "edit">("add");
const dialogSaving = ref(false);
const formRef = ref();
const form = reactive({
	id: "",
	wenduDd: "",
	wenduCjsj: "",
	wenduZhi: 0,
	wenduBz: "",
});

const importVisible = ref(false);
const importSaving = ref(false);
const importFileList = ref<UploadFiles>([]);
const importFile = ref<File | null>(null);

const selectedIds = computed(() =>
	selectedRows.value.map(item => item.id).filter((id): id is string => !!id),
);

function formatDateTime(value?: string) {
	if (!value) return "";
	return value.replace("T", " ");
}

function temperatureTag(value?: number) {
	if (typeof value !== "number") return "info";
	if (value < 0) return "primary";
	if (value > 20) return "warning";
	return "success";
}

function loadData() {
	loading.value = true;
	listTemperature(
		{ pageIndex: pageIndex.value, pageSize: pageSize.value },
		(data: any) => {
			rows.value = data.rows ?? [];
			total.value = data.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("温度维护数据加载失败");
		},
	);
}

function handleSelectionChange(selection: TemperatureRow[]) {
	selectedRows.value = selection;
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

function resetForm() {
	form.id = "";
	form.wenduDd = "";
	form.wenduCjsj = "";
	form.wenduZhi = 0;
	form.wenduBz = "";
}

function openAdd() {
	dialogMode.value = "add";
	resetForm();
	dialogVisible.value = true;
}

function openEdit(row: TemperatureRow) {
	dialogMode.value = "edit";
	form.id = row.id ?? "";
	form.wenduDd = row.wenduDd ?? "";
	form.wenduCjsj = row.wenduCjsj ?? "";
	form.wenduZhi = row.wenduZhi ?? 0;
	form.wenduBz = row.wenduBz ?? "";
	dialogVisible.value = true;
}

async function submitForm() {
	const valid = await formRef.value?.validate().catch(() => false);
	if (!valid) return;
	dialogSaving.value = true;
	try {
		const payload = {
			wenduDd: form.wenduDd,
			wenduCjsj: form.wenduCjsj,
			wenduZhi: form.wenduZhi,
			wenduBz: form.wenduBz,
		};
		if (dialogMode.value === "add") {
			await addTemperature(payload);
		} else {
			await updateTemperature({ ...payload, id: form.id });
		}
		ElMessage.success(dialogMode.value === "add" ? "温度录入成功" : "温度修改成功");
		dialogVisible.value = false;
		loadData();
	} catch (err: any) {
		ElMessage.error(err?.message || "操作失败");
	} finally {
		dialogSaving.value = false;
	}
}

async function removeRow(row: TemperatureRow) {
	try {
		await ElMessageBox.confirm("确定删除该温度记录吗？", "提示", {
			type: "warning",
			confirmButtonText: "确定",
			cancelButtonText: "取消",
		});
	} catch {
		return;
	}
	try {
		await deleteTemperature([row.id as string]);
		ElMessage.success("删除成功");
		loadData();
	} catch (err: any) {
		ElMessage.error(err?.message || "删除失败");
	}
}

async function removeSelected() {
	if (selectedIds.value.length === 0) {
		ElMessage.warning("请先勾选要删除的温度记录");
		return;
	}
	try {
		await ElMessageBox.confirm(`确定删除选中的 ${selectedIds.value.length} 条温度记录吗？`, "提示", {
			type: "warning",
			confirmButtonText: "确定",
			cancelButtonText: "取消",
		});
	} catch {
		return;
	}
	try {
		await deleteTemperature(selectedIds.value);
		ElMessage.success("批量删除成功");
		loadData();
	} catch (err: any) {
		ElMessage.error(err?.message || "批量删除失败");
	}
}

async function handleExport() {
	exporting.value = true;
	try {
		const blob = await exportTemperature();
		saveBlob(blob, `温度数据_${Date.now()}.xlsx`);
		ElMessage.success("导出成功");
	} catch (err: any) {
		ElMessage.error(err?.message || "导出失败");
	} finally {
		exporting.value = false;
	}
}

function openImport() {
	importFile.value = null;
	importFileList.value = [];
	importVisible.value = true;
}

function handleImportChange(file: UploadFile) {
	importFile.value = file.raw ?? null;
}

function handleImportRemove() {
	importFile.value = null;
	importFileList.value = [];
}

async function submitImport() {
	if (!importFile.value) {
		ElMessage.warning("请选择要导入的 Excel 文件");
		return;
	}
	importSaving.value = true;
	try {
		await importTemperature(importFile.value);
		ElMessage.success("导入成功");
		importVisible.value = false;
		loadData();
	} catch (err: any) {
		ElMessage.error(err?.message || "导入失败");
	} finally {
		importSaving.value = false;
	}
}

onMounted(() => {
	loadData();
});
</script>

<template>
	<section class="temperature-maintain-root">
		<h2>温度维护</h2>

		<div class="tool-bar">
			<el-button type="success" @click="openAdd">录入</el-button>
			<el-button type="danger" @click="removeSelected">批量删除</el-button>
			<el-button @click="openImport">导入数据</el-button>
			<el-button type="warning" :loading="exporting" @click="handleExport">导出数据</el-button>
			<span class="tip">各库区温度采集记录</span>
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
			<el-table-column prop="wenduDd" label="温度地点" min-width="150" show-overflow-tooltip />
			<el-table-column label="采集时间" width="180">
				<template #default="{ row }">{{ formatDateTime(row.wenduCjsj) }}</template>
			</el-table-column>
			<el-table-column label="温度(℃)" width="120" align="center">
				<template #default="{ row }">
					<el-tag :type="temperatureTag(row.wenduZhi)">{{ row.wenduZhi }} ℃</el-tag>
				</template>
			</el-table-column>
			<el-table-column prop="wenduBz" label="备注" min-width="200" show-overflow-tooltip />
			<el-table-column label="操作" width="130" fixed="right">
				<template #default="{ row }">
					<el-button link type="primary" @click="openEdit(row)">编辑</el-button>
					<el-button link type="danger" @click="removeRow(row)">删除</el-button>
				</template>
			</el-table-column>
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

		<el-dialog
			v-model="dialogVisible"
			:title="dialogMode === 'add' ? '录入温度' : '修改温度'"
			width="460px"
			:close-on-click-modal="false"
			destroy-on-close
		>
			<el-form ref="formRef" :model="form" label-width="90px">
				<el-form-item
					label="温度地点"
					prop="wenduDd"
					:rules="[{ required: true, message: '请输入温度地点', trigger: 'blur' }]"
				>
					<el-input v-model="form.wenduDd" placeholder="如：一号冷库" />
				</el-form-item>
				<el-form-item
					label="采集时间"
					prop="wenduCjsj"
					:rules="[{ required: true, message: '请选择采集时间', trigger: 'change' }]"
				>
					<el-date-picker
						v-model="form.wenduCjsj"
						type="datetime"
						value-format="YYYY-MM-DD HH:mm:ss"
						placeholder="选择采集时间"
						style="width: 100%"
					/>
				</el-form-item>
				<el-form-item
					label="温度值"
					prop="wenduZhi"
					:rules="[{ required: true, message: '请输入温度值', trigger: 'blur' }]"
				>
					<el-input-number
						v-model="form.wenduZhi"
						:step="0.1"
						:precision="1"
						controls-position="right"
						style="width: 100%"
					/>
				</el-form-item>
				<el-form-item label="备注">
					<el-input v-model="form.wenduBz" type="textarea" :rows="3" />
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="dialogVisible = false">取消</el-button>
				<el-button type="primary" :loading="dialogSaving" @click="submitForm">确定</el-button>
			</template>
		</el-dialog>

		<el-dialog v-model="importVisible" title="导入温度数据" width="460px" :close-on-click-modal="false">
			<el-upload
				v-model:file-list="importFileList"
				:auto-upload="false"
				:limit="1"
				accept=".xlsx,.xls"
				:on-change="handleImportChange"
				:on-remove="handleImportRemove"
				:on-exceed="() => ElMessage.warning('只能选择一个文件')"
			>
				<el-button type="primary">选择文件</el-button>
				<template #tip>
					<div class="el-upload__tip">请使用导出的温度模板格式导入</div>
				</template>
			</el-upload>
			<template #footer>
				<el-button @click="importVisible = false">取消</el-button>
				<el-button type="primary" :loading="importSaving" @click="submitImport">开始导入</el-button>
			</template>
		</el-dialog>
	</section>
</template>

<style lang="scss" scoped>
.temperature-maintain-root {
	width: 100%;

	.tool-bar {
		display: flex;
		align-items: center;
		gap: 8px;
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
