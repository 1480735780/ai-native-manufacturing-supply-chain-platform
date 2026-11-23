<script lang="ts" setup>
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { UploadFile, UploadFiles } from "element-plus";
import {
	listCompanies,
	getCompanyDetail,
	addCompany,
	modifyCompany,
	removeCompany,
	downloadCompanies,
	uploadCompanies,
	saveBlob,
} from "@/apis/enterprise-config/index";

definePage({
	meta: {
		menuType: "page",
		text: "公司信息",
		icon: "OfficeBuilding",
	},
});

interface CompanyRow {
	id?: string;
	code?: string;
	ChineseSampleName?: string;
	ChineseFullName?: string;
	ChineseAddr?: string;
	EnglishSampleName?: string;
	EnglishFullName?: string;
}

const loading = ref(false);
const rows = ref<CompanyRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const keyword = ref({
	code: "",
	ChineseSampleName: "",
	ChineseFullName: "",
	ChineseAddr: "",
	EnglishSampleName: "",
	EnglishFullName: "",
});

const dialogVisible = ref(false);
const dialogMode = ref<"add" | "edit">("add");
const saving = ref(false);
const formRef = ref();
const form = reactive({
	id: "",
	companyId: "",
	zhabbr: "",
	zhful: "",
	zhaddr: "",
	enabbr: "",
	enful: "",
});

const detailVisible = ref(false);
const detailLoading = ref(false);
const detailData = ref<CompanyRow | null>(null);

const importVisible = ref(false);
const importSaving = ref(false);
const importFile = ref<File | null>(null);
const importFileList = ref<UploadFiles>([]);

const selectedRows = ref<CompanyRow[]>([]);

function errText(err: any, fallback: string) {
	return err?.data?.message || err?.message || err?.response?.data?.message || fallback;
}

