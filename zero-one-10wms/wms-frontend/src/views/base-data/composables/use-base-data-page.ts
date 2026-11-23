import { ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { saveBlob } from "@/apis/base-data/index.js";

export interface BaseDataPageOptions {
	listApi: (data: any, success: (data: any) => void, fail: () => void) => void;
	/** 只读页面可不传删除/导出/导入接口 */
	removeApi?: (ids: any[]) => Promise<any>;
	exportApi?: (ids: any[], query: any) => Promise<Blob>;
	importApi?: (file: File) => Promise<any>;
	rowKey: (row: any) => any;
	rowLabel?: (row: any) => string;
	fileName: string;
	loadFailText?: string;
}

export function errText(err: any, fallback: string) {
	return err?.data?.message || err?.message || err?.response?.data?.message || fallback;
}

/**
 * 基础资料页面通用逻辑：分页查询、勾选、单删/批删、导出、导入。
 * 页面只负责查询条件、表格列和表单。
 */
export function useBaseDataPage(options: BaseDataPageOptions) {
	const loading = ref(false);
	const rows = ref<any[]>([]);
	const total = ref(0);
	const pageIndex = ref(1);
	const pageSize = ref(10);
	const selectedRows = ref<any[]>([]);

	let queryBuilder: () => any = () => ({});

	function setQueryBuilder(fn: () => any) {
		queryBuilder = fn;
	}

	function currentQuery() {
		return queryBuilder() || {};
	}

	function loadData() {
		loading.value = true;
		options.listApi(
			{ pageIndex: pageIndex.value, pageSize: pageSize.value, ...currentQuery() },
			(data: any) => {
				rows.value = data?.rows ?? [];
				total.value = data?.total ?? 0;
				loading.value = false;
			},
			() => {
				loading.value = false;
				ElMessage.error(options.loadFailText || "数据加载失败");
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

	function handleSelectionChange(list: any[]) {
		selectedRows.value = list;
	}

	function afterDelete() {
		if (rows.value.length === 1 && pageIndex.value > 1) {
			pageIndex.value -= 1;
		}
		loadData();
	}

	async function removeRow(row: any) {
		const key = options.rowKey(row);
		if (key === undefined || key === null || key === "") {
			ElMessage.warning("该记录缺少主键，无法删除");
			return;
		}
		const label = options.rowLabel ? options.rowLabel(row) : key;
		try {
			await ElMessageBox.confirm(`确认删除「${label}」？`, "提示", { type: "warning" });
		} catch {
			return;
		}
		try {
			if (!options.removeApi) {
				ElMessage.error("当前页面不支持删除操作");
				return;
			}
			await options.removeApi([key]);
			ElMessage.success("删除成功");
			afterDelete();
		} catch (err: any) {
			ElMessage.error(errText(err, "删除失败"));
		}
	}

	async function removeSelected() {
		const ids = selectedRows.value.map(options.rowKey).filter((v) => v !== undefined && v !== null && v !== "");
		if (ids.length === 0) {
			ElMessage.warning("请先勾选要删除的记录");
			return;
		}
		try {
			await ElMessageBox.confirm(`确认删除选中的 ${ids.length} 条记录？`, "提示", { type: "warning" });
		} catch {
			return;
		}
		try {
			if (!options.removeApi) {
				ElMessage.error("当前页面不支持批量删除操作");
				return;
			}
			await options.removeApi(ids);
			ElMessage.success("批量删除成功");
			afterDelete();
		} catch (err: any) {
			ElMessage.error(errText(err, "批量删除失败"));
		}
	}

	async function exportData() {
		const ids = selectedRows.value.map(options.rowKey).filter((v) => v !== undefined && v !== null && v !== "");
		try {
			if (!options.exportApi) {
				ElMessage.error("当前页面不支持导出操作");
				return;
			}
			const blob = await options.exportApi(ids, currentQuery());
			saveBlob(blob, `${options.fileName}_${Date.now()}.xlsx`);
			ElMessage.success("导出成功");
		} catch (err: any) {
			ElMessage.error(errText(err, "导出失败"));
		}
	}

	const importVisible = ref(false);
	const importSaving = ref(false);
	const importFile = ref<File | null>(null);
	const importFileList = ref<any[]>([]);

	function openImport() {
		importFile.value = null;
		importFileList.value = [];
		importVisible.value = true;
	}

	function handleImportChange(file: any) {
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
			if (!options.importApi) {
				ElMessage.error("当前页面不支持导入操作");
				return;
			}
			const result = await options.importApi(importFile.value);
			ElMessage.success(result ? String(result) : "导入成功");
			importVisible.value = false;
			loadData();
		} catch (err: any) {
			ElMessage.error(errText(err, "导入失败"));
		} finally {
			importSaving.value = false;
		}
	}

	return {
		loading,
		rows,
		total,
		pageIndex,
		pageSize,
		selectedRows,
		setQueryBuilder,
		loadData,
		handleSearch,
		handlePageChange,
		handleSizeChange,
		handleSelectionChange,
		removeRow,
		removeSelected,
		exportData,
		importVisible,
		importSaving,
		importFile,
		importFileList,
		openImport,
		handleImportChange,
		handleImportRemove,
		submitImport,
	};
}
