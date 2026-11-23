<script lang="ts" setup>
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
	listEmploymentStatuses,
	addEmploymentStatus,
	modifyEmploymentStatus,
	removeEmploymentStatuses,
	importEmploymentStatuses,
	exportEmploymentStatuses,
	employmentStatusFileName,
	saveBlob,
} from "@/apis/reference/index";

definePage({
	meta: {
		menuType: "page",
		text: "在职状态",
		icon: "IconSetting",
	},
});

interface Row {
	id?: string;
	pos_sta_code?: string;
	pos_sta_name?: string;
}

const loading = ref(false);
const rows = ref<Row[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const keyword = ref({ code: "", name: "" });
const selectedRows = ref<Row[]>([]);
const fileRef = ref();

const dialogVisible = ref(false);
const dialogMode = ref<"add" | "edit">("add");
const saving = ref(false);
const formRef = ref();
const form = reactive({ id: "", pos_sta_code: "", pos_sta_name: "" });

function errText(err: any, fallback: string) {
	return err?.data?.message || err?.message || err?.response?.data?.message || fallback;
}

function loadData() {
	loading.value = true;
	listEmploymentStatuses(
		{
			pageIndex: pageIndex.value,
			pageSize: pageSize.value,
			pos_sta_code: keyword.value.code,
			pos_sta_name: keyword.value.name,
		},
		(data: any) => {
			rows.value = data?.rows ?? [];
			total.value = data?.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("在职状态数据加载失败");
		},
	);
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}
function handleReset() {
	keyword.value = { code: "", name: "" };
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
function handleSelectionChange(vals: Row[]) {
	selectedRows.value = vals;
}

function openAdd() {
	dialogMode.value = "add";
	Object.assign(form, { id: "", pos_sta_code: "", pos_sta_name: "" });
	dialogVisible.value = true;
}
function openEdit(row: Row) {
	dialogMode.value = "edit";
	Object.assign(form, {
		id: row.id ?? "",
		pos_sta_code: row.pos_sta_code ?? "",
		pos_sta_name: row.pos_sta_name ?? "",
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
			await addEmploymentStatus({ pos_sta_code: form.pos_sta_code, pos_sta_name: form.pos_sta_name });
		} else {
			await modifyEmploymentStatus({
				id: form.id,
				pos_sta_code: form.pos_sta_code,
				pos_sta_name: form.pos_sta_name,
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

async function removeRow(row: Row) {
	// 在职状态删除按业务编码 pos_sta_code，不是 id
	const code = row.pos_sta_code;
	if (!code) {
		ElMessage.warning("该记录缺少编码，无法删除");
		return;
	}
	try {
		await ElMessageBox.confirm(`确认删除在职状态「${row.pos_sta_name}」？`, "提示", { type: "warning" });
	} catch {
		return;
	}
	try {
		await removeEmploymentStatuses([code]);
		ElMessage.success("删除成功");
		loadData();
	} catch (err: any) {
		ElMessage.error(errText(err, "删除失败"));
	}
}

async function removeBatch() {
	const codes = selectedRows.value.map((r) => r.pos_sta_code).filter(Boolean);
	if (!codes.length) {
		ElMessage.warning("请先勾选要删除的记录");
		return;
	}
	try {
		await ElMessageBox.confirm(`确认删除选中的 ${codes.length} 条在职状态？`, "提示", { type: "warning" });
	} catch {
		return;
	}
	try {
		await removeEmploymentStatuses(codes);
		ElMessage.success("批量删除成功");
		loadData();
	} catch (err: any) {
		ElMessage.error(errText(err, "批量删除失败"));
	}
}

async function exportData() {
	try {
		const blob = await exportEmploymentStatuses();
		saveBlob(blob, employmentStatusFileName());
		ElMessage.success("导出成功");
	} catch (err: any) {
		ElMessage.error(errText(err, "导出失败"));
	}
}

async function handleImportChange(uploadFile: any) {
	const raw = uploadFile?.raw;
	if (!raw) return;
	try {
		await importEmploymentStatuses(raw);
		ElMessage.success("导入成功");
		loadData();
	} catch (err: any) {
		ElMessage.error(errText(err, "导入失败"));
	} finally {
		if (fileRef.value) fileRef.value.clearFiles();
	}
}

onMounted(() => loadData());
</script>

<template>
	<section class="employment-status-root">
		<div class="toolbar">
			<el-input v-model="keyword.code" placeholder="在职状态代码" clearable style="width: 160px" @keyup.enter="handleSearch" />
			<el-input v-model="keyword.name" placeholder="在职状态名称" clearable style="width: 160px" @keyup.enter="handleSearch" />
			<el-button type="primary" @click="handleSearch">查询</el-button>
			<el-button @click="handleReset">重置</el-button>
			<el-button type="success" @click="openAdd">录入</el-button>
			<el-button type="danger" plain @click="removeBatch">批量删除</el-button>
			<el-button @click="exportData">导出</el-button>
			<el-upload
				ref="fileRef"
				:show-file-list="false"
				accept=".xlsx"
				:auto-upload="false"
				:on-change="handleImportChange"
			>
				<el-button type="warning" plain>导入</el-button>
			</el-upload>
			<el-button @click="loadData">刷新</el-button>
		</div>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%" @selection-change="handleSelectionChange">
			<el-table-column type="selection" width="45" />
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="pos_sta_code" label="在职状态代码" width="180" />
			<el-table-column prop="pos_sta_name" label="在职状态名称" min-width="180" />
			<el-table-column prop="id" label="ID" min-width="200" show-overflow-tooltip />
			<el-table-column label="操作" width="140" fixed="right">
				<template #default="{ row }">
					<el-button link type="primary" @click="openEdit(row)">修改</el-button>
					<el-button link type="danger" @click="removeRow(row)">删除</el-button>
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

		<el-dialog
			v-model="dialogVisible"
			:title="dialogMode === 'add' ? '录入职状态' : '修改在职状态'"
			width="460px"
			:close-on-click-modal="false"
			destroy-on-close
		>
			<el-form ref="formRef" :model="form" label-width="100px">
				<el-form-item label="状态代码" prop="pos_sta_code" :rules="[{ required: true, message: '请输入在职状态代码', trigger: 'blur' }]">
					<el-input v-model="form.pos_sta_code" placeholder="如 PROBATION" />
				</el-form-item>
				<el-form-item label="状态名称" prop="pos_sta_name" :rules="[{ required: true, message: '请输入在职状态名称', trigger: 'blur' }]">
					<el-input v-model="form.pos_sta_name" placeholder="如 试用期" />
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="dialogVisible = false">取消</el-button>
				<el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
			</template>
		</el-dialog>
	</section>
</template>

<style lang="scss" scoped>
.employment-status-root {
	width: 100%;

	.toolbar {
		display: flex;
		align-items: center;
		gap: 8px;
		margin: 12px 0;
		flex-wrap: wrap;
	}
}
</style>
