<script lang="ts" setup>
definePage({
	meta: {
		menuType: "page",
		text: "商品品牌",
		icon: "IconSetting",
	},
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
	listGoodsBrands,
	addGoodsBrand,
	getGoodsBrandForEdit,
	updateGoodsBrand,
	removeGoodsBrands,
	exportGoodsBrands,
	importGoodsBrands,
	saveBlob,
} from "@/apis/goods-brand/index";

interface TableData {
	id?: string;
	goodsBrandCode?: string;
	goodsBrandName?: string;
	goodsBrandWww?: string;
	goodsBrandPic?: string;
	goodsBrandText?: string;
	goodsBrandDel?: string;
}

const componentsTableProps = ref<SimpleDataTableProps<TableData>>({
	isIndex: true,
	isMultipleSelect: true,
	data: [],
	columns: [
		{ prop: "goodsBrandCode", label: "品牌代码" },
		{ prop: "goodsBrandName", label: "品牌名称" },
		{ prop: "goodsBrandWww", label: "品牌网址" },
		{ prop: "goodsBrandText", label: "备注" },
		{ prop: "goodsBrandDel", label: "停用" },
		{ prop: "operation-bar", label: "操作" },
	],
});

const currentPageData = ref({ pageIndex: 1, pageSize: 10, pages: 0, total: 0 });
const searchForm = ref({ goodsBrandCode: "", goodsBrandName: "" });

function loadData() {
	listGoodsBrands(
		{ ...searchForm.value, pageIndex: currentPageData.value.pageIndex, pageSize: currentPageData.value.pageSize },
		(data: any) => {
			componentsTableProps.value.data = data.rows || [];
			currentPageData.value.pages = data.pages;
			currentPageData.value.total = data.total;
		},
		() => ElMessage.error("商品品牌数据加载失败"),
	);
}
function handleSearch() {
	currentPageData.value.pageIndex = 1;
	loadData();
}
function handleReset() {
	searchForm.value = { goodsBrandCode: "", goodsBrandName: "" };
	handleSearch();
}
onMounted(() => loadData());

// =============================弹窗/表单=============================
interface OnConfirmParams<T> {
	resolve: (value: T) => void;
	reject: (reason?: any) => void;
}
type OnConfirmFunction<T> = (params: OnConfirmParams<T>) => Promise<boolean>;

const emptyForm = {
	id: "",
	goodsBrandCode: "",
	goodsBrandName: "",
	goodsBrandWww: "",
	goodsBrandPic: "",
	goodsBrandText: "",
	goodsBrandDel: "0",
};
/** 0 新增 1 编辑 */
const dialogType = ref<number>(0);
const form = ref<TableData>(cloneDeep(emptyForm));
const picFile = ref<File | null>(null);
const selectedRows: Ref<TableData[]> = ref([]);

function resetForm() {
	form.value = cloneDeep(emptyForm);
	picFile.value = null;
}

const dialogPromiseProps = ref<DialogPromiseProps<TableData>>({
	dialogProps: { title: "录入商品品牌" },
	async onDialogClose({ reject, resolve }) {
		resetForm();
		resolve(form.value);
		return true;
	},
});

const onConfirm: OnConfirmFunction<any> = async ({ resolve, reject }) => {
	try {
		resolve(form.value);
		const payload: any = { ...form.value };
		// 未选择新图片时不上传该字段，后端保留原图
		if (picFile.value) payload.goodsBrandPic = picFile.value;
		else delete payload.goodsBrandPic;

		if (dialogType.value === 0) {
			await addGoodsBrand(payload);
			ElMessage.success("录入成功");
		} else {
			await updateGoodsBrand(payload);
			ElMessage.success("修改成功");
		}
		resetForm();
		loadData();
		return true;
	} catch (error) {
		ElMessage.error(dialogType.value === 0 ? "录入失败" : "修改失败");
		reject(error);
		return false;
	}
};

const dialogRef = useTemplateRef("dialog");
function openDialog() {
	if (!isNil(dialogRef.value)) dialogRef.value.open().then(() => {});
}
function isNil(v: any) {
	return v === null || v === undefined;
}

const handleAdd = () => {
	resetForm();
	dialogType.value = 0;
	dialogPromiseProps.value.dialogProps.title = "录入商品品牌";
	openDialog();
};
const handleEdit = () => {
	if (selectedRows.value.length !== 1) {
		ElMessage.warning("请选择一条记录进行编辑");
		return;
	}
	resetForm();
	dialogType.value = 1;
	dialogPromiseProps.value.dialogProps.title = "修改商品品牌";
	getGoodsBrandForEdit(
		selectedRows.value[0].id,
		(data: any) => {
			form.value = { ...emptyForm, ...data };
		},
		() => ElMessage.error("加载品牌详情失败"),
	);
	openDialog();
};

const handleBatchDelete = () => {
	if (selectedRows.value.length === 0) {
		ElMessage.warning("请至少选择一条记录进行删除");
		return;
	}
	ElMessageBox.confirm(`确定要删除选中的 ${selectedRows.value.length} 条记录吗？`, "提示", {
		confirmButtonText: "确定",
		cancelButtonText: "取消",
		type: "warning",
	})
		.then(async () => {
			try {
				await removeGoodsBrands(selectedRows.value.map((r) => r.id));
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
				await removeGoodsBrands([row.id]);
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
		const blob = await exportGoodsBrands(searchForm.value);
		saveBlob(blob, "商品品牌.xlsx");
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
		await importGoodsBrands(file);
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
			<ElInput v-model="searchForm.goodsBrandCode" placeholder="品牌代码" clearable style="width: 180px" />
			<ElInput v-model="searchForm.goodsBrandName" placeholder="品牌名称" clearable style="width: 180px" />
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
					<ElFormItem prop="goodsBrandCode" label="品牌代码：">
						<ElInput v-model="form.goodsBrandCode" />
					</ElFormItem>
					<ElFormItem prop="goodsBrandName" label="品牌名称：">
						<ElInput v-model="form.goodsBrandName" />
					</ElFormItem>
					<ElFormItem prop="goodsBrandWww" label="品牌网址：">
						<ElInput v-model="form.goodsBrandWww" />
					</ElFormItem>
					<ElFormItem prop="goodsBrandText" label="备注：">
						<ElInput v-model="form.goodsBrandText" />
					</ElFormItem>
					<ElFormItem prop="goodsBrandDel" label="停用状态：">
						<ElSelect v-model="form.goodsBrandDel" style="width: 200px">
							<ElOption label="正常" value="0" />
							<ElOption label="停用" value="1" />
						</ElSelect>
					</ElFormItem>
					<ElFormItem label="品牌图片：">
						<input type="file" accept="image/*" @change="(e:any) => picFile = e.target.files?.[0] || null" />
						<span v-if="form.goodsBrandPic" class="pic-tip">已有图片，未选择新文件时保留原图</span>
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
.pic-tip {
	font-size: 12px;
	color: #909399;
	margin-left: 8px;
}
</style>
