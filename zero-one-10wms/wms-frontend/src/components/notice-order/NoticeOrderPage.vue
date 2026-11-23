<script lang="ts" setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
	confirmImportNotice,
	deleteImportNotice,
	exportImportNotice,
	getImportNoticeDetail,
	insertImportNotice,
	listCustomerOptions,
	listGoodsOptions,
	listImportNotices,
	listOrderTypeOptions,
	listPlatformOptions,
	listSupplierOptions,
	listWarehouseOptions,
	previewBlob,
	printImportNotice,
	saveBlob,
	updateImportNotice,
	uploadImportNoticeAttachment,
} from "@/apis/purchase/index";

interface Props {
	/** 页面标题（按钮、弹窗、提示文案使用） */
	title: string;
	/** 锁定的订单类型编码；传入后列表强制按该类型过滤，表单中不可修改 */
	fixedOrderTypeCode?: string;
	/** 是否为简化版：隐藏客户/供应商/月台/仓库等扩展字段，仅保留核心收货信息 */
	simple?: boolean;
	/** 是否隐藏打印/导出下拉（简化版默认隐藏） */
	hidePrintExport?: boolean;
	/** 是否隐藏完成按钮 */
	hideComplete?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
	fixedOrderTypeCode: "",
	simple: false,
	hidePrintExport: false,
	hideComplete: false,
});

const isSimple = computed(() => props.simple);
const lockOrderType = computed(() => !!props.fixedOrderTypeCode);

interface NoticeRow {
	noticeId?: string;
	cusCode?: string;
	cusName?: string;
	supCode?: string;
	supName?: string;
	orderTypeCode?: string;
	imData?: string;
	imCarNo?: string;
	imCarDri?: string;
	imSta?: string;
	imBeiZhu?: string;
	createName?: string;
	createDate?: string;
}

interface NoticeItem {
	id?: string;
	goodsCode?: string;
	goodsName?: string;
	goodsCount?: string;
	goodsUnit?: string;
	binPlan?: string;
	binPre?: string;
	goodsBatch?: string;
	goodsPrdData?: string;
	tinId?: string;
}

interface OptionRow {
	code: string;
	name: string;
	raw: any;
}

const loading = ref(false);
const rows = ref<NoticeRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);

const query = reactive({
	noticeId: "",
	cusCode: "",
	supName: "",
	orderTypeCode: "",
	imSta: "",
	dateRange: [] as string[],
});

const orderTypes = ref<OptionRow[]>([]);
const customers = ref<OptionRow[]>([]);
const suppliers = ref<OptionRow[]>([]);
const goodsList = ref<OptionRow[]>([]);
const platforms = ref<OptionRow[]>([]);
const warehouses = ref<OptionRow[]>([]);

const dialogVisible = ref(false);
const dialogMode = ref<"add" | "edit">("add");
const dialogSaving = ref(false);
const formRef = ref();
const form = reactive({
	noticeId: "",
	cusCode: "",
	supCode: "",
	supName: "",
	orderTypeCode: "",
	imData: "",
	imCusCode: "",
	imCarNo: "",
	imCarMobile: "",
	imCarDri: "",
	platformCode: "",
	storeCode: "",
	areaCode: "",
	imBeiZhu: "",
	imSta: "计划中",
	fuJian: "",
	items: [] as NoticeItem[],
});

const detailVisible = ref(false);
const detailLoading = ref(false);
const detail = ref<any>({});

const fileInput = ref<HTMLInputElement>();
const uploading = ref(false);

const detailItems = computed<NoticeItem[]>(() => detail.value?.importNoticeItemDTOList ?? []);
const formItems = computed<NoticeItem[]>(() => form.items);

const formOrderTypeOptions = computed(() => {
	if (!props.fixedOrderTypeCode) return orderTypes.value;
	return orderTypes.value.filter((item) => item.code === props.fixedOrderTypeCode);
});

function errText(err: any, fallback: string) {
	return err?.data?.message || err?.message || err?.response?.data?.message || fallback;
}

