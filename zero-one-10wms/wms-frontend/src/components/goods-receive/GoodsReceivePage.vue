<script lang="ts" setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { UploadFile, UploadFiles } from "element-plus";
import {
	addGoodReceive,
	batchModifyGoodReceiveBin,
	batchModifyGoodReceiveProductionDate,
	batchShelfGoodReceive,
	deleteGoodReceive,
	exportGoodReceive,
	getGoodReceiveDetail,
	importGoodReceive,
	listGoodReceive,
	saveBlob,
	updateGoodReceive,
} from "@/apis/purchase/index";

interface Props {
	/** 页面标题（按钮、弹窗、提示文案使用） */
	title: string;
	/** 锁定的订单类型编码；传入后列表强制按该类型过滤（03=退货通知） */
	fixedOrderTypeCode?: string;
}

const props = withDefaults(defineProps<Props>(), {
	fixedOrderTypeCode: "",
});

interface ReceiveRow {
	id?: string;
	createDate?: string;
	imNoticeId?: string;
	cusCode?: string;
	cusName?: string;
	goodsId?: string;
	goodsName?: string;
	imQuat?: string;
	qmOkQuat?: string;
	goodsUnit?: string;
	proData?: string;
	binId?: string;
	tinId?: string;
	binSta?: string;
	goodsBatch?: string;
	recDeg?: string;
	itemText?: string;
	baseInGoodscount?: string;
	baseGoodscount?: string;
	baseOutGoodscount?: string;
}

const loading = ref(false);
const exporting = ref(false);
const rows = ref<ReceiveRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const selectedRows = ref<ReceiveRow[]>([]);

const query = reactive({
	imNoticeId: "",
	goodsId: "",
	binId: "",
	cusCode: "",
	binSta: "",
});

const dialogVisible = ref(false);
const dialogMode = ref<"add" | "edit">("add");
const dialogSaving = ref(false);
const formRef = ref();
const form = reactive({
	id: "",
	imNoticeId: "",
	goodsId: "",
	cusCode: "",
	binId: "",
	imQuat: "",
	proData: "",
	goodsBatch: "",
	recDeg: "",
	itemText: "",
	tinId: "",
	baseInGoodscount: "",
});

const detailVisible = ref(false);
const detailLoading = ref(false);
const detail = ref<ReceiveRow>({});

const binVisible = ref(false);
const binSaving = ref(false);
const newBinId = ref("");

const dateVisible = ref(false);
const dateSaving = ref(false);
const newProductionDate = ref("");

const importVisible = ref(false);
const importSaving = ref(false);
const importFile = ref<File | null>(null);
const importFileList = ref<UploadFiles>([]);

const selectedIds = computed(() => selectedRows.value.map((item) => item.id).filter((id): id is string => !!id));

function shelfStatus(value?: string) {
	if (value === "Y") return "已上架";
	if (value === "I") return "上架中";
	if (value === "N") return "未上架";
	return value ?? "-";
}

function shelfTagType(value?: string) {
	if (value === "Y") return "success";
	if (value === "I") return "warning";
	return "primary";
}

function formatDateTime(value?: string) {
	if (!value) return "";
	return String(value).replace("T", " ");
}

