<script lang="ts" setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { pickPage } from "@/apis/billing/index";

interface Column {
	prop: string;
	label: string;
	width?: number | string;
	minWidth?: number | string;
	type?: "text" | "number" | "select" | "date";
	options?: { label: string; value: string }[];
	readonly?: boolean;
	placeholder?: string;
}

interface Props {
	title: string;
	tip?: string;
	/** 由 createDictApi 生成的接口集合 */
	api: {
		page: (params: any) => Promise<any>;
		add?: (data: any) => Promise<any>;
		modify?: (data: any) => Promise<any>;
		remove?: (ids: string[]) => Promise<any>;
		exportExcel?: (filename?: string) => Promise<void>;
		importExcel?: (file: File) => Promise<any>;
		/** 详情查询，返回单行对象或单元素数组 */
		detail?: (id: string) => Promise<any>;
	};
	/** 表格列 */
	columns: Column[];
	/** 可搜索字段（默认取前两列） */
	searchFields?: string[];
	/** 导出文件名 */
	filename?: string;
	/** 主键字段名 */
	idKey?: string;
}

const props = withDefaults(defineProps<Props>(), {
	tip: "",
	searchFields: () => [],
	filename: "",
	idKey: "id",
});

const loading = ref(false);
const rows = ref<any[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const selected = ref<any[]>([]);
const keyword = reactive<Record<string, string>>({});

const dialogVisible = ref(false);
const dialogMode = ref<"add" | "edit">("add");
const submitting = ref(false);
const formData = reactive<Record<string, any>>({});

const searchColumns = computed(() => {
	const fields = props.searchFields.length ? props.searchFields : props.columns.slice(0, 2).map((c) => c.prop);
	return props.columns.filter((c) => fields.includes(c.prop));
});

const formColumns = computed(() => props.columns.filter((c) => !["create_name", "create_date", "update_name", "update_date", "sys_org_code", "sys_company_code"].includes(c.prop)));

/** 查询列表 */
async function loadData() {
	loading.value = true;
	try {
		const params: Record<string, any> = { pageIndex: pageIndex.value, pageSize: pageSize.value };
		Object.entries(keyword).forEach(([k, v]) => {
			if (v !== "" && v !== null && v !== undefined) params[k] = v;
		});
		const payload = await props.api.page(params);
		const page = pickPage(payload);
		rows.value = page.rows;
		total.value = page.total;
	} catch (err) {
		console.warn(err);
		ElMessage.error(`${props.title}数据加载失败`);
		rows.value = [];
		total.value = 0;
	} finally {
		loading.value = false;
	}
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	Object.keys(keyword).forEach((k) => (keyword[k] = ""));
	pageIndex.value = 1;
	loadData();
}

function handleSelectionChange(val: any[]) {
	selected.value = val;
}

function resetForm() {
	Object.keys(formData).forEach((k) => delete formData[k]);
	props.columns.forEach((c) => (formData[c.prop] = ""));
}

function openAdd() {
	dialogMode.value = "add";
	resetForm();
	dialogVisible.value = true;
}

function openEdit(row: any) {
	dialogMode.value = "edit";
	resetForm();
	props.columns.forEach((c) => (formData[c.prop] = row[c.prop] ?? ""));
	formData[props.idKey] = row[props.idKey];
	dialogVisible.value = true;
}

async function handleSubmit() {
	for (const col of formColumns.value) {
		if (col.prop === props.idKey) continue;
		const required = col.prop === props.columns[0]?.prop;
		if (required && !String(formData[col.prop] ?? "").trim()) {
			ElMessage.warning(`请填写${col.label}`);
			return;
		}
	}
	submitting.value = true;
	try {
		const payload: Record<string, any> = {};
		props.columns.forEach((c) => {
			if (dialogMode.value === "add" && c.prop === props.idKey) return;
			if (formData[c.prop] !== undefined && formData[c.prop] !== "") payload[c.prop] = formData[c.prop];
		});
		if (dialogMode.value === "add") {
			await props.api.add?.(payload);
			ElMessage.success("新增成功");
		} else {
			payload[props.idKey] = formData[props.idKey];
			await props.api.modify?.(payload);
			ElMessage.success("修改成功");
		}
		dialogVisible.value = false;
		loadData();
	} catch (err) {
		console.warn(err);
		ElMessage.error(dialogMode.value === "add" ? "新增失败" : "修改失败");
	} finally {
		submitting.value = false;
	}
}

const detailVisible = ref(false);
const detailLoading = ref(false);
const detailRow = ref<Record<string, any>>({});

/** 查看详细信息 */
async function openDetail(row: any) {
	detailVisible.value = true;
	detailRow.value = row;
	if (!props.api.detail) return;
	detailLoading.value = true;
	try {
		const payload = await props.api.detail(row[props.idKey]);
		const single = Array.isArray(payload) ? payload[0] : payload;
		if (single) detailRow.value = { ...row, ...single };
	} catch (err) {
		console.warn(err);
		ElMessage.error("详情加载失败");
	} finally {
		detailLoading.value = false;
	}
}

async function handleDelete() {
	if (!selected.value.length) {
		ElMessage.warning("请先勾选要删除的数据");
		return;
	}
	try {
		await ElMessageBox.confirm(`确认删除选中的 ${selected.value.length} 条数据？`, "删除确认", {
			type: "warning",
		});
	} catch {
		return;
	}
	try {
		await props.api.remove?.(selected.value.map((r) => r[props.idKey]));
		ElMessage.success("删除成功");
		loadData();
	} catch (err) {
		console.warn(err);
		ElMessage.error("删除失败");
	}
}

async function handleExport() {	try {
		await props.api.exportExcel?.(props.filename || `${props.title}.xlsx`);
		ElMessage.success("导出成功");
	} catch (err) {
		console.warn(err);
		ElMessage.error("导出失败");
	}
}

const fileInput = ref<HTMLInputElement | null>(null);

function triggerImport() {
	fileInput.value?.click();
}

async function handleFileChange(e: Event) {
	const input = e.target as HTMLInputElement;
	const file = input.files?.[0];
	if (!file) return;
	try {
		await props.api.importExcel?.(file);
		ElMessage.success("导入成功");
		loadData();
	} catch (err) {
		console.warn(err);
		ElMessage.error("导入失败");
	} finally {
		input.value = "";
	}
}

function handleSizeChange(val: number) {
	pageSize.value = val;
	pageIndex.value = 1;
	loadData();
}

function handlePageChange(val: number) {
	pageIndex.value = val;
	loadData();
}

onMounted(() => {
	loadData();
});
</script>

<template>
	<section class="dict-crud-root">
		<el-card shadow="never" class="search-card">
			<el-form :inline="true" @submit.prevent>
				<el-form-item v-for="col in searchColumns" :key="col.prop" :label="col.label">
					<el-input
						v-model="keyword[col.prop]"
						:placeholder="`请输入${col.label}`"
						clearable
						style="width: 180px"
						@keyup.enter="handleSearch"
					/>
				</el-form-item>
				<el-form-item>
					<el-button type="primary" @click="handleSearch">查询</el-button>
					<el-button @click="handleReset">重置</el-button>
				</el-form-item>
			</el-form>
		</el-card>

		<el-card shadow="never" class="table-card">
			<div class="tool-bar">
				<div class="left">
					<el-button v-if="api.add" type="primary" @click="openAdd">新增</el-button>
					<el-button v-if="api.remove" type="danger" plain @click="handleDelete">批量删除</el-button>
					<el-button v-if="api.importExcel" @click="triggerImport">导入</el-button>
					<el-button v-if="api.exportExcel" @click="handleExport">导出</el-button>
					<el-button @click="loadData">刷新</el-button>
					<input ref="fileInput" type="file" accept=".xlsx,.xls" hidden @change="handleFileChange" />
				</div>
				<span class="tip">{{ tip || `${title}维护` }}</span>
			</div>

			<el-table
				v-loading="loading"
				:data="rows"
				border
				stripe
				style="width: 100%"
				@selection-change="handleSelectionChange"
			>
				<el-table-column v-if="api.remove" type="selection" width="48" />
				<el-table-column type="index" label="序号" width="60" />
				<el-table-column
					v-for="col in columns"
					:key="col.prop"
					:prop="col.prop"
					:label="col.label"
					:width="col.width"
					:min-width="col.minWidth || 120"
					show-overflow-tooltip
				/>
				<el-table-column v-if="api.modify || api.detail" label="操作" width="150" fixed="right">
					<template #default="{ row }">
						<el-button v-if="api.detail" link type="primary" @click="openDetail(row)">详情</el-button>
						<el-button v-if="api.modify" link type="primary" @click="openEdit(row)">编辑</el-button>
					</template>
				</el-table-column>
			</el-table>

			<el-pagination
				class="pager"
				v-model:current-page="pageIndex"
				v-model:page-size="pageSize"
				:page-sizes="[10, 20, 50, 100]"
				layout="total, sizes, prev, pager, next, jumper"
				:total="total"
				@size-change="handleSizeChange"
				@current-change="handlePageChange"
			/>
		</el-card>

		<el-dialog v-model="dialogVisible" :title="dialogMode === 'add' ? `新增${title}` : `编辑${title}`" width="520px">
			<el-form :model="formData" label-width="110px">
				<el-form-item
					v-for="col in formColumns"
					:key="col.prop"
					:label="col.label"
					:required="col.prop === columns[0]?.prop"
				>
					<el-input v-model="formData[col.prop]" :placeholder="`请输入${col.label}`" clearable />
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="dialogVisible = false">取消</el-button>
				<el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
			</template>
		</el-dialog>

		<el-drawer v-model="detailVisible" :title="`${title}详情`" size="420px">
			<div v-loading="detailLoading" class="detail-body">
				<el-descriptions :column="1" border>
					<el-descriptions-item v-for="col in columns" :key="col.prop" :label="col.label">
						{{ detailRow[col.prop] ?? "—" }}
					</el-descriptions-item>
				</el-descriptions>
			</div>
		</el-drawer>
	</section>
</template>

<style lang="scss" scoped>
.dict-crud-root {
	width: 100%;

	.search-card {
		margin-bottom: 12px;
	}

	.tool-bar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
		margin-bottom: 12px;

		.left {
			display: flex;
			flex-wrap: wrap;
			gap: 8px;
		}
	}

	.tip {
		color: #909399;
		font-size: 13px;
	}

	.pager {
		margin-top: 16px;
		justify-content: flex-end;
	}
}
</style>
