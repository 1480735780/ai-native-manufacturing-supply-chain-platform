<script lang="ts" setup>
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
	listEduCodes,
	addEduCode,
	modifyEduCode,
	removeEduCode,
	removeEduCodesBatch,
	importEduCodes,
	exportEduCodes,
	eduCodeFileName,
	saveBlob,
} from "@/apis/reference/index";

definePage({
	meta: {
		menuType: "page",
		text: "学历代码",
		icon: "IconSetting",
	},
});

interface Row {
	id?: string;
	educode?: string;
	eduname?: string;
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
const form = reactive({ id: "", educode: "", eduname: "" });

function errText(err: any, fallback: string) {
	return err?.data?.message || err?.message || err?.response?.data?.message || fallback;
}

function loadData() {
	loading.value = true;
	listEduCodes(
		{
			pageIndex: pageIndex.value,
			pageSize: pageSize.value,
			educode: keyword.value.code,
			eduname: keyword.value.name,
		},
		(data: any) => {
			rows.value = data?.rows ?? [];
			total.value = data?.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("学历代码数据加载失败");
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
	Object.assign(form, { id: "", educode: "", eduname: "" });
	dialogVisible.value = true;
}
function openEdit(row: Row) {
	dialogMode.value = "edit";
	Object.assign(form, {
		id: row.id ?? "",
		educode: row.educode ?? "",
		eduname: row.eduname ?? "",
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
			await addEduCode({ educode: form.educode, eduname: form.eduname });
		} else {
			// 修改接口 body 字段是 code/name，不是 educode/eduname
			await modifyEduCode({ id: form.id, code: form.educode, name: form.eduname });
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
	const id = row.id;
	if (!id) {
		ElMessage.warning("该记录缺少主键，无法删除");
		return;
	}
	try {
		await ElMessageBox.confirm(`确认删除学历代码「${row.eduname}」？`, "提示", { type: "warning" });
	} catch {
		return;
	}
	try {
		await removeEduCode(id);
		ElMessage.success("删除成功");
		loadData();
	} catch (err: any) {
		ElMessage.error(errText(err, "删除失败"));
	}
}

async function removeBatch() {
	const ids = selectedRows.value.map((r) => r.id).filter(Boolean);
	if (!ids.length) {
		ElMessage.warning("请先勾选要删除的记录");
		return;
	}
	try {
		await ElMessageBox.confirm(`确认删除选中的 ${ids.length} 条学历代码？`, "提示", { type: "warning" });
	} catch {
		return;
	}
	try {
		await removeEduCodesBatch(ids);
		ElMessage.success("批量删除成功");
		loadData();
	} catch (err: any) {
		ElMessage.error(errText(err, "批量删除失败"));
	}
}

async function exportData() {
	try {
		const blob = await exportEduCodes();
		saveBlob(blob, eduCodeFileName());
		ElMessage.success("导出成功");
	} catch (err: any) {
		ElMessage.error(errText(err, "导出失败"));
	}
}

async function handleImportChange(uploadFile: any) {
	const raw = uploadFile?.raw;
	if (!raw) return;
	try {
		const msg = await importEduCodes(raw);
		ElMessage.success(typeof msg === "string" ? `导入成功：${msg}` : "导入成功");
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
	<section class="academic-code-root">
		<div class="toolbar">
			<el-input v-model="keyword.code" placeholder="学历代码" clearable style="width: 160px" @keyup.enter="handleSearch" />
			<el-input v-model="keyword.name" placeholder="学历名称" clearable style="width: 160px" @keyup.enter="handleSearch" />
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
			<el-table-column prop="educode" label="学历代码" width="180" />
			<el-table-column prop="eduname" label="学历名称" min-width="180" />
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
			:title="dialogMode === 'add' ? '录入学历代码' : '修改学历代码'"
			width="460px"
			:close-on-click-modal="false"
			destroy-on-close
		>
			<el-form ref="formRef" :model="form" label-width="100px">
				<el-form-item label="学历代码" prop="educode" :rules="[{ required: true, message: '请输入学历代码', trigger: 'blur' }]">
					<el-input v-model="form.educode" placeholder="如 EDU01" />
				</el-form-item>
				<el-form-item label="学历名称" prop="eduname" :rules="[{ required: true, message: '请输入学历名称', trigger: 'blur' }]">
					<el-input v-model="form.eduname" placeholder="如 本科" />
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
.academic-code-root {
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