function extractRows(payload: any): any[] {
	if (!payload) return [];
	if (Array.isArray(payload)) return payload;
	if (Array.isArray(payload.rows)) return payload.rows;
	if (Array.isArray(payload.data)) return payload.data;
	return [];
}

function formatDateTime(value?: string) {
	if (!value) return "";
	return String(value).replace("T", " ");
}

function statusTagType(status?: string) {
	if (status === "已完成") return "success";
	if (status === "收货中") return "warning";
	if (status === "已取消") return "info";
	return "primary";
}

function orderTypeName(code?: string) {
	return orderTypes.value.find((item) => item.code === code)?.name || code || "";
}

function customerName(code?: string) {
	return customers.value.find((item) => item.code === code)?.name || code || "";
}

function platformName(code?: string) {
	return platforms.value.find((item) => item.code === code)?.name || code || "";
}

function warehouseName(code?: string) {
	return warehouses.value.find((item) => item.code === code)?.name || code || "";
}

function goodsOption(code?: string) {
	return goodsList.value.find((item) => item.code === code)?.raw;
}

function normalizeOptions(payload: any, codeKeys: string[], nameKeys: string[]): OptionRow[] {
	return extractRows(payload)
		.map((row: any) => {
			const code = codeKeys
				.map((key) => row?.[key])
				.find((value) => value !== undefined && value !== null && value !== "");
			const name = nameKeys
				.map((key) => row?.[key])
				.find((value) => value !== undefined && value !== null && value !== "");
			return { code: String(code ?? ""), name: String(name ?? code ?? ""), raw: row };
		})
		.filter((item) => item.code);
}

function loadOptions() {
	listOrderTypeOptions((data: any) => {
		orderTypes.value = normalizeOptions(
			data,
			["order_type_code", "orderTypeCode"],
			["order_type_name", "orderTypeName"],
		);
	});
	if (isSimple.value) return;
	listCustomerOptions((data: any) => {
		customers.value = normalizeOptions(data, ["keHuBianMa", "kehuBianMa", "cusCode"], ["zhongWenQch"]);
	});
	listSupplierOptions((data: any) => {
		suppliers.value = normalizeOptions(data, ["gysBianMa", "supCode"], ["zhongWenQch", "supName"]);
	});
	listGoodsOptions((data: any) => {
		goodsList.value = normalizeOptions(data, ["shpBianMa", "goodsCode"], ["shpMingCheng", "goodsName"]);
	});
	listPlatformOptions((data: any) => {
		platforms.value = normalizeOptions(data, ["platform_code", "platformCode"], ["platform_name", "platformName"]);
	});
	listWarehouseOptions((data: any) => {
		warehouses.value = normalizeOptions(data, ["store_code", "storeCode"], ["store_name", "storeName"]);
	});
}

