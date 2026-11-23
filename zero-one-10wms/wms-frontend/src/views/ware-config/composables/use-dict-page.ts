/**
 * 仓库配置通用字典页面工厂（列表 + 条件查询 + 分页 + 录入/修改/删除/批量删除 + 导入/导出）
 * 供订单类型/业务类型/作业类型/业务环节/操作类型/提货方式/接货方式/库位类型/温度属性 9 个子模块复用
 */
import { ref, reactive, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { UploadFile, UploadFiles } from "element-plus";
import type { Component } from "@element-plus/icons-vue";

export interface DictColumn {
	label: string;
	prop: string;
	width?: number;
	editable?: boolean;
}

export interface DictPageOptions {
	/** 页面标题 */
	title: string;
	/** 菜单图标 */
	icon?: Component | string;
	/** 行数据字段（不含 id） */
	columns: DictColumn[];
	/** 查询条件字段 */
	queryFields: { prop: string; label: string }[];
	/** 录入参数字段 */
	addFields: { prop: string; label: string }[];
	/** 修改参数字段（通常含 id） */
	editFields: { prop: string; label: string }[];
	/** 列表 */
	listApi: (data: any, success: (d: any) => void, fail: (e?: any) => void) => void;
	/** 新增 */
	addApi?: (data: any) => Promise<any>;
	/** 修改 */
	updateApi?: (data: any) => Promise<any>;
	/** 单删（传行 id） */
	deleteApi?: (id: any) => Promise<any>;
	/** 批删（传 id 数组） */
	deleteBatchApi?: (ids: any[]) => Promise<any>;
	/** 导入（file） */
	importApi?: (file: File) => Promise<any>;
	/** 导出（返回 blob） */
	exportApi?: () => Promise<Blob>;
	/** 导出文件名 */
	exportFileName?: string;
	/** 兼容：行 id 字段名，默认 id */
	rowKey?: string;
}

export function useDictPage(options: DictPageOptions) {
	const rowKey = options.rowKey || "id";
	const loading = ref(false);
	const rows = ref<any[]>([]);
	const total = ref(0);
	const pageIndex = ref(1);
	const pageSize = ref(10);
	const selectedRows = ref<any[]>([]);
	const query = reactive<Record<string, string>>({});

	const dialogVisible = ref(false);
	const dialogMode = ref<"add" | "edit">("add");
	const dialogSaving = ref(false);
	const formRef = ref();
	const form = reactive<Record<string, string>>({});

	const importVisible = ref(false);
	const importSaving = ref(false);
	const importFileList = ref<UploadFiles>([]);
	const importFile = ref<File | null>(null);

	const selectedIds = computed(() =>
		selectedRows.value.map(item => item[rowKey]).filter((v): v is string => !!v),
	);

	function loadData() {
		loading.value = true;
		options.listApi(
			{ pageIndex: pageIndex.value, pageSize: pageSize.value, ...query },
			(data: any) => {
				rows.value = data?.rows ?? [];
				total.value = data?.total ?? 0;
				loading.value = false;
			},
			() => {
				loading.value = false;
				ElMessage.error(`${options.title}数据加载失败`);
			},
		);
	}

	function handleSelectionChange(selection: any[]) {
		selectedRows.value = selection;
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

	function handleSearch() {
		pageIndex.value = 1;
		loadData();
	}

	function handleReset() {
		Object.keys(query).forEach(key => (query[key] = ""));
		pageIndex.value = 1;
		loadData();
	}

	function resetForm() {
		Object.keys(form).forEach(key => delete form[key]);
	}

	function openAdd() {
		dialogMode.value = "add";
		resetForm();
		dialogVisible.value = true;
	}

	function openEdit(row: any) {
		dialogMode.value = "edit";
		resetForm();
		// 整行回填：兜住 id、sys_org_code、sys_company_code 等修改接口需要但不在编辑表单中展示的字段
		Object.assign(form, row);
		(options.editFields.length ? options.editFields : options.addFields).forEach(f => {
			form[f.prop] = row[f.prop] ?? "";
		});
		dialogVisible.value = true;
	}

	async function handleSave() {
		if (!options.addApi || !options.updateApi) {
			ElMessage.warning("当前模块未接入保存接口");
			return;
		}
		dialogSaving.value = true;
		try {
			if (dialogMode.value === "add") {
				await options.addApi({ ...form });
				ElMessage.success("录入成功");
			} else {
				await options.updateApi({ ...form });
				ElMessage.success("修改成功");
			}
			dialogVisible.value = false;
			loadData();
		} catch (e) {
			console.warn(e);
			ElMessage.error(dialogMode.value === "add" ? "录入失败" : "修改失败");
		} finally {
			dialogSaving.value = false;
		}
	}

	async function handleDelete(row: any) {
		if (!options.deleteApi) {
			ElMessage.warning("当前模块未接入删除接口");
			return;
		}
		try {
			await ElMessageBox.confirm(`确定删除该条${options.title}记录吗？`, "提示", {
				type: "warning",
			});
		} catch {
			return;
		}
		try {
			await options.deleteApi(row[rowKey]);
			ElMessage.success("删除成功");
			loadData();
		} catch (e) {
			console.warn(e);
			ElMessage.error("删除失败");
		}
	}

	async function handleDeleteBatch() {
		if (!options.deleteBatchApi) {
			ElMessage.warning("当前模块未接入批量删除接口");
			return;
		}
		if (selectedIds.value.length === 0) {
			ElMessage.warning("请先勾选要删除的记录");
			return;
		}
		try {
			await ElMessageBox.confirm(`确定删除选中的 ${selectedIds.value.length} 条记录吗？`, "提示", {
				type: "warning",
			});
		} catch {
			return;
		}
		try {
			await options.deleteBatchApi(selectedIds.value);
			ElMessage.success("批量删除成功");
			loadData();
		} catch (e) {
			console.warn(e);
			ElMessage.error("批量删除失败");
		}
	}

	function openImport() {
		if (!options.importApi) {
			ElMessage.warning("当前模块未接入导入接口");
			return;
		}
		importFileList.value = [];
		importFile.value = null;
		importVisible.value = true;
	}

	function handleImportChange(uploadFile: UploadFile, uploadFiles: UploadFiles) {
		importFileList.value = uploadFiles;
		importFile.value = (uploadFile.raw as File) ?? null;
	}

	async function handleImportSubmit() {
		if (!options.importApi) return;
		if (!importFile.value) {
			ElMessage.warning("请先选择要导入的 Excel 文件");
			return;
		}
		importSaving.value = true;
		try {
			await options.importApi(importFile.value);
			ElMessage.success("导入成功");
			importVisible.value = false;
			loadData();
		} catch (e) {
			console.warn(e);
			ElMessage.error("导入失败，请检查文件格式（表头需与模板一致）");
		} finally {
			importSaving.value = false;
		}
	}

	async function handleExport() {
		if (!options.exportApi) {
			ElMessage.warning("当前模块未接入导出接口");
			return;
		}
		try {
			const blob = await options.exportApi();
			const { saveBlob } = await import("@/apis/ware-config/index.js");
			saveBlob(blob, `${options.exportFileName || options.title}_${Date.now()}.xlsx`);
		} catch (e) {
			console.warn(e);
			ElMessage.error("导出失败");
		}
	}

	onMounted(() => {
		loadData();
	});

	return {
		rowKey,
		loading,
		rows,
		total,
		pageIndex,
		pageSize,
		selectedRows,
		selectedIds,
		query,
		dialogVisible,
		dialogMode,
		dialogSaving,
		formRef,
		form,
		importVisible,
		importSaving,
		importFileList,
		loadData,
		handleSelectionChange,
		handlePageChange,
		handleSizeChange,
		handleSearch,
		handleReset,
		openAdd,
		openEdit,
		handleSave,
		handleDelete,
		handleDeleteBatch,
		openImport,
		handleImportChange,
		handleImportSubmit,
		handleExport,
	};
}
