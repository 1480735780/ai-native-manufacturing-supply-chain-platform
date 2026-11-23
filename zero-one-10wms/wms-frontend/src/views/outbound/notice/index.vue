<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
	listOutNotices,
	getOutNoticeDetail,
	addOutNotice,
	updateOutNotice,
	deleteOutNotice,
	uploadOutNoticeAttachment,
	printPickingList,
	printOutGoodsList,
	exportOutNoticeH,
	exportOutNoticeI,
	previewBlob,
	saveBlob,
} from "@/apis/outbound/index";

definePage({
	meta: {
		menuType: "page",
		text: "出库通知单管理",
		icon: "IconSetting",
	},
});

interface NoticeRow {
	omNoticeId?: string;
	cusCode?: string;
	imCusCode?: string;
	ocusName?: string;
	delvData?: string;
	delvMember?: string;
	omSta?: string;
	createDate?: string;
	fuJian?: string;
}

interface NoticeItem {
	id?: string;
	goodsId?: string;
	goodsName?: string;
	outGoodsNumber?: string;
	sku?: string;
}

const loading = ref(false);
const rows = ref<NoticeRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);

const query = ref({
	omNoticeId: "",
	imCusCode: "",
	ocusName: "",
	omSta: "",
});

const dialogVisible = ref(false);
const dialogTitle = ref("新增出库通知单");
const isEdit = ref(false);
const form = ref<any>(createEmptyForm());
const items = ref<NoticeItem[]>([]);
const detailVisible = ref(false);
const detail = ref<any>({});
const detailItems = ref<NoticeItem[]>([]);

function createEmptyForm() {
	return {
		omNoticeId: "",
		cueCode: "",
		delvData: "",
		orderTypeCode: "01",
		imCusCode: "",
		ocusName: "",
		delvMember: "",
		delvMobile: "",
		delvAddr: "",
		reMember: "",
		reCarno: "",
		delvMethod: "汽运",
		omPlatNo: "",
		omBeizhu: "",
		storeCode: "",
	};
}

function loadData() {
	loading.value = true;
	listOutNotices(
		{ pageIndex: pageIndex.value, pageSize: pageSize.value, ...query.value },
		(data: any) => {
			rows.value = data.rows ?? [];
			total.value = data.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("出库通知单加载失败");
		},
	);
}

function resetQuery() {
	query.value = { omNoticeId: "", imCusCode: "", ocusName: "", omSta: "" };
	pageIndex.value = 1;
	loadData();
}

function openAdd() {
	isEdit.value = false;
	dialogTitle.value = "新增出库通知单";
	form.value = createEmptyForm();
	items.value = [{ goodsId: "", goodsName: "", outGoodsNumber: "", sku: "" }];
	dialogVisible.value = true;
}

function openEdit(row: NoticeRow) {
	isEdit.value = true;
	dialogTitle.value = "编辑出库通知单";
	form.value = createEmptyForm();
	form.value.omNoticeId = row.omNoticeId ?? "";
	getOutNoticeDetail(
		row.omNoticeId,
		(data: any) => {
			Object.assign(form.value, {
				cueCode: data.cusCode ?? "",
				delvData: formatDate(data.delvData),
				orderTypeCode: data.orderTypeCode ?? "01",
				imCusCode: data.imCusCode ?? "",
				ocusName: data.ocusName ?? data.cusName ?? "",
				delvMember: data.delvMember ?? "",
				delvMobile: data.delvMobile ?? "",
				delvAddr: data.delvAddr ?? "",
				reMember: data.reMember ?? "",
				reCarno: data.reCarno ?? "",
				delvMethod: data.delvMethod ?? "汽运",
				omPlatNo: data.omPlatNo ?? "",
				omBeizhu: data.omBeizhu ?? "",
				storeCode: data.storeCode ?? data.scoreCode ?? "",
			});
			items.value = (data.outGoodDetailDTOList ?? []).map((it: any) => ({
				goodsId: it.goodsId ?? it.sku ?? "",
				goodsName: it.goodsName ?? "",
				outGoodsNumber: it.baseGoodscount ?? it.outGoodsNumber ?? "",
				sku: it.sku ?? "",
			}));
			dialogVisible.value = true;
		},
		() => ElMessage.error("通知单详情加载失败"),
	);
}