function loadData() {
	loading.value = true;
	const params: Record<string, unknown> = {
		pageIndex: pageIndex.value,
		pageSize: pageSize.value,
		...query,
	};
	if (props.fixedOrderTypeCode) {
		params.orderTypeCode = props.fixedOrderTypeCode;
	}
	listGoodReceive(
		params,
		(data: any) => {
			rows.value = data?.rows ?? [];
			total.value = data?.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error(`${props.title}数据加载失败`);
		},
	);
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	Object.assign(query, { imNoticeId: "", goodsId: "", binId: "", cusCode: "", binSta: "" });
	pageIndex.value = 1;
	loadData();
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

function handleSelectionChange(selection: ReceiveRow[]) {
	selectedRows.value = selection;
}

function resetForm() {
	Object.assign(form, {
		id: "",
		imNoticeId: "",
		goodsId: "",
		cusCode: "",
		binId: "",
		imQuat: "",
		proData: "",
		goodsBatch: "",
		recDeg: "",
		itemText: "",
		tinId: "",
		baseInGoodscount: "",
	});
}

function openAdd() {
	dialogMode.value = "add";
	resetForm();
	dialogVisible.value = true;
}

function openEdit(row: ReceiveRow) {
	dialogMode.value = "edit";
	Object.assign(form, {
		id: row.id ?? "",
		imNoticeId: row.imNoticeId ?? "",
		goodsId: row.goodsId ?? "",
		cusCode: row.cusCode ?? "",
		binId: row.binId ?? "",
		imQuat: row.qmOkQuat ?? row.imQuat ?? "",
		proData: row.proData ?? "",
		goodsBatch: row.goodsBatch ?? "",
		recDeg: row.recDeg ?? "",
		itemText: row.itemText ?? "",
		tinId: row.tinId ?? "",
		baseInGoodscount: row.baseInGoodscount ?? "",
	});
	dialogVisible.value = true;
}

function openDetail(row: ReceiveRow) {
	detailLoading.value = true;
	detailVisible.value = true;
	detail.value = row;
	getGoodReceiveDetail(
		row.id as string,
		(data: ReceiveRow) => {
			detail.value = data ?? row;
			detailLoading.value = false;
		},
		() => {
			detailLoading.value = false;
		},
	);
}

function submitForm() {
	formRef.value
		?.validate()
		.then(async () => {
			dialogSaving.value = true;
			try {
				const payload = {
					id: form.id || undefined,
					imNoticeId: form.imNoticeId,
					goodsId: form.goodsId,
					cusCode: form.cusCode,
					binId: form.binId,
					imQuat: form.imQuat,
					qmOkQuat: form.imQuat,
					proData: form.proData,
					goodsBatch: form.goodsBatch,
					recDeg: form.recDeg,
					itemText: form.itemText,
					tinId: form.tinId,
					baseInGoodscount: form.baseInGoodscount,
				};
				if (dialogMode.value === "add") {
					await addGoodReceive(payload);
				} else {
					await updateGoodReceive(payload);
				}
				ElMessage.success(dialogMode.value === "add" ? "录入成功" : "修改成功");
				dialogVisible.value = false;
				loadData();
			} catch (err: any) {
				ElMessage.error(err?.data?.message || err?.message || "保存失败");
			} finally {
				dialogSaving.value = false;
			}
		})
		.catch(() => undefined);
}

async function removeRow(row: ReceiveRow) {
	try {
		await ElMessageBox.confirm(`确定删除该${props.title}记录吗？`, "提示", {
			type: "warning",
			confirmButtonText: "确定",
			cancelButtonText: "取消",
		});
	} catch {
		return;
	}
	try {
		await deleteGoodReceive(row.id as string);
		ElMessage.success("删除成功");
		loadData();
	} catch (err: any) {
		ElMessage.error(err?.data?.message || err?.message || "删除失败");
	}
}

function requireSelection() {
	if (selectedIds.value.length === 0) {
		ElMessage.warning(`请先勾选要操作的${props.title}记录`);
		return false;
	}
	return true;
}

function openBinDialog() {
	if (!requireSelection()) return;
	newBinId.value = "";
	binVisible.value = true;
}

async function submitBin() {
	if (!newBinId.value) {
		ElMessage.warning("请输入新的储位");
		return;
	}
	binSaving.value = true;
	try {
		await batchModifyGoodReceiveBin({ ids: selectedIds.value, binId: newBinId.value });
		ElMessage.success("批量修改储位成功");
		binVisible.value = false;
		loadData();
	} catch (err: any) {
		ElMessage.error(err?.data?.message || err?.message || "批量修改储位失败");
	} finally {
		binSaving.value = false;
	}
}

function openDateDialog() {
	if (!requireSelection()) return;
	newProductionDate.value = "";
	dateVisible.value = true;
}

async function submitDate() {
	if (!newProductionDate.value) {
		ElMessage.warning("请选择新的生产日期");
		return;
	}
	dateSaving.value = true;
	try {
		await batchModifyGoodReceiveProductionDate({
			ids: selectedIds.value,
			newProductionDate: newProductionDate.value,
		});
		ElMessage.success("批量修改生产日期成功");
		dateVisible.value = false;
		loadData();
	} catch (err: any) {
		ElMessage.error(err?.data?.message || err?.message || "批量修改生产日期失败");
	} finally {
		dateSaving.value = false;
	}
}

async function shelfSelected() {
	if (!requireSelection()) return;
	try {
		await ElMessageBox.confirm(`确定将选中的 ${selectedIds.value.length} 条货物上架吗？`, "提示", {
			type: "warning",
			confirmButtonText: "确定",
			cancelButtonText: "取消",
		});
	} catch {
		return;
	}
	try {
		await batchShelfGoodReceive({ ids: selectedIds.value });
		ElMessage.success("上架成功");
		loadData();
	} catch (err: any) {
		ElMessage.error(err?.data?.message || err?.message || "上架失败");
	}
}

async function handleExport() {
	exporting.value = true;
	try {
		const params: Record<string, unknown> = { ...query };
		if (props.fixedOrderTypeCode) {
			params.orderTypeCode = props.fixedOrderTypeCode;
		}
		const blob = await exportGoodReceive(params);
		saveBlob(blob, `${props.title}_${Date.now()}.xlsx`);
		ElMessage.success("导出成功");
	} catch (err: any) {
		ElMessage.error(err?.message || "导出失败");
	} finally {
		exporting.value = false;
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
		await importGoodReceive(importFile.value);
		ElMessage.success("导入成功");
		importVisible.value = false;
		loadData();
	} catch (err: any) {
		ElMessage.error(err?.data?.message || err?.message || "导入失败");
	} finally {
		importSaving.value = false;
	}
}

onMounted(() => {
	loadData();
});
</script>

<template>
	<section class="goods-receive-root">
		<el-card shadow="never" class="query-card">
			<el-form :model="query" inline label-width="90px">
				<el-form-item label="到货通知单号">
					<el-input v-model="query.imNoticeId" clearable placeholder="请输入通知单号" style="width: 170px" />
				</el-form-item>
				<el-form-item label="商品编码">
					<el-input v-model="query.goodsId" clearable placeholder="请输入商品编码" style="width: 150px" />
				</el-form-item>
				<el-form-item label="客户编码">
					<el-input v-model="query.cusCode" clearable placeholder="请输入客户编码" style="width: 140px" />
				</el-form-item>
				<el-form-item label="储位">
					<el-input v-model="query.binId" clearable placeholder="请输入储位" style="width: 140px" />
				</el-form-item>
				<el-form-item label="上架状态">
					<el-select v-model="query.binSta" clearable placeholder="全部" style="width: 130px">
						<el-option label="未上架" value="N" />
						<el-option label="上架中" value="I" />
						<el-option label="已上架" value="Y" />
					</el-select>
				</el-form-item>
				<el-form-item>
					<el-button type="primary" @click="handleSearch">查询</el-button>
					<el-button @click="handleReset">重置</el-button>
				</el-form-item>
			</el-form>
		</el-card>

		<div class="tool-bar">
			<el-button type="primary" @click="openAdd">录入</el-button>
			<el-button @click="openBinDialog">批量修改储位</el-button>
			<el-button @click="openDateDialog">批量修改生产日期</el-button>
			<el-button type="success" @click="shelfSelected">上架货物</el-button>
			<el-button @click="openImport">导入数据</el-button>
			<el-button type="warning" :loading="exporting" @click="handleExport">导出数据</el-button>
			<el-button @click="loadData">刷新</el-button>
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
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="imNoticeId" label="到货通知单号" width="160" show-overflow-tooltip />
			<el-table-column prop="cusCode" label="客户编码" width="110" />
			<el-table-column prop="cusName" label="客户名称" min-width="150" show-overflow-tooltip />
			<el-table-column prop="goodsId" label="商品编码" width="120" show-overflow-tooltip />
			<el-table-column prop="goodsName" label="商品名称" min-width="140" show-overflow-tooltip />
			<el-table-column prop="imQuat" label="到货数量" width="100" align="right" />
			<el-table-column prop="qmOkQuat" label="收货数量" width="100" align="right" />
			<el-table-column prop="goodsUnit" label="单位" width="80" />
			<el-table-column prop="proData" label="生产日期" width="120" />
			<el-table-column prop="binId" label="储位" width="110" show-overflow-tooltip />
			<el-table-column prop="tinId" label="托盘" width="110" show-overflow-tooltip />
			<el-table-column label="上架状态" width="100">
				<template #default="{ row }">
					<el-tag :type="shelfTagType(row.binSta)">{{ shelfStatus(row.binSta) }}</el-tag>
				</template>
			</el-table-column>
			<el-table-column label="收货日期" width="170">
				<template #default="{ row }">{{ formatDateTime(row.createDate) }}</template>
			</el-table-column>
			<el-table-column label="操作" width="190" fixed="right">
				<template #default="{ row }">
					<el-button link type="primary" @click="openDetail(row)">详情</el-button>
					<el-button link type="primary" @click="openEdit(row)">编辑</el-button>
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

		<el-drawer v-model="detailVisible" :title="`${title}详情`" size="640px">
			<div v-loading="detailLoading">
				<el-descriptions :column="2" border>
					<el-descriptions-item label="通知单号">{{ detail.imNoticeId }}</el-descriptions-item>
					<el-descriptions-item label="上架状态">
						<el-tag :type="shelfTagType(detail.binSta)">{{ shelfStatus(detail.binSta) }}</el-tag>
					</el-descriptions-item>
					<el-descriptions-item label="客户编码">{{ detail.cusCode }}</el-descriptions-item>
					<el-descriptions-item label="客户名称">{{ detail.cusName }}</el-descriptions-item>
					<el-descriptions-item label="商品编码">{{ detail.goodsId }}</el-descriptions-item>
					<el-descriptions-item label="商品名称">{{ detail.goodsName }}</el-descriptions-item>
					<el-descriptions-item label="到货数量">{{ detail.imQuat }}</el-descriptions-item>
					<el-descriptions-item label="收货数量">{{ detail.qmOkQuat }}</el-descriptions-item>
					<el-descriptions-item label="单位">{{ detail.goodsUnit }}</el-descriptions-item>
					<el-descriptions-item label="批次">{{ detail.goodsBatch }}</el-descriptions-item>
					<el-descriptions-item label="生产日期">{{ detail.proData }}</el-descriptions-item>
					<el-descriptions-item label="储位">{{ detail.binId }}</el-descriptions-item>
					<el-descriptions-item label="托盘">{{ detail.tinId }}</el-descriptions-item>
					<el-descriptions-item label="收货温度">{{ detail.recDeg }}</el-descriptions-item>
					<el-descriptions-item label="入库数量">{{ detail.baseInGoodscount }}</el-descriptions-item>
					<el-descriptions-item label="备注">{{ detail.itemText }}</el-descriptions-item>
					<el-descriptions-item label="收货日期">{{ formatDateTime(detail.createDate) }}</el-descriptions-item>
				</el-descriptions>
			</div>
		</el-drawer>

		<el-dialog
			v-model="dialogVisible"
			:title="dialogMode === 'add' ? `录入${title}` : `修改${title}`"
			width="720px"
			:close-on-click-modal="false"
			destroy-on-close
		>
			<el-form ref="formRef" :model="form" label-width="100px">
				<div class="form-grid">
					<el-form-item
						label="通知单号"
						prop="imNoticeId"
						:rules="[{ required: true, message: '请输入通知单号', trigger: 'blur' }]"
					>
						<el-input v-model="form.imNoticeId" placeholder="请输入通知单号" />
					</el-form-item>
					<el-form-item
						label="商品编码"
						prop="goodsId"
						:rules="[{ required: true, message: '请输入商品编码', trigger: 'blur' }]"
					>
						<el-input v-model="form.goodsId" placeholder="请输入商品编码" />
					</el-form-item>
					<el-form-item label="客户编码">
						<el-input v-model="form.cusCode" placeholder="请输入客户编码" />
					</el-form-item>
					<el-form-item label="储位">
						<el-input v-model="form.binId" placeholder="请输入储位" />
					</el-form-item>
					<el-form-item
						label="收货数量"
						prop="imQuat"
						:rules="[{ required: true, message: '请输入收货数量', trigger: 'blur' }]"
					>
						<el-input v-model="form.imQuat" placeholder="请输入收货数量" />
					</el-form-item>
					<el-form-item label="入库数量">
						<el-input v-model="form.baseInGoodscount" placeholder="默认等于收货数量" />
					</el-form-item>
					<el-form-item label="生产日期">
						<el-date-picker
							v-model="form.proData"
							type="date"
							value-format="YYYY-MM-DD"
							placeholder="选择生产日期"
							style="width: 100%"
						/>
					</el-form-item>
					<el-form-item label="批次">
						<el-input v-model="form.goodsBatch" placeholder="请输入批次" />
					</el-form-item>
					<el-form-item label="托盘">
						<el-input v-model="form.tinId" placeholder="请输入托盘" />
					</el-form-item>
					<el-form-item label="收货温度">
						<el-input v-model="form.recDeg" placeholder="如 25" />
					</el-form-item>
					<el-form-item label="备注" class="span-2">
						<el-input v-model="form.itemText" type="textarea" :rows="2" placeholder="请输入备注" />
					</el-form-item>
				</div>
			</el-form>
			<template #footer>
				<el-button @click="dialogVisible = false">取消</el-button>
				<el-button type="primary" :loading="dialogSaving" @click="submitForm">保存</el-button>
			</template>
		</el-dialog>

		<el-dialog v-model="binVisible" title="批量修改储位" width="420px" :close-on-click-modal="false">
			<el-form label-width="90px">
				<el-form-item label="新储位">
					<el-input v-model="newBinId" placeholder="请输入新的储位" />
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="binVisible = false">取消</el-button>
				<el-button type="primary" :loading="binSaving" @click="submitBin">确定</el-button>
			</template>
		</el-dialog>

		<el-dialog v-model="dateVisible" title="批量修改生产日期" width="420px" :close-on-click-modal="false">
			<el-form label-width="100px">
				<el-form-item label="生产日期">
					<el-date-picker
						v-model="newProductionDate"
						type="date"
						value-format="YYYY-MM-DD"
						placeholder="选择生产日期"
						style="width: 100%"
					/>
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="dateVisible = false">取消</el-button>
				<el-button type="primary" :loading="dateSaving" @click="submitDate">确定</el-button>
			</template>
		</el-dialog>

		<el-dialog v-model="importVisible" :title="`导入${title}`" width="460px" :close-on-click-modal="false">
			<el-upload
				v-model:file-list="importFileList"
				:auto-upload="false"
				:limit="1"
				accept=".xlsx,.xls"
				:on-change="handleImportChange"
				:on-remove="handleImportRemove"
			>
				<el-button type="primary">选择文件</el-button>
				<template #tip>
					<div class="el-upload__tip">
						列：通知单号、商品编码、客户编码、储位、数量、生产日期、批次、收货温度、备注、托盘、入库数量
					</div>
				</template>
			</el-upload>
			<template #footer>
				<el-button @click="importVisible = false">取消</el-button>
				<el-button type="primary" :loading="importSaving" @click="submitImport">导入</el-button>
			</template>
		</el-dialog>
	</section>
</template>

<style lang="scss" scoped>
.goods-receive-root {
	width: 100%;

	.query-card {
		margin-bottom: 12px;
	}

	.tool-bar {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 10px;
		margin-bottom: 12px;
	}

	.form-grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		column-gap: 24px;
	}

	.span-2 {
		grid-column: span 2;
	}
}
</style>
