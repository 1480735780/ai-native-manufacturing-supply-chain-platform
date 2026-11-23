<script lang="ts" setup>
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { UploadFile, UploadFiles } from "element-plus";
import {
	listCompanyAttributes,
	addCompanyAttribute,
	modifyCompanyAttribute,
	removeCompanyAttributes,
	downloadCompanyAttributes,
	uploadCompanyAttributes,
	saveBlob,
} from "@/apis/enterprise-config/index";

definePage({
	meta: {
		menuType: "page",
		text: "企业属性",
		icon: "Collection",
	},
});

interface AttributeRow {
	id?: string;
	com_type_code?: string;
	com_type_name?: string;
}

const loading = ref(false);
const rows = ref<AttributeRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const keyword = ref({ code: "", name: "" });

const dialogVisible = ref(false);
const dialogMode = ref<"add" | "edit">("add");
const saving = ref(false);
const formRef = ref();
const form = reactive({ id: "", com_type_code: "", com_type_name: "" });

const importVisible = ref(false);
const importSaving = ref(false);
const importFile = ref<File | null>(null);
const importFileList = ref<UploadFiles>([]);

const selectedRows = ref<AttributeRow[]>([]);

function errText(err: any, fallback: string) {
	return err?.data?.message || err?.message || err?.response?.data?.message || fallback;
}

function loadData() {
	loading.value = true;
	listCompanyAttributes(
		{
			pageIndex: pageIndex.value,
			pageSize: pageSize.value,
			com_type_code: keyword.value.code,
			com_type_name: keyword.value.name,
		},
		(data: any) => {
			rows.value = data?.rows ?? [];
			total.value = data?.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("企业属性加载失败");
		},
	);
}

function handleSearch() {
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

function openAdd() {
	dialogMode.value = "add";
	Object.assign(form, { id: "", com_type_code: "", com_type_name: "" });
	dialogVisible.value = true;
}
function openEdit(row: AttributeRow) {
	dialogMode.value = "edit";
	Object.assign(form, {
		id: row.id ?? "",
		com_type_code: row.com_type_code ?? "",
		com_type_name: row.com_type_name ?? "",
	});
	dialogVisible.value = true;
}

async function submitForm() {
	if (!formRef.value) return;
	try {
		await formRef.value.validate();
	} catch {
		return;
	}
	saving.value = true;
	try {
		if (dialogMode.value === "add") {
			await addCompanyAttribute({ com_type_code: form.com_type_code, com_type_name: form.com_type_name });
		} else {
			await modifyCompanyAttribute({
				id: form.id,
				com_type_code: form.com_type_code,
				com_type_name: form.com_type_name,
			});
		}
		ElMessage.success(dialogMode.value === "add" ? "录入成功" : "修改成功");
		dialogVisible.value = false;
		loadData();
	} catch (err: any) {
		ElMessage.error(errText(err, "保存失败"));
	} finally {
		saving.value = false;
	}
}

async function removeRow(row: AttributeRow) {
	if (!row.id) {
		ElMessage.warning("该记录缺少主键，无法删除");
		return;
	}
	try {
		await ElMessageBox.confirm(`确认删除企业属性「${row.com_type_name}」？`, "提示", { type: "warning" });
	} catch {
		return;
	}
	try {
		await removeCompanyAttributes([row.id]);
		ElMessage.success("删除成功");
		loadData();
	} catch (err: any) {
		ElMessage.error(errText(err, "删除失败"));
	}
}

async function exportData() {
	try {
		const blob = await downloadCompanyAttributes(`企业属性_${Date.now()}.xlsx`);
		saveBlob(blob, `企业属性_${Date.now()}.xlsx`);
		ElMessage.success("导出成功");
	} catch (err: any) {
		ElMessage.error(errText(err, "导出失败"));
	}
}

function openImport() {
	importFile.value = null;
	importFileList.value = [];
	importVisible.value = true;
}

function handleSelectionChange(rows: AttributeRow[]) {
	selectedRows.value = rows;
}

async function removeSelected() {
	const ids = selectedRows.value.map((r) => r.id).filter(Boolean) as string[];
	if (ids.length === 0) {
		ElMessage.warning("请先勾选要删除的记录");
		return;
	}
	try {
		await ElMessageBox.confirm(`确认删除选中的 ${ids.length} 条企业属性？`, "提示", { type: "warning" });
	} catch {
		return;
	}
	try {
		await removeCompanyAttributes(ids);
		ElMessage.success("批量删除成功");
		loadData();
	} catch (err: any) {
		ElMessage.error(errText(err, "批量删除失败"));
	}
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
		await uploadCompanyAttributes(importFile.value);
		ElMessage.success("导入成功");
		importVisible.value = false;
		loadData();
	} catch (err: any) {
		ElMessage.error(errText(err, "导入失败"));
	} finally {
		importSaving.value = false;
	}
}