function formatDate(value: any) {
	if (!value) return "";
	return String(value).replace("T", " ").slice(0, 19);
}

function addItemRow() {
	items.value.push({ goodsId: "", goodsName: "", outGoodsNumber: "", sku: "" });
}

function removeItemRow(index: number) {
	if (items.value.length === 1) {
		ElMessage.warning("至少保留一条商品明细");
		return;
	}
	items.value.splice(index, 1);
}

async function submitForm() {
	if (!form.value.cueCode) {
		ElMessage.warning("请填写货主编码");
		return;
	}
	const validItems = items.value.filter(it => it.goodsId && it.outGoodsNumber);
	if (!validItems.length) {
		ElMessage.warning("请至少填写一条商品明细");
		return;
	}
	const payload: any = {
		cueCode: form.value.cueCode,
		delvData: form.value.delvData || null,
		orderTypeCode: form.value.orderTypeCode,
		imCusCode: form.value.imCusCode,
		ocusName: form.value.ocusName,
		delvMember: form.value.delvMember,
		delvMobile: form.value.delvMobile,
		delvAddr: form.value.delvAddr,
		reMember: form.value.reMember,
		reCarno: form.value.reCarno,
		delvMethod: form.value.delvMethod,
		omPlatNo: form.value.omPlatNo,
		omBeizhu: form.value.omBeizhu,
		storeCode: form.value.storeCode,
	};
	if (isEdit.value) {
		payload.omNoticeId = form.value.omNoticeId;
		const res = await updateOutNotice(payload);
		if (res.data?.code === 10000) {
			ElMessage.success("修改成功");
			dialogVisible.value = false;
			loadData();
		} else {
			ElMessage.error(res.data?.message || "修改失败");
		}
	} else {
		payload.outGoodsDetailDTOList = validItems.map(it => ({
			goodsId: it.goodsId,
			goodsName: it.goodsName,
			outGoodsNumber: it.outGoodsNumber,
			sku: it.sku || it.goodsId,
		}));
		const res = await addOutNotice(payload);
		if (res.data?.code === 10000) {
			ElMessage.success("新增成功");
			dialogVisible.value = false;
			loadData();
		} else {
			ElMessage.error(res.data?.message || "新增失败");
		}
	}
}

function openDetail(row: NoticeRow) {
	getOutNoticeDetail(
		row.omNoticeId,
		(data: any) => {
			detail.value = data;
			detailItems.value = data.outGoodDetailDTOList ?? [];
			detailVisible.value = true;
		},
		() => ElMessage.error("详情加载失败"),
	);
}

async function handleDelete(row: NoticeRow) {
	await ElMessageBox.confirm(`确定删除通知单 ${row.omNoticeId} 吗？`, "提示", { type: "warning" });
	const res = await deleteOutNotice(row.omNoticeId as string);
	if (res.data?.code === 10000) {
		ElMessage.success("删除成功");
		loadData();
	} else {
		ElMessage.error(res.data?.message || "删除失败");
	}
}

function makeUpload(row: NoticeRow) {
	return (option: any) => handleUpload(option, row);
}

async function handleUpload(option: any, row: NoticeRow) {
	try {
		const res = await uploadOutNoticeAttachment(row.omNoticeId as string, option.file);
		if (res.data?.code === 10000) {
			ElMessage.success("附件上传成功");
			loadData();
		} else {
			ElMessage.error(res.data?.message || "附件上传失败");
		}
	} catch (e) {
		ElMessage.error("附件上传失败");
	}
}

async function handlePrint(kind: "picking" | "goods", row: NoticeRow) {
	try {
		const blob =
			kind === "picking"
				? await printPickingList(row.omNoticeId as string)
				: await printOutGoodsList(row.omNoticeId as string);
		previewBlob(blob, kind === "picking" ? "拣货单.pdf" : "出库单.pdf");
	} catch (e) {
		ElMessage.error("打印失败");
	}
}

