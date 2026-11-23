<script lang="ts" setup>
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { UploadFile, UploadFiles } from "element-plus";
import {
	listCompanyLevels,
	addCompanyLevel,
	modifyCompanyLevel,
	removeCompanyLevels,
	downloadCompanyLevels,
	uploadCompanyLevels,
	saveBlob,
} from "@/apis/enterprise-config/index";

definePage({
	meta: {
		menuType: "page",
		text: "企业等级",
		icon: "Trophy",
	},
});

interface LevelRow {
	id?: string;
	degcode?: string;
	degname?: string;
	degdel?: string | number;
}

const loading = ref(false);
const rows = ref<LevelRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const keyword = ref({ degname: "", degcode: "" });

const dialogVisible = ref(false);
const dialogMode = ref<"add" | "edit">("add");
const saving = ref(false);
const formRef = ref();
const form = reactive({
	id: "",
	degcode: "",
	degname: "",
	degdel: "0",
	cname: "",
	cdd: "0",
});

const importVisible = ref(false);
const importSaving = ref(false);
const importFile = ref<File | null>(null);
const importFileList = ref<UploadFiles>([]);

const selectedRows = ref<LevelRow[]>([]);

function errText(err: any, fallback: string) {
	return err?.data?.message || err?.message || err?.response?.data?.message || fallback;
}

function loadData() {
	loading.value = true;
	listCompanyLevels(
		{
			pageIndex: pageIndex.value,
			pageSize: pageSize.value,
			degname: keyword.value.degname,
			degcode: keyword.value.degcode,
		},
		(data: any) => {
			rows.value = data?.rows ?? [];
			total.value = data?.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("企业等级加载失败");
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
	Object.assign(form, { id: "", degcode: "", degname: "", degdel: "0", cname: "", cdd: "0" });
	dialogVisible.value = true;
}
function openEdit(row: LevelRow) {
	dialogMode.value = "edit";
	Object.assign(form, {
		id: row.id ?? "",
		degcode: row.degcode ?? "",
		degname: row.degname ?? "",
		degdel: String(row.degdel ?? "0"),
		cname: row.degname ?? "",
		cdd: String(row.degdel ?? "0"),
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
			await addCompanyLevel({
				degname: form.degname,
				degcode: form.degcode,
				degdel: form.degdel,
			});
		} else {
			// 修改接口底层 ba_com_deg 使用 CdmDTO 字段：cname=等级名称，cdn=等级编码，cdd=停用标记
			await modifyCompanyLevel({
				id: form.id,
				cname: form.degname,
				cdn: form.degcode,
				cdd: form.cdd,
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

async function removeRow(row: LevelRow) {
	if (!row.id) {
		ElMessage.warning("该记录缺少主键，无法删除");
		return;
	}
	try {
		await ElMessageBox.confirm(`确认删除企业等级「${row.degname}」？`, "提示", { type: "warning" });
	} catch {
		return;
	}
	try {
		await removeCompanyLevels([row.id]);
		ElMessage.success("删除成功");
		loadData();
	} catch (err: any) {
		ElMessage.error(errText(err, "删除失败"));
	}
}

async function exportData() {
	try {
		const blob = await downloadCompanyLevels();
		saveBlob(blob, `企业等级_${Date.now()}.xlsx`);
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

function handleSelectionChange(rows: LevelRow[]) {
	selectedRows.value = rows;
}

async function removeSelected() {
	const ids = selectedRows.value.map((r) => r.id).filter(Boolean) as string[];
	if (ids.length === 0) {
		ElMessage.warning("请先勾选要删除的记录");
		return;
	}
	try {
		await ElMessageBox.confirm(`确认删除选中的 ${ids.length} 条企业等级？`, "提示", { type: "warning" });
	} catch {
		return;
	}
	try {
		await removeCompanyLevels(ids);
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
		await uploadCompanyLevels(importFile.value);
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
	<section class="company-level-root">
		<h2>企业等级</h2>
		<div class="toolbar">
			<el-input
				v-model="keyword.degname"
				placeholder="等级名称"
				clearable
				style="width: 160px"
				@keyup.enter="handleSearch"
			/>
			<el-input
				v-model="keyword.degcode"
				placeholder="等级编码"
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
			<el-table-column prop="degcode" label="等级编码" min-width="160" show-overflow-tooltip />
			<el-table-column prop="degname" label="等级名称" min-width="180" show-overflow-tooltip />
			<el-table-column label="停用" width="90">
				<template #default="{ row }">{{ String(row.degdel) === "1" ? "是" : "否" }}</template>
			</el-table-column>
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
			:title="dialogMode === 'add' ? '录入企业等级' : '修改企业等级'"
			width="460px"
			:close-on-click-modal="false"
			destroy-on-close
		>
			<el-form ref="formRef" :model="form" label-width="100px">
				<el-form-item
					label="等级编码"
					prop="degcode"
					:rules="[{ required: true, message: '请输入等级编码', trigger: 'blur' }]"
				>
					<el-input v-model="form.degcode" placeholder="如 A" />
				</el-form-item>
				<el-form-item
					label="等级名称"
					prop="degname"
					:rules="[{ required: true, message: '请输入等级名称', trigger: 'blur' }]"
				>
					<el-input v-model="form.degname" placeholder="如 优" />
				</el-form-item>
				<el-form-item label="是否停用">
					<el-select v-model="form.degdel" style="width: 100%">
						<el-option label="否" value="0" />
						<el-option label="是" value="1" />
					</el-select>
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="dialogVisible = false">取消</el-button>
				<el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
			</template>
		</el-dialog>

		<el-dialog v-model="importVisible" title="导入企业等级" width="460px" :close-on-click-modal="false">
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
.company-level-root {
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