function loadData() {
	loading.value = true;
	const params: Record<string, unknown> = {
		pageIndex: pageIndex.value,
		pageSize: pageSize.value,
		noticeId: query.noticeId,
		cusCode: query.cusCode,
		supName: isSimple.value ? "" : query.supName,
		orderTypeCode: props.fixedOrderTypeCode || query.orderTypeCode,
		imSta: query.imSta,
	};
	if (!isSimple.value && query.dateRange?.length === 2) {
		params.imDataBegin = query.dateRange[0];
		params.imDataEnd = query.dateRange[1];
	}
	listImportNotices(
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
	query.noticeId = "";
	query.cusCode = "";
	query.supName = "";
	query.orderTypeCode = "";
	query.imSta = "";
	query.dateRange = [];
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

function resetForm() {
	Object.assign(form, {
		noticeId: "",
		cusCode: "",
		supCode: "",
		supName: "",
		orderTypeCode: props.fixedOrderTypeCode,
		imData: "",
		imCusCode: "",
		imCarNo: "",
		imCarMobile: "",
		imCarDri: "",
		platformCode: "",
		storeCode: "",
		areaCode: "",
		imBeiZhu: "",
		imSta: "计划中",
		fuJian: "",
		items: [],
	});
}

function openAdd() {
	dialogMode.value = "add";
	resetForm();
	addItem();
	dialogVisible.value = true;
}

async function openEdit(row: NoticeRow) {
	dialogMode.value = "edit";
	resetForm();
	try {
		const data: any = await new Promise((resolve, reject) => {
			getImportNoticeDetail(row.noticeId as string, resolve, () => reject(new Error(`加载${props.title}详情失败`)));
		});
		Object.assign(form, {
			noticeId: data.noticeId ?? "",
			cusCode: data.cusCode ?? "",
			supCode: data.supCode ?? "",
			supName: data.supName ?? "",
			orderTypeCode: props.fixedOrderTypeCode || (data.orderTypeCode ?? ""),
			imData: formatDateTime(data.imData),
			imCusCode: data.imCusCode ?? "",
			imCarNo: data.imCarNo ?? "",
			imCarMobile: data.imCarMobile ?? "",
			imCarDri: data.imCarDri ?? "",
			platformCode: data.platformCode ?? "",
			storeCode: data.storeCode ?? "",
			areaCode: data.areaCode ?? "",
			imBeiZhu: data.imBeiZhu ?? "",
			imSta: data.imSta ?? "计划中",
			fuJian: data.fuJian ?? "",
			items: (data.importNoticeItemDTOList ?? []).map((item: NoticeItem) => ({
				...item,
				goodsPrdData: formatDateTime(item.goodsPrdData),
			})),
		});
		if (form.items.length === 0) addItem();
		dialogVisible.value = true;
	} catch (err: any) {
		ElMessage.error(errText(err, `加载${props.title}详情失败`));
	}
}

function openDetail(row: NoticeRow) {
	detailLoading.value = true;
	detailVisible.value = true;
	detail.value = {};
	getImportNoticeDetail(
		row.noticeId as string,
		(data: any) => {
			detail.value = data ?? {};
			detailLoading.value = false;
		},
		() => {
			detailLoading.value = false;
			ElMessage.error(`加载${props.title}详情失败`);
		},
	);
}

function addItem() {
	form.items.push({
		id: "",
		goodsCode: "",
		goodsName: "",
		goodsCount: "",
		goodsUnit: "",
		binPlan: "",
		binPre: "N",
		goodsBatch: "",
		goodsPrdData: "",
		tinId: "",
	});
}

function removeItem(index: number) {
	form.items.splice(index, 1);
}

function onGoodsChange(item: NoticeItem) {
	const goods = goodsOption(item.goodsCode);
	if (!goods) return;
	item.goodsName = goods.shpMingCheng ?? item.goodsName;
	item.goodsUnit = goods.shlDanWei ?? item.goodsUnit;
}

function onSupplierChange(code: string) {
	const supplier = suppliers.value.find((item) => item.code === code);
	form.supName = supplier?.name ?? "";
}

function submitForm() {
	formRef.value
		?.validate()
		.then(async () => {
			if (!form.items.length) {
				ElMessage.warning("请至少录入一条货品明细");
				return;
			}
			dialogSaving.value = true;
			try {
				const payload = {
					noticeId: form.noticeId,
					cusCode: form.cusCode,
					supCode: form.supCode,
					supName: form.supName,
					orderTypeCode: props.fixedOrderTypeCode || form.orderTypeCode,
					imData: form.imData || null,
					imCusCode: form.imCusCode,
					imCarNo: form.imCarNo,
					imCarMobile: form.imCarMobile,
					imCarDri: form.imCarDri,
					platformCode: form.platformCode,
					storeCode: form.storeCode,
					areaCode: form.areaCode,
					imBeiZhu: form.imBeiZhu,
					imSta: form.imSta,
					fuJian: form.fuJian,
					importNoticeItemDTOList: form.items.map((item) => ({
						id: item.id || undefined,
						goodsCode: item.goodsCode,
						goodsCount: item.goodsCount,
						binPlan: item.binPlan,
						binPre: item.binPre,
						goodsBatch: item.goodsBatch,
						goodsPrdData: item.goodsPrdData || null,
						tinId: item.tinId,
					})),
				};
				if (dialogMode.value === "add") {
					await insertImportNotice(payload);
				} else {
					await updateImportNotice(payload);
				}
				ElMessage.success(dialogMode.value === "add" ? "录入成功" : "修改成功");
				dialogVisible.value = false;
				loadData();
			} catch (err: any) {
				ElMessage.error(errText(err, "保存失败"));
			} finally {
				dialogSaving.value = false;
			}
		})
		.catch(() => undefined);
}

async function completeRow(row: NoticeRow) {
	try {
		await ElMessageBox.confirm(`确定完成通知单 ${row.noticeId} 吗？`, "提示", {
			type: "warning",
			confirmButtonText: "确定",
			cancelButtonText: "取消",
		});
	} catch {
		return;
	}
	try {
		await confirmImportNotice(row.noticeId as string);
		ElMessage.success(`${props.title}已完成`);
		loadData();
	} catch (err: any) {
		ElMessage.error(errText(err, "完成失败"));
	}
}

async function removeRow(row: NoticeRow) {
	try {
		await ElMessageBox.confirm(`确定删除通知单 ${row.noticeId} 吗？`, "提示", {
			type: "warning",
			confirmButtonText: "确定",
			cancelButtonText: "取消",
		});
	} catch {
		return;
	}
	try {
		await deleteImportNotice(row.noticeId as string);
		ElMessage.success("删除成功");
		loadData();
	} catch (err: any) {
		ElMessage.error(errText(err, "删除失败"));
	}
}

const printNames: Record<string, string> = {
	notice: "通知单",
	goods: "货品信息",
	inbound: "入库单",
};

const exportNames: Record<string, string> = {
	acceptance: "验收单",
	inbound: "入库单",
	"goods-id": "货品ID",
	"tin-label": "托盘标签",
};

async function handleRowCommand(command: string, row: NoticeRow) {
	if (command.startsWith("print-")) {
		const kind = command.replace("print-", "");
		try {
			const blob = await printImportNotice(kind, row.noticeId as string);
			previewBlob(blob, `${row.noticeId}_${printNames[kind] ?? "打印"}.pdf`);
		} catch (err: any) {
			ElMessage.error(errText(err, `打印${printNames[kind] ?? ""}失败`));
		}
		return;
	}
	if (command.startsWith("export-")) {
		const kind = command.replace("export-", "");
		try {
			const blob = await exportImportNotice(kind, row.noticeId as string);
			saveBlob(blob, `${row.noticeId}_${exportNames[kind] ?? "导出"}.xlsx`);
			ElMessage.success("导出成功");
		} catch (err: any) {
			ElMessage.error(errText(err, `导出${exportNames[kind] ?? ""}失败`));
		}
	}
}

function triggerUpload() {
	fileInput.value?.click();
}

async function handleFileChange(event: Event) {
	const target = event.target as HTMLInputElement;
	const file = target.files?.[0];
	if (!file) return;
	uploading.value = true;
	try {
		const res: any = await uploadImportNoticeAttachment(file);
		form.fuJian = res?.data ?? "";
		ElMessage.success("附件上传成功");
	} catch (err: any) {
		ElMessage.error(errText(err, "附件上传失败"));
	} finally {
		uploading.value = false;
		target.value = "";
	}
}

onMounted(() => {
	loadOptions();
	loadData();
});
</script>

<template>
	<section class="notice-order-root">
		<el-card shadow="never" class="query-card">
			<el-form :model="query" inline label-width="90px">
				<el-form-item label="通知单号">
					<el-input v-model="query.noticeId" clearable placeholder="请输入通知单号" style="width: 180px" />
				</el-form-item>
				<el-form-item label="客户编码">
					<el-input v-model="query.cusCode" clearable placeholder="请输入客户编码" style="width: 150px" />
				</el-form-item>
				<el-form-item v-if="!isSimple" label="供应商">
					<el-input v-model="query.supName" clearable placeholder="请输入供应商名称" style="width: 170px" />
				</el-form-item>
				<el-form-item v-if="!lockOrderType" label="订单类型">
					<el-select v-model="query.orderTypeCode" clearable placeholder="全部" style="width: 150px">
						<el-option v-for="item in orderTypes" :key="item.code" :label="item.name" :value="item.code" />
					</el-select>
				</el-form-item>
				<el-form-item label="单据状态">
					<el-select v-model="query.imSta" clearable placeholder="全部" style="width: 130px">
						<el-option label="计划中" value="计划中" />
						<el-option label="收货中" value="收货中" />
						<el-option label="已完成" value="已完成" />
					</el-select>
				</el-form-item>
				<el-form-item v-if="!isSimple" label="到货时间">
					<el-date-picker
						v-model="query.dateRange"
						type="datetimerange"
						value-format="YYYY-MM-DD HH:mm:ss"
						start-placeholder="开始时间"
						end-placeholder="结束时间"
						style="width: 340px"
					/>
				</el-form-item>
				<el-form-item>
					<el-button type="primary" @click="handleSearch">查询</el-button>
					<el-button @click="handleReset">重置</el-button>
				</el-form-item>
			</el-form>
		</el-card>

		<div class="tool-bar">
			<el-button type="primary" @click="openAdd">录入{{ title }}</el-button>
			<el-button @click="loadData">刷新</el-button>
			<span class="tip">支持录入、修改、删除、详情{{ !hideComplete ? "、完成" : "" }}{{ !hidePrintExport ? "、打印与导出" : "" }}</span>
		</div>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%">
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="noticeId" label="通知单号" width="170" show-overflow-tooltip />
			<el-table-column label="客户" min-width="170" show-overflow-tooltip>
				<template #default="{ row }">{{ row.cusName || customerName(row.cusCode) }}</template>
			</el-table-column>
			<el-table-column v-if="!isSimple" prop="supName" label="供应商" min-width="160" show-overflow-tooltip />
			<el-table-column label="订单类型" width="120">
				<template #default="{ row }">{{ orderTypeName(row.orderTypeCode) }}</template>
			</el-table-column>
			<el-table-column label="预计到货时间" width="170">
				<template #default="{ row }">{{ formatDateTime(row.imData) }}</template>
			</el-table-column>
			<el-table-column prop="imCarNo" label="车号" width="110" />
			<el-table-column prop="imCarDri" label="司机" width="90" />
			<el-table-column label="单据状态" width="100">
				<template #default="{ row }">
					<el-tag :type="statusTagType(row.imSta)">{{ row.imSta || "计划中" }}</el-tag>
				</template>
			</el-table-column>
			<el-table-column prop="createName" label="创建人" width="100" />
			<el-table-column label="创建时间" width="170">
				<template #default="{ row }">{{ formatDateTime(row.createDate) }}</template>
			</el-table-column>
			<el-table-column label="操作" :width="!hidePrintExport && !hideComplete ? 330 : 250" fixed="right">
				<template #default="{ row }">
					<el-button link type="primary" @click="openDetail(row)">详情</el-button>
					<el-button link type="primary" @click="openEdit(row)">编辑</el-button>
					<el-button v-if="!hideComplete" link type="success" @click="completeRow(row)">完成</el-button>
					<el-button link type="danger" @click="removeRow(row)">删除</el-button>
					<el-dropdown v-if="!hidePrintExport" trigger="click" @command="(cmd) => handleRowCommand(cmd, row)">
						<el-button link type="primary">打印/导出</el-button>
						<template #dropdown>
							<el-dropdown-menu>
								<el-dropdown-item command="print-notice">打印通知单</el-dropdown-item>
								<el-dropdown-item command="print-goods">打印货品信息</el-dropdown-item>
								<el-dropdown-item command="print-inbound">打印入库单</el-dropdown-item>
								<el-dropdown-item divided command="export-acceptance">导出验收单</el-dropdown-item>
								<el-dropdown-item command="export-inbound">导出入库单</el-dropdown-item>
								<el-dropdown-item command="export-goods-id">导出货品ID</el-dropdown-item>
								<el-dropdown-item command="export-tin-label">导出托盘标签</el-dropdown-item>
							</el-dropdown-menu>
						</template>
					</el-dropdown>
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

		<el-drawer v-model="detailVisible" :title="`${title}详情`" size="760px">
			<div v-loading="detailLoading">
				<el-descriptions :column="2" border>
					<el-descriptions-item label="通知单号">{{ detail.noticeId }}</el-descriptions-item>
					<el-descriptions-item label="单据状态">
						<el-tag :type="statusTagType(detail.imSta)">{{ detail.imSta || "计划中" }}</el-tag>
					</el-descriptions-item>
					<el-descriptions-item label="客户">{{ customerName(detail.cusCode) }}</el-descriptions-item>
					<el-descriptions-item label="客户订单号">{{ detail.imCusCode }}</el-descriptions-item>
					<el-descriptions-item v-if="!isSimple" label="供应商">{{ detail.supName }}</el-descriptions-item>
					<el-descriptions-item label="订单类型">{{ orderTypeName(detail.orderTypeCode) }}</el-descriptions-item>
					<el-descriptions-item label="预计到货时间">{{ formatDateTime(detail.imData) }}</el-descriptions-item>
					<el-descriptions-item v-if="!isSimple" label="月台">{{ platformName(detail.platformCode) }}</el-descriptions-item>
					<el-descriptions-item v-if="!isSimple" label="仓库">{{ warehouseName(detail.storeCode) }}</el-descriptions-item>
					<el-descriptions-item v-if="!isSimple" label="库区">{{ detail.areaCode }}</el-descriptions-item>
					<el-descriptions-item label="车号">{{ detail.imCarNo }}</el-descriptions-item>
					<el-descriptions-item label="司机">{{ detail.imCarDri }}</el-descriptions-item>
					<el-descriptions-item label="司机电话">{{ detail.imCarMobile }}</el-descriptions-item>
					<el-descriptions-item label="创建人">{{ detail.createName }}</el-descriptions-item>
					<el-descriptions-item label="创建时间">{{ formatDateTime(detail.createDate) }}</el-descriptions-item>
					<el-descriptions-item label="备注">{{ detail.imBeiZhu }}</el-descriptions-item>
					<el-descriptions-item label="附件">
						<el-link v-if="detail.fuJian" :href="detail.fuJian" target="_blank" type="primary"> 查看附件 </el-link>
						<span v-else>无</span>
					</el-descriptions-item>
				</el-descriptions>

				<h4 class="section-title">货品明细</h4>
				<el-table :data="detailItems" border stripe style="width: 100%">
					<el-table-column type="index" label="序号" width="60" />
					<el-table-column prop="goodsCode" label="商品编码" width="130" show-overflow-tooltip />
					<el-table-column prop="goodsName" label="商品名称" min-width="150" show-overflow-tooltip />
					<el-table-column prop="goodsCount" label="数量" width="90" align="right" />
					<el-table-column prop="goodsUnit" label="单位" width="80" />
					<el-table-column prop="binPlan" label="计划库位" width="110" show-overflow-tooltip />
					<el-table-column prop="goodsBatch" label="批次" width="110" show-overflow-tooltip />
					<el-table-column label="生产日期" width="150">
						<template #default="{ row }">{{ formatDateTime(row.goodsPrdData) }}</template>
					</el-table-column>
					<el-table-column prop="tinId" label="托盘" width="100" />
				</el-table>
			</div>
		</el-drawer>

		<el-dialog
			v-model="dialogVisible"
			:title="dialogMode === 'add' ? `录入${title}` : `修改${title}`"
			width="1080px"
			:close-on-click-modal="false"
			destroy-on-close
		>
			<el-form ref="formRef" :model="form" label-width="100px">
				<div class="form-grid">
					<el-form-item
						label="客户"
						prop="cusCode"
						:rules="[{ required: true, message: '请选择客户', trigger: 'change' }]"
					>
						<el-select
							v-if="!isSimple"
							v-model="form.cusCode"
							filterable
							placeholder="请选择客户"
							style="width: 100%"
						>
							<el-option
								v-for="item in customers"
								:key="item.code"
								:label="`${item.code} ${item.name}`"
								:value="item.code"
							/>
						</el-select>
						<el-input v-else v-model="form.cusCode" placeholder="请输入客户编码" />
					</el-form-item>
					<el-form-item v-if="!isSimple" label="供应商" prop="supCode">
						<el-select
							v-model="form.supCode"
							filterable
							clearable
							placeholder="请选择供应商"
							style="width: 100%"
							@change="onSupplierChange"
						>
							<el-option
								v-for="item in suppliers"
								:key="item.code"
								:label="`${item.code} ${item.name}`"
								:value="item.code"
							/>
						</el-select>
					</el-form-item>
					<el-form-item
						label="订单类型"
						prop="orderTypeCode"
						:rules="[{ required: true, message: '请选择订单类型', trigger: 'change' }]"
					>
						<el-select
							v-model="form.orderTypeCode"
							:disabled="lockOrderType"
							filterable
							placeholder="请选择订单类型"
							style="width: 100%"
						>
							<el-option v-for="item in formOrderTypeOptions" :key="item.code" :label="item.name" :value="item.code" />
						</el-select>
					</el-form-item>
					<el-form-item
						label="预计到货"
						prop="imData"
						:rules="[{ required: true, message: '请选择预计到货时间', trigger: 'change' }]"
					>
						<el-date-picker
							v-model="form.imData"
							type="datetime"
							value-format="YYYY-MM-DD HH:mm:ss"
							placeholder="选择预计到货时间"
							style="width: 100%"
						/>
					</el-form-item>
					<el-form-item label="客户订单号">
						<el-input v-model="form.imCusCode" placeholder="请输入客户订单号" />
					</el-form-item>
					<el-form-item label="车号">
						<el-input v-model="form.imCarNo" placeholder="请输入车号" />
					</el-form-item>
					<el-form-item label="司机">
						<el-input v-model="form.imCarDri" placeholder="请输入司机姓名" />
					</el-form-item>
					<el-form-item label="司机电话">
						<el-input v-model="form.imCarMobile" placeholder="请输入司机电话" />
					</el-form-item>
					<el-form-item v-if="!isSimple" label="月台">
						<el-select
							v-model="form.platformCode"
							clearable
							filterable
							allow-create
							default-first-option
							placeholder="请选择或输入月台编码"
							style="width: 100%"
						>
							<el-option v-for="item in platforms" :key="item.code" :label="item.name" :value="item.code" />
						</el-select>
					</el-form-item>
					<el-form-item v-if="!isSimple" label="仓库">
						<el-select v-model="form.storeCode" clearable filterable placeholder="请选择仓库" style="width: 100%">
							<el-option v-for="item in warehouses" :key="item.code" :label="item.name" :value="item.code" />
						</el-select>
					</el-form-item>
					<el-form-item v-if="!isSimple" label="库区">
						<el-input v-model="form.areaCode" placeholder="请输入预约库区" />
					</el-form-item>
					<el-form-item label="单据状态">
						<el-select v-model="form.imSta" style="width: 100%">
							<el-option label="计划中" value="计划中" />
							<el-option label="收货中" value="收货中" />
							<el-option label="已完成" value="已完成" />
						</el-select>
					</el-form-item>
					<el-form-item v-if="!isSimple" label="附件">
						<div class="attachment-row">
							<el-button :loading="uploading" @click="triggerUpload">上传附件</el-button>
							<el-link v-if="form.fuJian" :href="form.fuJian" target="_blank" type="primary">查看附件</el-link>
							<span v-else class="tip">未上传</span>
						</div>
						<input ref="fileInput" type="file" hidden @change="handleFileChange" />
					</el-form-item>
					<el-form-item label="备注" class="span-2">
						<el-input v-model="form.imBeiZhu" type="textarea" :rows="2" placeholder="请输入备注" />
					</el-form-item>
				</div>
			</el-form>

			<div class="items-header">
				<h4>货品明细</h4>
				<el-button type="primary" plain size="small" @click="addItem">添加明细</el-button>
			</div>
			<el-table :data="formItems" border stripe style="width: 100%">
				<el-table-column type="index" label="序号" width="55" />
				<el-table-column label="商品" width="260">
					<template #default="{ row }">
						<el-select
							v-if="!isSimple"
							v-model="row.goodsCode"
							filterable
							placeholder="选择商品"
							style="width: 100%"
							@change="onGoodsChange(row)"
						>
							<el-option
								v-for="item in goodsList"
								:key="item.code"
								:label="`${item.code} ${item.name}`"
								:value="item.code"
							/>
						</el-select>
						<el-input v-else v-model="row.goodsCode" placeholder="商品编码" />
					</template>
				</el-table-column>
				<el-table-column label="商品名称" min-width="140">
					<template #default="{ row }">
						<el-input v-model="row.goodsName" placeholder="自动带出" />
					</template>
				</el-table-column>
				<el-table-column label="数量" width="110">
					<template #default="{ row }">
						<el-input v-model="row.goodsCount" placeholder="数量" />
					</template>
				</el-table-column>
				<el-table-column label="单位" width="90">
					<template #default="{ row }">
						<el-input v-model="row.goodsUnit" placeholder="单位" />
					</template>
				</el-table-column>
				<el-table-column label="计划库位" width="130">
					<template #default="{ row }">
						<el-input v-model="row.binPlan" placeholder="计划库位" />
					</template>
				</el-table-column>
				<el-table-column label="收货完成" width="100">
					<template #default="{ row }">
						<el-select v-model="row.binPre" style="width: 100%">
							<el-option label="否" value="N" />
							<el-option label="进行中" value="I" />
							<el-option label="是" value="Y" />
						</el-select>
					</template>
				</el-table-column>
				<el-table-column label="批次" width="120">
					<template #default="{ row }">
						<el-input v-model="row.goodsBatch" placeholder="批次" />
					</template>
				</el-table-column>
				<el-table-column label="生产日期" width="180">
					<template #default="{ row }">
						<el-date-picker
							v-model="row.goodsPrdData"
							type="datetime"
							value-format="YYYY-MM-DD HH:mm:ss"
							placeholder="生产日期"
							style="width: 100%"
						/>
					</template>
				</el-table-column>
				<el-table-column label="托盘" width="110">
					<template #default="{ row }">
						<el-input v-model="row.tinId" placeholder="托盘" />
					</template>
				</el-table-column>
				<el-table-column label="操作" width="70" fixed="right">
					<template #default="{ $index }">
						<el-button link type="danger" @click="removeItem($index)">删除</el-button>
					</template>
				</el-table-column>
			</el-table>

			<template #footer>
				<el-button @click="dialogVisible = false">取消</el-button>
				<el-button type="primary" :loading="dialogSaving" @click="submitForm">保存</el-button>
			</template>
		</el-dialog>
	</section>
</template>

<style lang="scss" scoped>
.notice-order-root {
	width: 100%;

	.query-card {
		margin-bottom: 12px;
	}

	.tool-bar {
		display: flex;
		align-items: center;
		gap: 16px;
		margin: 12px 0;
	}

	.tip {
		color: #909399;
		font-size: 13px;
	}

	.section-title {
		margin: 18px 0 10px;
	}

	.form-grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		column-gap: 24px;
	}

	.span-2 {
		grid-column: span 2;
	}

	.attachment-row {
		display: flex;
		align-items: center;
		gap: 12px;
	}

	.items-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin: 8px 0;
	}
}
</style>
