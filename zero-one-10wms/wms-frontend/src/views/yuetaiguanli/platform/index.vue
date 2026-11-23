<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import {
	listPlatform,
	addPlatform,
	updatePlatform,
	deletePlatform,
	batchDeletePlatform,
	exportPlatform,
	importPlatform,
} from "@/apis/yuetaiguanli/index";

definePage({
	meta: {
		menuType: "page",
		text: "月台定义",
		icon: "IconSetting",
	},
});

interface PlatRow {
	id: string;
	platform_code: string;
	platform_name: string;
	create_name?: string;
	create_date?: string;
}

const loading = ref(false);
const rows = ref<PlatRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const selectedRows = ref<PlatRow[]>([]);
const tableRef = ref();

const query = ref({ platform_code: "", platform_name: "" });

// 新增/编辑弹窗
const dialogVisible = ref(false);
const isEdit = ref(false);
const form = ref({ id: "", platform_code: "", platform_name: "" });

// 导入
const importInputRef = ref<HTMLInputElement>();

function loadData() {
	loading.value = true;
	listPlatform(
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
			ElMessage.error("月台列表加载失败");
		},
	);
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	query.value = { platform_code: "", platform_name: "" };
	pageIndex.value = 1;
	loadData();
}

function handleSelectionChange(selection: PlatRow[]) {
	selectedRows.value = selection;
}

function openAdd() {
	isEdit.value = false;
	form.value = { id: "", platform_code: "", platform_name: "" };
	dialogVisible.value = true;
}

function openEdit(row: PlatRow) {
	isEdit.value = true;
	form.value = {
		id: row.id,
		platform_code: row.platform_code,
		platform_name: row.platform_name,
	};
	dialogVisible.value = true;
}

function handleSave() {
	if (!form.value.platform_code.trim() || !form.value.platform_name.trim()) {
		ElMessage.warning("月台代码与名称不能为空");
		return;
	}
	loading.value = true;
	const finish = (ok: boolean, dup?: boolean) => {
		loading.value = false;
		if (ok) {
			ElMessage.success(isEdit.value ? "修改成功" : "录入成功");
			dialogVisible.value = false;
			loadData();
		} else if (dup) {
			ElMessage.warning("月台代码已存在");
		} else {
			ElMessage.error(isEdit.value ? "修改失败" : "录入失败");
		}
	};
	if (isEdit.value) {
		updatePlatform(
			{ ...form.value },
			() => finish(true),
			() => finish(false),
		);
	} else {
		addPlatform(
			{ platform_code: form.value.platform_code, platform_name: form.value.platform_name },
			() => finish(true),
			() => finish(false),
		);
	}
}

function handleDelete(row: PlatRow) {
	loading.value = true;
	deletePlatform(
		row.id,
		() => {
			loading.value = false;
			ElMessage.success("删除成功");
			loadData();
		},
		() => {
			loading.value = false;
			ElMessage.error("删除失败");
		},
	);
}

function handleBatchDelete() {
	if (selectedRows.value.length === 0) {
		ElMessage.warning("请先勾选要删除的月台");
		return;
	}
	const ids = selectedRows.value.map((r) => r.id);
	loading.value = true;
	batchDeletePlatform(
		ids,
		() => {
			loading.value = false;
			ElMessage.success("批量删除成功");
			tableRef.value?.clearSelection();
			loadData();
		},
		() => {
			loading.value = false;
			ElMessage.error("批量删除失败");
		},
	);
}

function handleExport() {
	loading.value = true;
	exportPlatform(
		(data: any) => {
			loading.value = false;
			if (typeof data === "string" && data) {
				window.open(data, "_blank");
				ElMessage.success("导出成功，已打开下载地址");
			} else {
				ElMessage.warning("导出结果为空");
			}
		},
		() => {
			loading.value = false;
			ElMessage.error("导出失败");
		},
	);
}

function triggerImport() {
	importInputRef.value?.click();
}

function handleImportFile(event: Event) {
	const target = event.target as HTMLInputElement;
	const file = target.files?.[0];
	if (!file) return;
	loading.value = true;
	importPlatform(
		file,
		() => {
			loading.value = false;
			ElMessage.success("导入成功");
			loadData();
		},
		() => {
			loading.value = false;
			ElMessage.error("导入失败，请检查文件格式（xlsx，表头：月台代码,月台名称）");
		},
	);
	target.value = "";
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
	<section>
		<el-card shadow="never">
			<el-form :model="query" inline>
				<el-form-item label="月台代码">
					<el-input v-model="query.platform_code" clearable placeholder="月台代码" style="width: 160px" />
				</el-form-item>
				<el-form-item label="月台名称">
					<el-input v-model="query.platform_name" clearable placeholder="月台名称（模糊）" style="width: 160px" />
				</el-form-item>
				<el-form-item>
					<el-button type="primary" @click="handleSearch">查询</el-button>
					<el-button @click="handleReset">重置</el-button>
				</el-form-item>
			</el-form>
		</el-card>

		<el-card shadow="never" style="margin-top: 12px">
			<div style="margin-bottom: 12px; display: flex; gap: 8px">
				<el-button type="primary" @click="openAdd">录入月台</el-button>
				<el-button type="danger" :disabled="selectedRows.length === 0" @click="handleBatchDelete">
					批量删除（{{ selectedRows.length }}）
				</el-button>
				<el-button @click="handleExport">导出</el-button>
				<el-button @click="triggerImport">导入</el-button>
				<input ref="importInputRef" type="file" accept=".xlsx" style="display: none" @change="handleImportFile" />
			</div>

			<el-table
				ref="tableRef"
				v-loading="loading"
				:data="rows"
				border
				stripe
				style="width: 100%"
				@selection-change="handleSelectionChange"
			>
				<el-table-column type="selection" width="50" />
				<el-table-column type="index" label="序号" width="60" />
				<el-table-column prop="platform_code" label="月台代码" width="160" />
				<el-table-column prop="platform_name" label="月台名称" min-width="160" />
				<el-table-column prop="create_name" label="创建人" width="120" />
				<el-table-column prop="create_date" label="创建时间" width="180" />
				<el-table-column label="操作" width="160" fixed="right">
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
				:total="total"
				:page-sizes="[10, 20, 50]"
				layout="total, sizes, prev, pager, next, jumper"
				@current-change="handlePageChange"
				@size-change="handleSizeChange"
			/>
		</el-card>

		<el-dialog v-model="dialogVisible" :title="isEdit ? '修改月台' : '录入月台'" width="420px">
			<el-form :model="form" label-width="90px">
				<el-form-item label="月台代码" required>
					<el-input v-model="form.platform_code" :disabled="isEdit" placeholder="如 P001" />
				</el-form-item>
				<el-form-item label="月台名称" required>
					<el-input v-model="form.platform_name" placeholder="如 1号装卸月台" />
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="dialogVisible = false">取消</el-button>
				<el-button type="primary" :loading="loading" @click="handleSave">保存</el-button>
			</template>
		</el-dialog>
	</section>
</template>
