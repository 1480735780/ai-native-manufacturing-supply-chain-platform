<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { UploadFilled } from "@element-plus/icons-vue";
import {
	listRegionInfos,
	listRegionNameTree,
	listCityTypeNames,
	listBigAreaNames,
	listDistrictAreaNames,
	addRegionInfo,
	updateRegionInfo,
	removeRegionInfo,
	removeRegionInfosBatch,
	importRegionInfos,
	exportRegionInfos,
	regionInfoFileName,
	saveBlob,
} from "@/apis/reference/index";

definePage({
	meta: {
		menuType: "page",
		text: "地区信息",
		icon: "IconSetting",
	},
});

interface Row {
	id?: string;
	city_code?: string;
	city_name?: string;
	city_serc?: string;
	city_type_name?: string;
	barea_name?: string;
	area_name?: string;
	city_del?: string;
}

const loading = ref(false);
const rows = ref<Row[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const selectedRows = ref<Row[]>([]);

const query = ref({
	city_code: "",
	city_name: "",
	city_serc: "",
	city_type_name: "",
	barea_name: "",
	area_name: "",
	city_del: "",
});

// 名称树（左侧）
interface TreeNode {
	id?: string;
	name?: string;
	children?: TreeNode[];
}
const treeData = ref<TreeNode[]>([]);
const treeProps = { label: "name", children: "children" };

// 字典下拉（value 用名称：后端按名称反查编码）
const cityTypeOptions = ref<{ id: string; name: string }[]>([]);
const bigAreaOptions = ref<{ id: string; name: string }[]>([]);
const districtAreaOptions = ref<{ id: string; name: string }[]>([]);

function loadData() {
	loading.value = true;
	listRegionInfos(
		{
			pageIndex: pageIndex.value,
			pageSize: pageSize.value,
			...query.value,
		},
		(data: any) => {
			rows.value = data.rows ?? [];
			total.value = data.total || 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("地区信息加载失败");
		},
	);
}

function loadDicts() {
	listRegionNameTree(
		(data: any) => {
			treeData.value = Array.isArray(data) ? data : [];
		},
		() => {
			treeData.value = [];
		},
	);
	listCityTypeNames(
		(data: any) => {
			cityTypeOptions.value = (data ?? []).map((x: any) => ({ id: String(x.id ?? ""), name: String(x.name ?? "") })).filter((x: any) => x.name);
		},
		() => {},
	);
	listBigAreaNames(
		(data: any) => {
			bigAreaOptions.value = (data ?? []).map((x: any) => ({ id: String(x.id ?? ""), name: String(x.name ?? "") })).filter((x: any) => x.name);
		},
		() => {},
	);
	listDistrictAreaNames(
		(data: any) => {
			districtAreaOptions.value = (data ?? []).map((x: any) => ({ id: String(x.id ?? ""), name: String(x.name ?? "") })).filter((x: any) => x.name);
		},
		() => {},
	);
}

function handleTreeClick(node: any) {
	query.value.city_name = node?.name ?? "";
	handleSearch();
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	query.value = {
		city_code: "",
		city_name: "",
		city_serc: "",
		city_type_name: "",
		barea_name: "",
		area_name: "",
		city_del: "",
	};
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

function enabledText(value?: string) {
	if (value === "0" || value === "N") return "启用";
	if (value === "1" || value === "Y") return "停用";
	return value ?? "-";
}

const dialogVisible = ref(false);
const isEdit = ref(false);
const formRef = ref();
const emptyForm = () => ({
	id: "",
	city_code: "",
	city_name: "",
	city_serc: "",
	city_type_name: "",
	barea_name: "",
	area_name: "",
	city_del: "N",
});
const form = ref(emptyForm());
const rules = {
	city_code: [{ required: true, message: "请输入地区代码", trigger: "blur" }],
	city_name: [{ required: true, message: "请输入地区名称", trigger: "blur" }],
	city_type_name: [{ required: true, message: "请选择城市类型", trigger: "change" }],
	barea_name: [{ required: true, message: "请选择大区", trigger: "change" }],
	area_name: [{ required: true, message: "请选择片区", trigger: "change" }],
};

function openAdd() {
	isEdit.value = false;
	form.value = emptyForm();
	dialogVisible.value = true;
}

function openEdit(row: Row) {
	isEdit.value = true;
	form.value = {
		id: row.id ?? "",
		city_code: row.city_code ?? "",
		city_name: row.city_name ?? "",
		city_serc: row.city_serc ?? "",
		city_type_name: row.city_type_name ?? "",
		barea_name: row.barea_name ?? "",
		area_name: row.area_name ?? "",
		city_del: row.city_del ?? "N",
	};
	dialogVisible.value = true;
}

async function submitForm() {
	await formRef.value?.validate();
	try {
		if (isEdit.value) {
			await updateRegionInfo({ ...form.value });
			ElMessage.success("修改成功");
		} else {
			const { id, ...payload } = form.value;
			await addRegionInfo(payload);
			ElMessage.success("录入成功");
		}
		dialogVisible.value = false;
		loadData();
	} catch (err: any) {
		ElMessage.error(err?.message || "操作失败");
	}
}

async function handleDelete(row: Row) {
	await ElMessageBox.confirm(`确定要删除「${row.city_name}」吗？`, "提示", { type: "warning" });
	try {
		// 单删接口 body 为裸 JSON 字符串 id
		await removeRegionInfo(row.id!);
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
		const msg = await removeRegionInfosBatch(ids);
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
		const msg = await importRegionInfos(importFileRef.value);
		ElMessage.success(typeof msg === "string" ? msg : "导入成功");
		importVisible.value = false;
		loadData();
	} catch (err: any) {
		ElMessage.error(err?.message || "导入失败");
	}
}

async function handleExport() {
	try {
		const blob = await exportRegionInfos();
		saveBlob(new Blob([blob]), regionInfoFileName());
		ElMessage.success("导出成功");
	} catch {
		ElMessage.error("导出失败");
	}
}

onMounted(() => {
	loadData();
	loadDicts();
});
</script>

<template>
	<section class="regional-information-root">
		<div class="main-layout">
			<div class="tree-panel">
				<div class="tree-title">地区名称树</div>
				<el-tree :data="treeData" :props="treeProps" node-key="id" @node-click="handleTreeClick" />
			</div>

			<div class="content-panel">
				<div class="query-bar">
					<el-form inline @submit.prevent="handleSearch">
						<el-form-item label="地区代码">
							<el-input v-model="query.city_code" placeholder="请输入代码" clearable @keyup.enter="handleSearch" />
						</el-form-item>
						<el-form-item label="地区名称">
							<el-input v-model="query.city_name" placeholder="请输入名称" clearable @keyup.enter="handleSearch" />
						</el-form-item>
						<el-form-item label="助记码">
							<el-input v-model="query.city_serc" placeholder="请输入助记码" clearable @keyup.enter="handleSearch" />
						</el-form-item>
						<el-form-item label="城市类型">
							<el-select v-model="query.city_type_name" placeholder="全部" clearable style="width: 140px">
								<el-option v-for="o in cityTypeOptions" :key="o.id" :label="o.name" :value="o.name" />
							</el-select>
						</el-form-item>
						<el-form-item label="大区">
							<el-select v-model="query.barea_name" placeholder="全部" clearable style="width: 140px">
								<el-option v-for="o in bigAreaOptions" :key="o.id" :label="o.name" :value="o.name" />
							</el-select>
						</el-form-item>
						<el-form-item label="片区">
							<el-select v-model="query.area_name" placeholder="全部" clearable style="width: 140px">
								<el-option v-for="o in districtAreaOptions" :key="o.id" :label="o.name" :value="o.name" />
							</el-select>
						</el-form-item>
						<el-form-item label="状态">
							<el-select v-model="query.city_del" placeholder="全部" clearable style="width: 110px">
								<el-option label="启用" value="N" />
								<el-option label="停用" value="Y" />
							</el-select>
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
					<el-table-column prop="city_code" label="地区代码" width="130" />
					<el-table-column prop="city_name" label="地区名称" width="140" />
					<el-table-column prop="city_serc" label="地区助记码" width="120" />
					<el-table-column prop="city_type_name" label="城市类型" width="110" />
					<el-table-column prop="barea_name" label="大区信息" width="140" show-overflow-tooltip />
					<el-table-column prop="area_name" label="片区信息" width="140" show-overflow-tooltip />
					<el-table-column label="状态" width="90">
						<template #default="{ row }">{{ enabledText(row.city_del) }}</template>
					</el-table-column>
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
			</div>
		</div>

		<el-dialog v-model="dialogVisible" :title="isEdit ? '修改地区信息' : '录入地区信息'" width="520px">
			<el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
				<el-form-item label="地区代码" prop="city_code">
					<el-input v-model="form.city_code" placeholder="请输入代码" />
				</el-form-item>
				<el-form-item label="地区名称" prop="city_name">
					<el-input v-model="form.city_name" placeholder="请输入名称" />
				</el-form-item>
				<el-form-item label="地区助记码" prop="city_serc">
					<el-input v-model="form.city_serc" placeholder="请输入助记码" />
				</el-form-item>
				<el-form-item label="城市类型" prop="city_type_name">
					<el-select v-model="form.city_type_name" placeholder="请选择" style="width: 100%">
						<el-option v-for="o in cityTypeOptions" :key="o.id" :label="o.name" :value="o.name" />
					</el-select>
				</el-form-item>
				<el-form-item label="大区" prop="barea_name">
					<el-select v-model="form.barea_name" placeholder="请选择" style="width: 100%">
						<el-option v-for="o in bigAreaOptions" :key="o.id" :label="o.name" :value="o.name" />
					</el-select>
				</el-form-item>
				<el-form-item label="片区" prop="area_name">
					<el-select v-model="form.area_name" placeholder="请选择" style="width: 100%">
						<el-option v-for="o in districtAreaOptions" :key="o.id" :label="o.name" :value="o.name" />
					</el-select>
				</el-form-item>
				<el-form-item label="状态" prop="city_del">
					<el-radio-group v-model="form.city_del">
						<el-radio value="N">启用</el-radio>
						<el-radio value="Y">停用</el-radio>
					</el-radio-group>
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="dialogVisible = false">取消</el-button>
				<el-button type="primary" @click="submitForm">确定</el-button>
			</template>
		</el-dialog>

		<el-dialog v-model="importVisible" title="导入地区信息" width="480px">
			<el-upload drag action="#" :auto-upload="false" :limit="1" :on-change="onImportFileChange" accept=".xlsx,.xls">
				<el-icon class="el-icon--upload"><upload-filled /></el-icon>
				<div class="el-upload__text">拖拽文件到此处或 <em>点击选择</em></div>
				<template #tip>
					<div class="el-upload__tip">只能上传 Excel 文件，表头行会被自动跳过；城市类型/大区/片区列请填写名称</div>
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
.regional-information-root {
	width: 100%;

	.main-layout {
		display: flex;
		gap: 16px;
		align-items: flex-start;
	}

	.tree-panel {
		width: 220px;
		flex-shrink: 0;
		border: 1px solid var(--el-border-color-light);
		border-radius: 6px;
		padding: 10px;
		margin-top: 12px;
		max-height: 560px;
		overflow: auto;

		.tree-title {
			font-weight: 500;
			margin-bottom: 8px;
		}
	}

	.content-panel {
		flex: 1;
		min-width: 0;
	}

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
