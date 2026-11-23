<script lang="ts" setup>
import { ref, reactive, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { UploadFile, UploadFiles } from "element-plus";
import {
	listCostDetails,
	addCostDetail,
	updateCostDetail,
	deleteCostDetail,
	deleteCostDetails,
	chargeCostDetails,
	dischargeCostDetails,
	downloadCostDetails,
	uploadCostDetails,
	listCostNames,
	listCustomerBills,
	saveBlob,
} from "@/apis/cost-management/index";

definePage({
	meta: {
		menuType: "page",
		text: "费用明细",
		icon: "IconSetting",
	},
});

interface CostRow {
	id?: string;
	create_name?: string;
	create_date?: string;
	cus_code?: string;
	cus_name?: string;
	cost_code?: string;
	cost_name?: string;
	cost_data?: string;
	day_cost_yj?: string;
	day_cost_bhs?: string;
	day_cost_se?: string;
	day_cost_hsj?: string;
	cost_ori?: string;
	beizhu?: string;
	cost_sta?: string;
	cost_sl?: string;
	cost_unit?: string;
	cost_js?: string;
}

const loading = ref(false);
const rows = ref<CostRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const selectedRows = ref<CostRow[]>([]);

const searchForm = reactive({
	cusCode: "",
	cusName: "",
	costCode: "",
	costName: "",
	dateRange: [] as string[],
	costOrigin: "",
	note: "",
	costState: "",
});

const costNameOptions = ref<{ code: string; name: string }[]>([]);
const costNameMap = ref<Record<string, string>>({});
const customerNameMap = ref<Record<string, string>>({});
const customerOptions = ref<{ code: string; name: string }[]>([]);

const dialogVisible = ref(false);
const dialogMode = ref<"add" | "edit">("add");
const dialogSaving = ref(false);
const formRef = ref();
const form = reactive({
	id: "",
	cus_code: "",
	cost_code: "",
	cost_date: "",
	day_cost_yj: "",
	day_cost_bhs: "",
	day_cost_se: "",
	day_cost_hsj: "",
	cost_ori: "",
	beizhu: "",
	cost_sta: "",
	cost_sl: "",
	cost_unit: "",
});

const importVisible = ref(false);
const importSaving = ref(false);
const importFileList = ref<UploadFiles>([]);
const importFile = ref<File | null>(null);

const selectedIds = computed(() =>
	selectedRows.value.map(item => item.id).filter((id): id is string => !!id),
);

function formatDateTime(value?: string) {
	if (!value) return "";
	return String(value).replace("T", " ").replace(/\.\d+$/, "");
}

function costNameOf(row: CostRow) {
	return row.cost_name || costNameMap.value[row.cost_code ?? ""] || row.cost_code || "";
}

function customerNameOf(row: CostRow) {
	return row.cus_name || customerNameMap.value[row.cus_code ?? ""] || row.cus_code || "";
}

function receiptText(value?: string) {
	return value === "Y" ? "已收款" : "未收款";
}

function buildQuery() {
	const query: Record<string, any> = {
		cusCode: searchForm.cusCode,
		cusName: searchForm.cusName,
		costCode: searchForm.costCode,
		costName: searchForm.costName,
		costOrigin: searchForm.costOrigin,
		note: searchForm.note,
		costState: searchForm.costState,
	};
	if (searchForm.dateRange && searchForm.dateRange.length === 2) {
		query.costDateBegin = `${searchForm.dateRange[0]} 00:00:00`;
		query.costDateEnd = `${searchForm.dateRange[1]} 00:00:00`;
	}
	return query;
}

function loadData() {
	loading.value = true;
	listCostDetails(
		{ pageIndex: pageIndex.value, pageSize: pageSize.value, ...buildQuery() },
		(data: any) => {
			rows.value = data?.rows ?? [];
			total.value = data?.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("费用明细加载失败");
		},
	);
}

function loadCostNames() {
	listCostNames(
		{ pageIndex: 1, pageSize: 500 },
		(data: any) => {
			const list = data?.rows ?? [];
			costNameOptions.value = list.map((item: any) => ({
				code: item.cost_code,
				name: item.cost_name,
			}));
			const map: Record<string, string> = {};
			list.forEach((item: any) => {
				if (item.cost_code) map[item.cost_code] = item.cost_name;
			});
			costNameMap.value = map;
		},
		() => {},
	);
}

function loadCustomerNames() {
	listCustomerBills(
		{ pageIndex: 1, pageSize: 500 },
		(data: any) => {
			const map: Record<string, string> = {};
			const options: { code: string; name: string }[] = [];
			(data?.rows ?? []).forEach((item: any) => {
				if (item.customercode) {
					map[item.customercode] = item.fullchinesename;
					options.push({ code: item.customercode, name: item.fullchinesename });
				}
			});
			customerNameMap.value = map;
			customerOptions.value = options;
		},
		() => {},
	);
}

function handleCustomerChange(code: string) {
	searchForm.cusName = customerNameMap.value[code] ?? "";
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	searchForm.cusCode = "";
	searchForm.cusName = "";
	searchForm.costCode = "";
	searchForm.costName = "";
	searchForm.dateRange = [];
	searchForm.costOrigin = "";
	searchForm.note = "";
	searchForm.costState = "";
	pageIndex.value = 1;
	loadData();
}

function handleCostNameChange(code: string) {
	searchForm.costName = costNameMap.value[code] ?? "";
}

function handleSelectionChange(selection: CostRow[]) {
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

function resetForm() {
	form.id = "";
	form.cus_code = "";
	form.cost_code = "";
	form.cost_date = "";
	form.day_cost_yj = "";
	form.day_cost_bhs = "";
	form.day_cost_se = "";
	form.day_cost_hsj = "";
	form.cost_ori = "";
	form.beizhu = "";
	form.cost_sta = "";
	form.cost_sl = "";
	form.cost_unit = "";
}

function openAdd() {
	dialogMode.value = "add";
	resetForm();
	dialogVisible.value = true;
}

function openEdit(row: CostRow) {
	dialogMode.value = "edit";
	resetForm();
	form.id = row.id ?? "";
	form.cus_code = row.cus_code ?? "";
	form.cost_code = row.cost_code ?? "";
	form.cost_date = (row.cost_data ?? "").slice(0, 10);
	form.day_cost_yj = row.day_cost_yj ?? "";
	form.day_cost_bhs = row.day_cost_bhs ?? "";
	form.day_cost_se = row.day_cost_se ?? "";
	form.day_cost_hsj = row.day_cost_hsj ?? "";
	form.cost_ori = row.cost_ori ?? "";
	form.beizhu = row.beizhu ?? "";
	form.cost_sta = row.cost_sta ?? "";
	form.cost_sl = row.cost_sl ?? "";
	form.cost_unit = row.cost_unit ?? "";
	dialogVisible.value = true;
}

async function submitForm() {
	const valid = await formRef.value?.validate().catch(() => false);
	if (!valid) return;
	dialogSaving.value = true;
	try {
		if (dialogMode.value === "add") {
			const payload: Record<string, any> = { ...form };
			delete payload.id;
			await addCostDetail(payload);
		} else {
			await updateCostDetail({ ...form });
		}
		ElMessage.success(dialogMode.value === "add" ? "费用明细录入成功" : "费用明细修改成功");
		dialogVisible.value = false;
		loadData();
	} catch (err: any) {
		ElMessage.error(err?.message || "操作失败");
	} finally {
		dialogSaving.value = false;
	}
}

async function removeRow(row: CostRow) {
	try {
		await ElMessageBox.confirm(`确定删除该费用明细吗？`, "提示", {
			type: "warning",
			confirmButtonText: "确定",
			cancelButtonText: "取消",
		});
	} catch {
		return;
	}
	try {
		await deleteCostDetail(row.id as string);
		ElMessage.success("删除成功");
		loadData();
	} catch (err: any) {
		ElMessage.error(err?.message || "删除失败");
	}
}

async function removeSelected() {
	if (selectedIds.value.length === 0) {
		ElMessage.warning("请先勾选要删除的记录");
		return;
	}
	try {
		await ElMessageBox.confirm(`确定删除选中的 ${selectedIds.value.length} 条费用明细吗？`, "提示", {
			type: "warning",
			confirmButtonText: "确定",
			cancelButtonText: "取消",
		});
	} catch {
		return;
	}
	try {
		await deleteCostDetails(selectedIds.value);
		ElMessage.success("批量删除成功");
		loadData();
	} catch (err: any) {
		ElMessage.error(err?.message || "批量删除失败");
	}
}

async function chargeSelected() {
	if (selectedIds.value.length === 0) {
		ElMessage.warning("请先勾选要收款的记录");
		return;
	}
	try {
		await chargeCostDetails(selectedIds.value);
		ElMessage.success("批量收款成功");
		loadData();
	} catch (err: any) {
		ElMessage.error(err?.message || "批量收款失败");
	}
}

async function dischargeSelected() {
	if (selectedIds.value.length === 0) {
		ElMessage.warning("请先勾选要取消收款的记录");
		return;
	}
	try {
		await dischargeCostDetails(selectedIds.value);
		ElMessage.success("批量取消收款成功");
		loadData();
	} catch (err: any) {
		ElMessage.error(err?.message || "批量取消收款失败");
	}
}

async function exportSelected() {
	if (selectedIds.value.length === 0) {
		ElMessage.warning("请先勾选要导出的记录");
		return;
	}
	try {
		const blob = await downloadCostDetails(selectedIds.value);
		saveBlob(blob, `费用明细_${Date.now()}.xlsx`);
		ElMessage.success("导出成功");
	} catch (err: any) {
		ElMessage.error(err?.message || "导出失败");
	}
}

function openImport() {
	importFile.value = null;
	importFileList.value = [];
	importVisible.value = true;
}

function handleImportChange(file: UploadFile) {
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
		await uploadCostDetails(importFile.value);
		ElMessage.success("导入成功");
		importVisible.value = false;
		loadData();
	} catch (err: any) {
		ElMessage.error(err?.message || "导入失败");
	} finally {
		importSaving.value = false;
	}
}

onMounted(() => {
	loadData();
	loadCostNames();
	loadCustomerNames();
});
</script>

<template>
	<section class="cost-detail-root">
		<h2>费用明细</h2>

		<el-form :inline="true" class="filter-bar">
			<el-form-item label="客户名称">
				<el-select
					v-model="searchForm.cusCode"
					placeholder="选择客户"
					clearable
					filterable
					style="width: 190px"
					@change="handleCustomerChange"
				>
					<el-option
						v-for="item in customerOptions"
						:key="item.code"
						:label="`${item.name}（${item.code}）`"
						:value="item.code"
					/>
				</el-select>
			</el-form-item>
			<el-form-item label="费用名称">
				<el-select
					v-model="searchForm.costCode"
					placeholder="选择费用名称"
					clearable
					filterable
					style="width: 180px"
					@change="handleCostNameChange"
				>
					<el-option
						v-for="item in costNameOptions"
						:key="item.code"
						:label="`${item.name}（${item.code}）`"
						:value="item.code"
					/>
				</el-select>
			</el-form-item>
			<el-form-item label="费用日期">
				<el-date-picker
					v-model="searchForm.dateRange"
					type="daterange"
					value-format="YYYY-MM-DD"
					start-placeholder="开始日期"
					end-placeholder="结束日期"
					style="width: 240px"
				/>
			</el-form-item>
			<el-form-item label="费用来源">
				<el-input v-model="searchForm.costOrigin" placeholder="费用来源" clearable style="width: 130px" />
			</el-form-item>
			<el-form-item label="备注">
				<el-input v-model="searchForm.note" placeholder="备注" clearable style="width: 130px" />
			</el-form-item>
			<el-form-item label="状态">
				<el-input v-model="searchForm.costState" placeholder="状态" clearable style="width: 110px" />
			</el-form-item>
			<el-form-item>
				<el-button type="primary" @click="handleSearch">查询</el-button>
				<el-button @click="handleReset">重置</el-button>
			</el-form-item>
		</el-form>

		<div class="tool-bar">
			<el-button type="success" @click="openAdd">录入</el-button>
			<el-button type="primary" @click="chargeSelected">批量收款</el-button>
			<el-button @click="dischargeSelected">批量取消收款</el-button>
			<el-button type="warning" @click="exportSelected">导出选中</el-button>
			<el-button @click="openImport">导入</el-button>
			<el-button type="danger" @click="removeSelected">批量删除</el-button>
			<span class="tip">收款 / 取消收款 / 导出需先勾选记录</span>
		</div>

		<el-table
			v-loading="loading"
			:data="rows"
			border
			stripe
			style="width: 100%"
			@selection-change="handleSelectionChange"
		>
			<el-table-column type="selection" width="45" />
			<el-table-column type="index" label="序号" width="55" />
			<el-table-column label="创建日期" width="160">
				<template #default="{ row }">{{ formatDateTime(row.create_date) }}</template>
			</el-table-column>
			<el-table-column prop="create_name" label="创建人" width="90" />
			<el-table-column prop="cus_code" label="客户编码" width="100" />
			<el-table-column label="客户名称" min-width="150" show-overflow-tooltip>
				<template #default="{ row }">{{ customerNameOf(row) }}</template>
			</el-table-column>
			<el-table-column prop="cost_code" label="费用编码" width="110" />
			<el-table-column label="费用名称" min-width="130" show-overflow-tooltip>
				<template #default="{ row }">{{ costNameOf(row) }}</template>
			</el-table-column>
			<el-table-column label="费用日期" width="120">
				<template #default="{ row }">{{ (row.cost_data ?? "").slice(0, 10) }}</template>
			</el-table-column>
			<el-table-column prop="day_cost_yj" label="原价" width="90" align="right" />
			<el-table-column prop="day_cost_bhs" label="不含税价" width="95" align="right" />
			<el-table-column prop="day_cost_se" label="税额" width="85" align="right" />
			<el-table-column prop="day_cost_hsj" label="含税价" width="95" align="right" />
			<el-table-column prop="cost_sl" label="数量" width="80" align="right" />
			<el-table-column prop="cost_unit" label="单位" width="70" />
			<el-table-column prop="cost_ori" label="费用来源" width="110" show-overflow-tooltip />
			<el-table-column prop="beizhu" label="备注" min-width="110" show-overflow-tooltip />
			<el-table-column prop="cost_sta" label="状态" width="80" />
			<el-table-column label="收款状态" width="95" align="center">
				<template #default="{ row }">
					<el-tag :type="row.cost_js === 'Y' ? 'success' : 'info'">
						{{ receiptText(row.cost_js) }}
					</el-tag>
				</template>
			</el-table-column>
			<el-table-column label="操作" width="120" fixed="right">
				<template #default="{ row }">
					<el-button link type="primary" @click="openEdit(row)">编辑</el-button>
					<el-button link type="danger" @click="removeRow(row)">删除</el-button>
				</template>
			</el-table-column>
		</el-table>

		<div class="pagination-bar">
			<el-pagination
				:current-page="pageIndex"
				:page-size="pageSize"
				:page-sizes="[10, 20, 50]"
				:total="total"
				layout="total, sizes, prev, pager, next, jumper"
				@current-change="handlePageChange"
				@size-change="handleSizeChange"
			/>
		</div>

		<el-dialog
			v-model="dialogVisible"
			:title="dialogMode === 'add' ? '录入费用明细' : '修改费用明细'"
			width="640px"
			:close-on-click-modal="false"
			destroy-on-close
		>
			<el-form ref="formRef" :model="form" label-width="95px">
				<el-row :gutter="12">
					<el-col :span="12">
						<el-form-item
							label="客户编码"
							prop="cus_code"
							:rules="[{ required: true, message: '请输入客户编码', trigger: 'change' }]"
						>
							<el-select
								v-model="form.cus_code"
								filterable
								allow-create
								default-first-option
								style="width: 100%"
							>
								<el-option
									v-for="item in customerOptions"
									:key="item.code"
									:label="`${item.name}（${item.code}）`"
									:value="item.code"
								/>
							</el-select>
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item
							label="费用名称"
							prop="cost_code"
							:rules="[{ required: true, message: '请选择费用名称', trigger: 'change' }]"
						>
							<el-select v-model="form.cost_code" filterable style="width: 100%">
								<el-option
									v-for="item in costNameOptions"
									:key="item.code"
									:label="`${item.name}（${item.code}）`"
									:value="item.code"
								/>
							</el-select>
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="费用日期" prop="cost_date">
							<el-date-picker
								v-model="form.cost_date"
								type="date"
								value-format="YYYY-MM-DD"
								placeholder="选择日期"
								style="width: 100%"
							/>
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="原价">
							<el-input v-model="form.day_cost_yj" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="不含税价">
							<el-input v-model="form.day_cost_bhs" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="税额">
							<el-input v-model="form.day_cost_se" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="含税价">
							<el-input v-model="form.day_cost_hsj" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="计费数量">
							<el-input v-model="form.cost_sl" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="数量单位">
							<el-input v-model="form.cost_unit" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="费用来源">
							<el-input v-model="form.cost_ori" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="状态">
							<el-input v-model="form.cost_sta" />
						</el-form-item>
					</el-col>
					<el-col :span="24">
						<el-form-item label="备注">
							<el-input v-model="form.beizhu" type="textarea" :rows="2" />
						</el-form-item>
					</el-col>
				</el-row>
			</el-form>
			<template #footer>
				<el-button @click="dialogVisible = false">取消</el-button>
				<el-button type="primary" :loading="dialogSaving" @click="submitForm">确定</el-button>
			</template>
		</el-dialog>

		<el-dialog v-model="importVisible" title="导入费用明细" width="460px" :close-on-click-modal="false">
			<el-upload
				v-model:file-list="importFileList"
				:auto-upload="false"
				:limit="1"
				accept=".xlsx,.xls"
				:on-change="handleImportChange"
				:on-remove="handleImportRemove"
				:on-exceed="() => ElMessage.warning('只能选择一个文件')"
			>
				<el-button type="primary">选择文件</el-button>
				<template #tip>
					<div class="el-upload__tip">请按导出模板格式导入（前 3 行为表头）</div>
				</template>
			</el-upload>
			<template #footer>
				<el-button @click="importVisible = false">取消</el-button>
				<el-button type="primary" :loading="importSaving" @click="submitImport">开始导入</el-button>
			</template>
		</el-dialog>
	</section>
</template>

<style lang="scss" scoped>
.cost-detail-root {
	width: 100%;

	.filter-bar {
		margin-top: 12px;
	}

	.tool-bar {
		display: flex;
		align-items: center;
		gap: 8px;
		margin: 4px 0 12px;
	}

	.tip {
		color: #909399;
		font-size: 13px;
	}

	.pagination-bar {
		display: flex;
		justify-content: flex-end;
		margin-top: 16px;
	}
}
</style>
