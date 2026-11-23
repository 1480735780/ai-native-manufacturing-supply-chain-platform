<script lang="ts" setup>
definePage({
	meta: { menuType: "page", text: "港口信息", icon: "IconSetting" },
});
import { ElButton, ElMessage, ElMessageBox } from "element-plus";
import { ref, useTemplateRef, onMounted } from "vue";
import { cloneDeep } from "lodash-es";
import ComponentsTable from "components/table/index.vue";
import ComponentsDialogPromise from "components/dialog-promise/index.vue";
import { type DialogPromiseProps } from "components/dialog-promise/types";
import Pagination from "@/components/Pagination/index.vue";
import "element-plus/dist/index.css";
import { Download, Plus, Upload } from "@element-plus/icons-vue";
import Edit from "@/components/table-title/table-icon/Edit.vue";
import Delete from "@/components/table-title/table-icon/Delete.vue";

import {
	listPorts,
	addPort,
	updatePort,
	removePorts,
	exportPorts,
	importPorts,
	saveBlob,
} from "@/apis/port/index";

interface TableData {
	id?: string;
	portCode?: string;
	portZhName?: string;
	portEnName?: string;
	portThCode?: string;
	portUcode?: string;
	portCode1?: string;
	portCode2?: string;
	portText?: string;
	portDel?: string;
}

const componentsTableProps = ref<SimpleDataTableProps<TableData>>({
	isIndex: true,
	isMultipleSelect: true,
	data: [],
	columns: [
		{ prop: "portCode", label: "港口代码" },
		{ prop: "portZhName", label: "中文名称" },
		{ prop: "portEnName", label: "英文名称" },
		{ prop: "portThCode", label: "三字代码" },
		{ prop: "portUcode", label: "UNCODE" },
		{ prop: "portText", label: "备注" },
		{ prop: "operation-bar", label: "操作" },
	],
});

const currentPageData = ref({ pageIndex: 1, pageSize: 10, pages: 0, total: 0 });
const searchForm = ref({ portCode: "", portZhName: "", portEnName: "", portThCode: "" });

function loadData() {
	listPorts(
		{ ...searchForm.value, pageIndex: currentPageData.value.pageIndex, pageSize: currentPageData.value.pageSize },
		(data: any) => {
			componentsTableProps.value.data = data.rows || [];
			currentPageData.value.pages = data.pages;
			currentPageData.value.total = data.total;
		},
		() => ElMessage.error("港口信息数据加载失败"),
	);
}
function handleSearch() {
	currentPageData.value.pageIndex = 1;
	loadData();
}
function handleReset() {
	searchForm.value = { portCode: "", portZhName: "", portEnName: "", portThCode: "" };
	handleSearch();
}
onMounted(() => loadData());

interface OnConfirmParams<T> {
	resolve: (value: T) => void;
	reject: (reason?: any) => void;
}
type OnConfirmFunction<T> = (params: OnConfirmParams<T>) => Promise<boolean>;

const emptyForm = {
	id: "",
	portCode: "",
	portZhName: "",
	portEnName: "",
	portThCode: "",
	portUcode: "",
	portCode1: "",
	portCode2: "",
	portText: "",
	portDel: "0",
};
const dialogType = ref<number>(0);
const form = ref<TableData>(cloneDeep(emptyForm));
const selectedRows: Ref<TableData[]> = ref([]);

function resetForm() {
	form.value = cloneDeep(emptyForm);
}

const dialogPromiseProps = ref<DialogPromiseProps<TableData>>({
	dialogProps: { title: "录入港口信息" },
	async onDialogClose({ reject, resolve }) {
		resetForm();
		resolve(form.value);
		return true;
	},
});

const onConfirm: OnConfirmFunction<any> = async ({ resolve, reject }) => {
	try {
		resolve(form.value);
		if (dialogType.value === 0) {
			await addPort(form.value);
			ElMessage.success("录入成功");
		} else {
			await updatePort(form.value);
			ElMessage.success("修改成功");
		}
		resetForm();
		loadData();
		return true;
	} catch {
		ElMessage.error(dialogType.value === 0 ? "录入失败" : "修改失败");
		reject(new Error("save failed"));
		return false;
	}
};

const dialogRef = useTemplateRef("dialog");
const isNil = (v: any) => v === null || v === undefined;
function openDialog() {
	if (!isNil(dialogRef.value)) dialogRef.value.open().then(() => {});
}
const handleAdd = () => {
	resetForm();
	dialogType.value = 0;
	dialogPromiseProps.value.dialogProps.title = "录入港口信息";
	openDialog();
};
const handleEdit = () => {
	if (selectedRows.value.length !== 1) {
		ElMessage.warning("请选择一条记录进行修改");
		return;
	}
	form.value = { ...emptyForm, ...selectedRows.value[0] };
	dialogType.value = 1;
	dialogPromiseProps.value.dialogProps.title = "修改港口信息";
	openDialog();
};

const handleBatchDelete = () => {
	if (selectedRows.value.length === 0) {
		ElMessage.warning("请至少选择一条记录进行删除");
		return;
	}
	ElMessageBox.confirm(`确定要删除选中的 ${selectedRows.value.length} 条记录吗？`, "提示", { type: "warning" })
		.then(async () => {
			try {
				await removePorts(selectedRows.value.map((r) => r.id));
				ElMessage.success("批量删除成功");
				loadData();
			} catch {
				ElMessage.error("批量删除失败");
			}
		})
		.catch(() => {});
};
const handleDelete = (row: TableData) => {
	ElMessageBox.confirm("确定要删除这条记录吗？", "提示", { type: "warning" })
		.then(async () => {
			try {
				await removePorts([row.id]);
				ElMessage.success("删除成功");
				loadData();
			} catch {
				ElMessage.error("删除失败");
			}
		})
		.catch(() => {});
};

