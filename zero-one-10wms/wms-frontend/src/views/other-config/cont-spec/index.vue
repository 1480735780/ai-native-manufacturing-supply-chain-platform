<script lang="ts" setup>
definePage({
	meta: { menuType: "page", text: "箱规", icon: "IconSetting" },
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
	listSpecifications,
	addSpecification,
	updateSpecification,
	removeSpecifications,
	exportSpecifications,
	importSpecifications,
	saveBlob,
} from "@/apis/cont-spec/index";

interface TableData {
	id?: string;
	contSpecId?: string;
	contSpecName?: string;
	createName?: string;
	createBy?: string;
	createDate?: string;
	sysOrgCode?: string;
	sysCompanyCode?: string;
}

const componentsTableProps = ref<SimpleDataTableProps<TableData>>({
	isIndex: true,
	isMultipleSelect: true,
	data: [],
	columns: [
		{ prop: "contSpecId", label: "箱规代码" },
		{ prop: "contSpecName", label: "箱规名称" },
		{ prop: "createName", label: "创建人" },
		{ prop: "createDate", label: "创建日期" },
		{ prop: "operation-bar", label: "操作" },
	],
});

const currentPageData = ref({ pageIndex: 1, pageSize: 10, pages: 0, total: 0 });
const searchForm = ref({ specificationId: "", specificationName: "" });

function loadData() {
	listSpecifications(
		{ ...searchForm.value, pageIndex: currentPageData.value.pageIndex, pageSize: currentPageData.value.pageSize },
		(data: any) => {
			componentsTableProps.value.data = data.rows || [];
			currentPageData.value.pages = data.pages;
			currentPageData.value.total = data.total;
		},
		() => ElMessage.error("箱规数据加载失败"),
	);
}
function handleSearch() {
	currentPageData.value.pageIndex = 1;
	loadData();
}
function handleReset() {
	searchForm.value = { specificationId: "", specificationName: "" };
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
	contSpecId: "",
	contSpecName: "",
	createName: "",
	createBy: "",
	sysOrgCode: "",
	sysCompanyCode: "",
};
const dialogType = ref<number>(0);
const form = ref<TableData>(cloneDeep(emptyForm));
const selectedRows: Ref<TableData[]> = ref([]);

function resetForm() {
	form.value = cloneDeep(emptyForm);
}

const dialogPromiseProps = ref<DialogPromiseProps<TableData>>({
	dialogProps: { title: "录入箱规" },
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
			await addSpecification(form.value);
			ElMessage.success("录入成功");
		} else {
			await updateSpecification(form.value);
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
	dialogPromiseProps.value.dialogProps.title = "录入箱规";
	openDialog();
};
const handleEdit = () => {
	if (selectedRows.value.length !== 1) {
		ElMessage.warning("请选择一条记录进行修改");
		return;
	}
	form.value = { ...emptyForm, ...selectedRows.value[0] };
	dialogType.value = 1;
	dialogPromiseProps.value.dialogProps.title = "修改箱规";
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
				await removeSpecifications(selectedRows.value.map((r) => r.id));
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
				await removeSpecifications([row.id]);
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
		const blob = await exportSpecifications();
		saveBlob(blob, "箱规.xlsx");
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
		await importSpecifications(file);
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
			<ElInput v-model="searchForm.specificationId" placeholder="箱规代码" clearable style="width: 180px" />
			<ElInput v-model="searchForm.specificationName" placeholder="箱规名称" clearable style="width: 180px" />
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
					<ElFormItem prop="contSpecId" label="箱规代码："><ElInput v-model="form.contSpecId" /></ElFormItem>
					<ElFormItem prop="contSpecName" label="箱规名称："><ElInput v-model="form.contSpecName" /></ElFormItem>
					<ElFormItem prop="createName" label="创建人名称："><ElInput v-model="form.createName" /></ElFormItem>
					<ElFormItem prop="createBy" label="创建人登录名："><ElInput v-model="form.createBy" /></ElFormItem>
					<ElFormItem prop="sysOrgCode" label="所属部门："><ElInput v-model="form.sysOrgCode" /></ElFormItem>
					<ElFormItem prop="sysCompanyCode" label="所属公司："><ElInput v-model="form.sysCompanyCode" /></ElFormItem>
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
