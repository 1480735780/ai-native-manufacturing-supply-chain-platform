<script lang="ts" setup>
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { UploadFile, UploadFiles } from "element-plus";
import {
	listCompanyStatuses,
	addCompanyStatus,
	modifyCompanyStatus,
	removeCompanyStatus,
	downloadCompanyStatuses,
	uploadCompanyStatuses,
	saveBlob,
} from "@/apis/enterprise-config/index";

definePage({
	meta: {
		menuType: "page",
		text: "企业状态",
		icon: "Odometer",
	},
});

interface StatusRow {
	id?: string;
	enterpriseid?: string;
	enterprisename?: string;
	status?: string;
}

const loading = ref(false);
const rows = ref<StatusRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const keyword = ref({ code: "", name: "" });

const dialogVisible = ref(false);
const dialogMode = ref<"add" | "edit">("add");
const saving = ref(false);
const formRef = ref();
const form = reactive({ id: "", clientid: "", clientname: "", state: "0" });

const importVisible = ref(false);
const importSaving = ref(false);
const importFile = ref<File | null>(null);
const importFileList = ref<UploadFiles>([]);

const selectedRows = ref<StatusRow[]>([]);

function errText(err: any, fallback: string) {
	return err?.data?.message || err?.message || err?.response?.data?.message || fallback;
}

function loadData() {
	loading.value = true;
	listCompanyStatuses(
		{
			pageIndex: pageIndex.value,
			pageSize: pageSize.value,
			enterpriseid: keyword.value.code,
			enterprisename: keyword.value.name,
		},
		(data: any) => {
			rows.value = data?.rows ?? [];
			total.value = data?.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("企业状态加载失败");
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
	Object.assign(form, { id: "", clientid: "", clientname: "", state: "0" });
	dialogVisible.value = true;
}
function openEdit(row: StatusRow) {
	dialogMode.value = "edit";
	Object.assign(form, {
		// 修改接口按主键 id 定位记录，不能用业务编码 enterpriseid 充当 id
		id: row.id ?? "",
		clientid: row.enterpriseid ?? "",
		clientname: row.enterprisename ?? "",
		state: String(row.status ?? "0"),
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
			await addCompanyStatus({ clientid: form.clientid, clientname: form.clientname, state: form.state });
		} else {
			await modifyCompanyStatus({
				id: form.id,
				clientid: form.clientid,
				clientname: form.clientname,
				state: form.state,
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

async function removeRow(row: StatusRow) {
	// 删除按主键 id 定位，业务编码不能替代
	const id = row.id;
	if (!id) {
		ElMessage.warning("该记录缺少主键，无法删除");
		return;
	}
	try {
		await ElMessageBox.confirm(`确认删除企业状态「${row.enterprisename}」？`, "提示", { type: "warning" });
	} catch {
		return;
	}
	try {
		await removeCompanyStatus(id, [id]);
		ElMessage.success("删除成功");
		loadData();
	} catch (err: any) {
		ElMessage.error(errText(err, "删除失败"));
	}
}

function handleSelectionChange(rows: StatusRow[]) {
	selectedRows.value = rows;
}

async function removeSelected() {
	const ids = selectedRows.value.map((r) => r.id).filter(Boolean) as string[];
	if (ids.length === 0) {
		ElMessage.warning("请先勾选要删除的记录");
		return;
	}
	try {
		await ElMessageBox.confirm(`确认删除选中的 ${ids.length} 条企业状态？`, "提示", { type: "warning" });
	} catch {
		return;
	}
	try {
		await removeCompanyStatus(ids[0], ids);
		ElMessage.success("批量删除成功");
		loadData();
	} catch (err: any) {
		ElMessage.error(errText(err, "批量删除失败"));
	}
}

async function exportData() {
	try {
		const blob = await downloadCompanyStatuses(`企业状态_${Date.now()}.xlsx`);
		saveBlob(blob, `企业状态_${Date.now()}.xlsx`);
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
		await uploadCompanyStatuses(importFile.value);
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
	<section class="company-status-root">
		<h2>企业状态</h2>
		<div class="toolbar">
			<el-input
				v-model="keyword.code"
				placeholder="状态编码"
				clearable
				style="width: 160px"
				@keyup.enter="handleSearch"
			/>
			<el-input
				v-model="keyword.name"
				placeholder="状态名称"
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
			<el-table-column prop="enterpriseid" label="状态编码" min-width="160" show-overflow-tooltip />
			<el-table-column prop="enterprisename" label="状态名称" min-width="180" show-overflow-tooltip />
			<el-table-column label="停用" width="90">
				<template #default="{ row }">{{ String(row.status) === "1" ? "是" : "否" }}</template>
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
			:title="dialogMode === 'add' ? '录入企业状态' : '修改企业状态'"
			width="460px"
			:close-on-click-modal="false"
			destroy-on-close
		>
			<el-form ref="formRef" :model="form" label-width="100px">
				<el-form-item
					label="状态编码"
					prop="clientid"
					:rules="[{ required: true, message: '请输入状态编码', trigger: 'blur' }]"
				>
					<el-input v-model="form.clientid" placeholder="如 ENABLED" />
				</el-form-item>
				<el-form-item
					label="状态名称"
					prop="clientname"
					:rules="[{ required: true, message: '请输入状态名称', trigger: 'blur' }]"
				>
					<el-input v-model="form.clientname" placeholder="如 启用" />
				</el-form-item>
				<el-form-item label="是否停用">
					<el-select v-model="form.state" style="width: 100%">
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

		<el-dialog v-model="importVisible" title="导入企业状态" width="460px" :close-on-click-modal="false">
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
.company-status-root {
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