const handleExport = async () => {
	try {
		const blob = await exportPorts();
		saveBlob(blob, "港口信息.xlsx");
	} catch {
		ElMessage.error("导出失败");
	}
};
const fileInput = useTemplateRef<HTMLInputElement>("fileInput");
const handleImportClick = () => fileInput.value?.click();
const handleFileChange = async (event: Event) => {
	const input = event.target as HTMLInputElement;
	const file = input.files?.[0];
	if (!file) return;
	try {
		await importPorts(file);
		ElMessage.success("导入成功");
		loadData();
	} catch {
		ElMessage.error("导入失败");
	}
	input.value = "";
};

const handlePageChange = (data: any) => {
	currentPageData.value.pageIndex = data.pageNum;
	currentPageData.value.pageSize = data.pageSize;
	loadData();
};
</script>

<template>
	<section class="menu-page example-root">
		<div class="search-bar">
			<ElInput v-model="searchForm.portCode" placeholder="港口代码" clearable style="width: 160px" />
			<ElInput v-model="searchForm.portZhName" placeholder="中文名称" clearable style="width: 160px" />
			<ElInput v-model="searchForm.portEnName" placeholder="英文名称" clearable style="width: 160px" />
			<ElInput v-model="searchForm.portThCode" placeholder="三字代码" clearable style="width: 140px" />
			<ElButton type="primary" @click="handleSearch">查询</ElButton>
			<ElButton @click="handleReset">重置</ElButton>
		</div>
		<div class="button-group">
			<ElButton type="primary" @click="handleAdd"><el-icon><Plus /></el-icon>录入</ElButton>
			<ElButton type="primary" @click="handleEdit"><el-icon><Edit /></el-icon>修改</ElButton>
			<ElButton type="danger" @click="handleBatchDelete"><el-icon><Delete /></el-icon>批量删除</ElButton>
			<ElButton @click="handleImportClick"><el-icon><Upload /></el-icon>导入</ElButton>
			<ElButton @click="handleExport"><el-icon><Download /></el-icon>导出</ElButton>
		</div>
		<input ref="fileInput" type="file" accept=".xlsx,.xls" style="display: none" @change="handleFileChange" />

		<ComponentsDialogPromise :="dialogPromiseProps" ref="dialog">
			<template #default>
				<ElForm :model="form" label-position="right" label-width="110px">
					<ElFormItem prop="portCode" label="港口代码："><ElInput v-model="form.portCode" /></ElFormItem>
					<ElFormItem prop="portZhName" label="中文名称："><ElInput v-model="form.portZhName" /></ElFormItem>
					<ElFormItem prop="portEnName" label="英文名称："><ElInput v-model="form.portEnName" /></ElFormItem>
					<ElFormItem prop="portThCode" label="三字代码："><ElInput v-model="form.portThCode" /></ElFormItem>
					<ElFormItem prop="portUcode" label="UNCODE："><ElInput v-model="form.portUcode" /></ElFormItem>
					<ElFormItem prop="portCode1" label="代码1："><ElInput v-model="form.portCode1" /></ElFormItem>
					<ElFormItem prop="portCode2" label="代码2："><ElInput v-model="form.portCode2" /></ElFormItem>
					<ElFormItem prop="portText" label="备注："><ElInput v-model="form.portText" /></ElFormItem>
					<ElFormItem prop="portDel" label="停用：">
						<ElSelect v-model="form.portDel" style="width: 200px">
							<ElOption label="正常" value="0" />
							<ElOption label="停用" value="1" />
						</ElSelect>
					</ElFormItem>
				</ElForm>
			</template>
			<template #footer="{ reject, resolve }">
				<ElButton type="info" @click="dialogPromiseProps.onDialogClose({ reject, resolve })">关闭</ElButton>
				<ElButton type="primary" @click="onConfirm({ reject, resolve })">确认</ElButton>
			</template>
		</ComponentsDialogPromise>

		<ComponentsTable :="componentsTableProps" @selection-change="selectedRows = $event">
			<template #bodyCell="{ prop, row }">
				<template v-if="prop === 'operation-bar'">
					<ElButton type="danger" link @click="handleDelete(row)">删除</ElButton>
				</template>
			</template>
		</ComponentsTable>

		<div class="demo-section">
			<Pagination
				:page-total="currentPageData.total"
				:page-sizes="[10, 20, 50, 100]"
				:pager-count="currentPageData.pages"
				:current-page="currentPageData.pageIndex"
				:page-size="currentPageData.pageSize"
				layout="total, sizes, prev, pager, next, jumper"
				@page-func="handlePageChange"
			/>
		</div>
	</section>
</template>

<style lang="scss" scoped>
.search-bar,
.button-group {
	margin: 20px 5px;
}
.search-bar .el-input {
	margin-right: 8px;
}
.demo-section {
	margin-bottom: 30px;
	padding: 20px;
	border: 1px solid #eee;
	border-radius: 8px;
}
</style>