function loadData() {
	loading.value = true;
	listCompanies(
		{
			pageIndex: pageIndex.value,
			pageSize: pageSize.value,
			...keyword.value,
		},
		(data: any) => {
			rows.value = data?.rows ?? [];
			total.value = data?.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("公司信息加载失败");
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
	Object.assign(form, { id: "", companyId: "", zhabbr: "", zhful: "", zhaddr: "", enabbr: "", enful: "" });
	dialogVisible.value = true;
}
async function openEdit(row: CompanyRow) {
	dialogMode.value = "edit";
	Object.assign(form, {
		id: row.id ?? "",
		companyId: row.code ?? "",
		zhabbr: row.ChineseSampleName ?? "",
		zhful: row.ChineseFullName ?? "",
		zhaddr: row.ChineseAddr ?? "",
		enabbr: row.EnglishSampleName ?? "",
		enful: row.EnglishFullName ?? "",
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
			await addCompany({
				companyId: form.companyId,
				zhabbr: form.zhabbr,
				zhful: form.zhful,
				zhaddr: form.zhaddr,
				enabbr: form.enabbr,
				enful: form.enful,
			});
		} else {
			await modifyCompany({
				id: form.id,
				companyId: form.companyId,
				zhabbr: form.zhabbr,
				zhful: form.zhful,
				zhaddr: form.zhaddr,
				enabbr: form.enabbr,
				enful: form.enful,
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

async function openDetail(row: CompanyRow) {
	if (!row.id) {
		ElMessage.warning("该记录缺少主键，无法查看详细信息");
		return;
	}
	detailVisible.value = true;
	detailLoading.value = true;
	detailData.value = null;
	try {
		detailData.value = await getCompanyDetail(row.id);
	} catch (err: any) {
		ElMessage.error(errText(err, "详细信息加载失败"));
		detailVisible.value = false;
	} finally {
		detailLoading.value = false;
	}
}

async function removeRow(row: CompanyRow) {
	if (!row.id) {
		ElMessage.warning("该记录缺少主键，无法删除");
		return;
	}
	try {
		await ElMessageBox.confirm(`确认删除公司「${row.ChineseFullName}」？`, "提示", { type: "warning" });
	} catch {
		return;
	}
	try {
		await removeCompany(row.id, [row.id]);
		ElMessage.success("删除成功");
		loadData();
	} catch (err: any) {
		ElMessage.error(errText(err, "删除失败"));
	}
}

async function exportData() {
	try {
		const blob = await downloadCompanies(`公司信息_${Date.now()}.xlsx`);
		saveBlob(blob, `公司信息_${Date.now()}.xlsx`);
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

function handleSelectionChange(rows: CompanyRow[]) {
	selectedRows.value = rows;
}

async function removeSelected() {
	const ids = selectedRows.value.map((r) => r.id).filter(Boolean) as string[];
	if (ids.length === 0) {
		ElMessage.warning("请先勾选要删除的记录");
		return;
	}
	try {
		await ElMessageBox.confirm(`确认删除选中的 ${ids.length} 条公司信息？`, "提示", { type: "warning" });
	} catch {
		return;
	}
	try {
		await removeCompany(ids[0], ids);
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
		await uploadCompanies(importFile.value);
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
	<section class="company-info-root">
		<h2>公司信息</h2>
		<div class="toolbar">
			<el-input
				v-model="keyword.code"
				placeholder="企业编码"
				clearable
				style="width: 140px"
				@keyup.enter="handleSearch"
			/>
			<el-input
				v-model="keyword.ChineseSampleName"
				placeholder="中文简称"
				clearable
				style="width: 140px"
				@keyup.enter="handleSearch"
			/>
			<el-input
				v-model="keyword.ChineseFullName"
				placeholder="中文全称"
				clearable
				style="width: 140px"
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
			<el-table-column prop="code" label="企业编码" min-width="120" show-overflow-tooltip />
			<el-table-column prop="ChineseSampleName" label="中文简称" min-width="140" show-overflow-tooltip />
			<el-table-column prop="ChineseFullName" label="中文全称" min-width="180" show-overflow-tooltip />
			<el-table-column prop="ChineseAddr" label="中文地址" min-width="180" show-overflow-tooltip />
			<el-table-column prop="EnglishSampleName" label="英文简称" min-width="140" show-overflow-tooltip />
			<el-table-column prop="EnglishFullName" label="英文全称" min-width="180" show-overflow-tooltip />
			<el-table-column label="操作" width="200" fixed="right">
				<template #default="{ row }">
					<el-button link type="primary" @click="openDetail(row)">详情</el-button>
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
			:title="dialogMode === 'add' ? '录入公司信息' : '修改公司信息'"
			width="560px"
			:close-on-click-modal="false"
			destroy-on-close
		>
			<el-form ref="formRef" :model="form" label-width="100px">
				<el-form-item
					label="企业编码"
					prop="companyId"
					:rules="[{ required: true, message: '请输入企业编码', trigger: 'blur' }]"
				>
					<el-input v-model="form.companyId" placeholder="如 COM001" />
				</el-form-item>
				<el-form-item
					label="中文简称"
					prop="zhabbr"
					:rules="[{ required: true, message: '请输入中文简称', trigger: 'blur' }]"
				>
					<el-input v-model="form.zhabbr" />
				</el-form-item>
				<el-form-item
					label="中文全称"
					prop="zhful"
					:rules="[{ required: true, message: '请输入中文全称', trigger: 'blur' }]"
				>
					<el-input v-model="form.zhful" />
				</el-form-item>
				<el-form-item label="中文地址">
					<el-input v-model="form.zhaddr" />
				</el-form-item>
				<el-form-item label="英文简称">
					<el-input v-model="form.enabbr" />
				</el-form-item>
				<el-form-item label="英文全称">
					<el-input v-model="form.enful" />
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="dialogVisible = false">取消</el-button>
				<el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
			</template>
		</el-dialog>

		<el-dialog v-model="detailVisible" title="公司详细信息" width="560px">
			<div v-loading="detailLoading">
				<el-descriptions v-if="detailData" :column="1" border>
					<el-descriptions-item label="企业编码">{{ detailData.code || "-" }}</el-descriptions-item>
					<el-descriptions-item label="中文简称">{{ detailData.ChineseSampleName || "-" }}</el-descriptions-item>
					<el-descriptions-item label="中文全称">{{ detailData.ChineseFullName || "-" }}</el-descriptions-item>
					<el-descriptions-item label="中文地址">{{ detailData.ChineseAddr || "-" }}</el-descriptions-item>
					<el-descriptions-item label="英文简称">{{ detailData.EnglishSampleName || "-" }}</el-descriptions-item>
					<el-descriptions-item label="英文全称">{{ detailData.EnglishFullName || "-" }}</el-descriptions-item>
				</el-descriptions>
			</div>
			<template #footer>
				<el-button @click="detailVisible = false">关闭</el-button>
			</template>
		</el-dialog>

		<el-dialog v-model="importVisible" title="导入公司信息" width="460px" :close-on-click-modal="false">
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
.company-info-root {
	width: 100%;
	.toolbar {
		display: flex;
		gap: 8px;
		flex-wrap: wrap;
		margin: 12px 0;
	}
	.pagination-bar {
		display: flex;
		justify-content: flex-end;
		margin-top: 12px;
	}
}
</style>