async function handleExport(kind: "h" | "i", row: NoticeRow) {
	try {
		const params = { omNoticeId: row.omNoticeId };
		const blob = kind === "h" ? await exportOutNoticeH(params) : await exportOutNoticeI(params);
		saveBlob(blob, kind === "h" ? "出货通知.xlsx" : "出库单.xlsx");
	} catch (e) {
		ElMessage.error("导出失败");
	}
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

onMounted(loadData);
</script>

<template>
	<section class="notice-root">
		<el-form :model="query" inline class="query-bar">
			<el-form-item label="出库单号">
				<el-input v-model="query.omNoticeId" clearable placeholder="请输入" style="width: 170px" />
			</el-form-item>
			<el-form-item label="第三方单号">
				<el-input v-model="query.imCusCode" clearable placeholder="请输入" style="width: 150px" />
			</el-form-item>
			<el-form-item label="客户名称">
				<el-input v-model="query.ocusName" clearable placeholder="请输入" style="width: 170px" />
			</el-form-item>
			<el-form-item label="状态">
				<el-select v-model="query.omSta" clearable placeholder="全部" style="width: 130px">
					<el-option label="计划中" value="计划中" />
					<el-option label="已完成" value="已完成" />
				</el-select>
			</el-form-item>
			<el-form-item>
				<el-button type="primary" @click="loadData">查询</el-button>
				<el-button @click="resetQuery">重置</el-button>
				<el-button type="success" @click="openAdd">新增</el-button>
			</el-form-item>
		</el-form>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%">
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="omNoticeId" label="出库单号" width="180" show-overflow-tooltip />
			<el-table-column prop="cusCode" label="货主" width="100" />
			<el-table-column prop="imCusCode" label="客户订单号" width="140" show-overflow-tooltip />
			<el-table-column prop="ocusName" label="客户名称" min-width="170" show-overflow-tooltip />
			<el-table-column prop="delvData" label="要求交货时间" width="170" />
			<el-table-column prop="delvMember" label="收货人" width="110" />
			<el-table-column prop="omSta" label="状态" width="90" />
			<el-table-column prop="createDate" label="创建日期" width="170" />
			<el-table-column label="操作" width="360" fixed="right">
				<template #default="{ row }">
					<el-button link type="primary" @click="openDetail(row)">详情</el-button>
					<el-button link type="primary" @click="openEdit(row)">编辑</el-button>
					<el-upload
						:show-file-list="false"
						:http-request="makeUpload(row)"
						style="display: inline-block; margin: 0 8px"
					>
						<el-button link type="primary">附件</el-button>
					</el-upload>
					<el-button link type="primary" @click="handlePrint('picking', row)">拣货单</el-button>
					<el-button link type="primary" @click="handlePrint('goods', row)">出库单</el-button>
					<el-dropdown>
						<el-button link type="primary">导出</el-button>
						<template #dropdown>
							<el-dropdown-menu>
								<el-dropdown-item @click="handleExport('h', row)">出货通知</el-dropdown-item>
								<el-dropdown-item @click="handleExport('i', row)">出库单</el-dropdown-item>
							</el-dropdown-menu>
						</template>
					</el-dropdown>
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

		<el-dialog v-model="dialogVisible" :title="dialogTitle" width="980px" destroy-on-close>
			<el-form :model="form" label-width="100px">
				<el-row :gutter="12">
					<el-col :span="8">
						<el-form-item label="货主编码" required>
							<el-input v-model="form.cueCode" placeholder="如 1250" />
						</el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="交货时间">
							<el-date-picker
								v-model="form.delvData"
								type="datetime"
								value-format="YYYY-MM-DD HH:mm:ss"
								style="width: 100%"
							/>
						</el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="订单类型">
							<el-input v-model="form.orderTypeCode" placeholder="01" />
						</el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="客户订单号">
							<el-input v-model="form.imCusCode" />
						</el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="客户名称">
							<el-input v-model="form.ocusName" />
						</el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="收货人">
							<el-input v-model="form.delvMember" />
						</el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="收货电话">
							<el-input v-model="form.delvMobile" />
						</el-form-item>
					</el-col>
					<el-col :span="16">
						<el-form-item label="收货地址">
							<el-input v-model="form.delvAddr" />
						</el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="承运人">
							<el-input v-model="form.reMember" />
						</el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="车号">
							<el-input v-model="form.reCarno" />
						</el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="发货月台">
							<el-input v-model="form.omPlatNo" />
						</el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="仓库">
							<el-input v-model="form.storeCode" />
						</el-form-item>
					</el-col>
					<el-col :span="24">
						<el-form-item label="备注">
							<el-input v-model="form.omBeizhu" type="textarea" :rows="2" />
						</el-form-item>
					</el-col>
				</el-row>
			</el-form>

			<div class="items-bar">
				<span>商品明细</span>
				<el-button size="small" type="primary" @click="addItemRow">添加明细</el-button>
			</div>
			<el-table :data="items" border size="small">
				<el-table-column label="商品编码" width="180">
					<template #default="{ row }">
						<el-input v-model="row.goodsId" placeholder="如 RL001" />
					</template>
				</el-table-column>
				<el-table-column label="商品名称" min-width="180">
					<template #default="{ row }">
						<el-input v-model="row.goodsName" />
					</template>
				</el-table-column>
				<el-table-column label="出货数量" width="140">
					<template #default="{ row }">
						<el-input v-model="row.outGoodsNumber" />
					</template>
				</el-table-column>
				<el-table-column label="SKU" width="160">
					<template #default="{ row }">
						<el-input v-model="row.sku" />
					</template>
				</el-table-column>
				<el-table-column label="操作" width="80">
					<template #default="{ $index }">
						<el-button link type="danger" @click="removeItemRow($index)">删除</el-button>
					</template>
				</el-table-column>
			</el-table>

			<template #footer>
				<el-button @click="dialogVisible = false">取消</el-button>
				<el-button type="primary" @click="submitForm">保存</el-button>
			</template>
		</el-dialog>

		<el-drawer v-model="detailVisible" title="出库通知单详情" size="60%">
			<el-descriptions :column="2" border>
				<el-descriptions-item label="客户订单号">{{ detail.imCusCode }}</el-descriptions-item>
				<el-descriptions-item label="客户名称">{{ detail.cusName ?? detail.ocusName }}</el-descriptions-item>
				<el-descriptions-item label="货主">{{ detail.cusCode }}</el-descriptions-item>
				<el-descriptions-item label="状态">{{ detail.omSta }}</el-descriptions-item>
				<el-descriptions-item label="收货人">{{ detail.delvMember }}</el-descriptions-item>
				<el-descriptions-item label="收货电话">{{ detail.delvMobile }}</el-descriptions-item>
				<el-descriptions-item label="收货地址" :span="2">{{ detail.delvAddr }}</el-descriptions-item>
				<el-descriptions-item label="承运人">{{ detail.reMember }}</el-descriptions-item>
				<el-descriptions-item label="车号">{{ detail.reCarno }}</el-descriptions-item>
				<el-descriptions-item label="发货月台">{{ detail.omPlatNo }}</el-descriptions-item>
				<el-descriptions-item label="备注">{{ detail.omBeizhu }}</el-descriptions-item>
			</el-descriptions>
			<el-table :data="detailItems" border size="small" style="margin-top: 16px">
				<el-table-column type="index" label="序号" width="60" />
				<el-table-column prop="goodsName" label="商品名称" min-width="180" />
				<el-table-column prop="goodsId" label="商品编码" width="140" />
				<el-table-column prop="baseGoodscount" label="数量" width="120" />
				<el-table-column prop="planSta" label="下架任务" width="110" />
				<el-table-column prop="sku" label="SKU" width="150" />
			</el-table>
		</el-drawer>
	</section>
</template>

<style lang="scss" scoped>
.notice-root {
	width: 100%;

	.query-bar {
		margin-top: 8px;
	}

	.items-bar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin: 4px 0 8px;
		font-weight: 600;
	}
}
</style>