onMounted(() => loadData());
</script>

<template>
	<section class="company-attribute-root">
		<h2>企业属性</h2>
		<div class="toolbar">
			<el-input
				v-model="keyword.code"
				placeholder="属性编码"
				clearable
				style="width: 160px"
				@keyup.enter="handleSearch"
			/>
			<el-input
				v-model="keyword.name"
				placeholder="属性名称"
				clearable
				style="width: 160px"
				@keyup.enter="handleSearch"
			/>
			<el-button type="primary" @click="handleSearch">查询</el-button>
			<el-button type="success" @click="openAdd">录入</el-button>
			<el-button @click="exportData">导出</el-button>
			<el-button @click="openImport">导入</el-button>
			<el-button type="danger" plain :disabled="selectedRows.length === 0" @click="removeSelected">批量删除</el-button>
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
			<el-table-column prop="com_type_code" label="属性编码" min-width="160" show-overflow-tooltip />
			<el-table-column prop="com_type_name" label="属性名称" min-width="180" show-overflow-tooltip />
			<el-table-column label="操作" width="140" fixed="right">
				<template #default="{ row }">
					<el-button link type="primary" @click="openEdit(row)">修改</el-button>
					<el-button link type="danger" @click="removeRow(row)">删除</el-button>
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

		<el-dialog
			v-model="dialogVisible"
			:title="dialogMode === 'add' ? '录入企业属性' : '修改企业属性'"
			width="460px"
			:close-on-click-modal="false"
			destroy-on-close
		>
			<el-form ref="formRef" :model="form" label-width="100px">
				<el-form-item
					label="属性编码"
					prop="com_type_code"
					:rules="[{ required: true, message: '请输入属性编码', trigger: 'blur' }]"
				>
					<el-input v-model="form.com_type_code" placeholder="如 CUSTOMER" />
				</el-form-item>
				<el-form-item
					label="属性名称"
					prop="com_type_name"
					:rules="[{ required: true, message: '请输入属性名称', trigger: 'blur' }]"
				>
					<el-input v-model="form.com_type_name" placeholder="如 客户" />
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="dialogVisible = false">取消</el-button>
				<el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
			</template>
		</el-dialog>

		<el-dialog v-model="importVisible" title="导入企业属性" width="460px" :close-on-click-modal="false">
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
				<template #tip><div class="el-upload__tip">请按导出模板格式导入（前 2 行为表头）</div></template>
			</el-upload>
			<template #footer>
				<el-button @click="importVisible = false">取消</el-button>
				<el-button type="primary" :loading="importSaving" @click="submitImport">开始导入</el-button>
			</template>
		</el-dialog>
	</section>
</template>

<style lang="scss" scoped>
.company-attribute-root {
	width: 100%;
	.toolbar {
		display: flex;
		gap: 8px;
		margin: 12px 0;
	}
	.pagination-bar {
		display: flex;
		justify-content: flex-end;
		margin-top: 12px;
	}
}
</style>
