<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import {
	listAdPick,
	getAdPickDetail,
	modifyAdPick,
	modifyAdPickList,
	exportAdPick,
	saveBlob,
} from "@/apis/outbound/index";

definePage({
	meta: {
		menuType: "page",
		text: "按单拣货",
		icon: "IconSetting",
	},
});

interface PickRow {
	id?: string;
	createDate?: string;
	orderId?: string;
	goodsId?: string;
	goodsName?: string;
	imCusCode?: string;
	omBeiZhu?: string;
	goodsQua?: string;
	goodsQuaok?: string;
	baseGoodscount?: string;
	baseUnit?: string;
	goodsProData?: string;
	binIdFrom?: string;
	kuWeiBianMa?: string;
	cusCode?: string;
	cusName?: string;
}

const loading = ref(false);
const rows = ref<PickRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const selected = ref<PickRow[]>([]);
const query = ref({
	orderId: "",
	goodsId: "",
	goodsName: "",
	imCusCode: "",
	cusCode: "",
	binIdFrom: "",
});

const editVisible = ref(false);
const editForm = ref<any>({});
const batchVisible = ref(false);
const batchForm = ref<any>({});

function loadData() {
	loading.value = true;
	listAdPick(
		{ pageIndex: pageIndex.value, pageSize: pageSize.value, ...query.value },
		(data: any) => {
			rows.value = data.rows ?? [];
			total.value = data.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("拣货列表加载失败");
		},
	);
}

function resetQuery() {
	query.value = { orderId: "", goodsId: "", goodsName: "", imCusCode: "", cusCode: "", binIdFrom: "" };
	pageIndex.value = 1;
	loadData();
}

function openEdit(row: PickRow) {
	getAdPickDetail(
		row.id as string,
		(data: any) => {
			editForm.value = {
				id: data.id,
				orderId: data.orderId,
				goodsId: data.goodsId,
				goodsName: data.goodsName ?? row.goodsName,
				imCusCode: row.imCusCode,
				goodsQua: data.goodsQua,
				goodsQuaok: data.goodsQuaok,
				baseGoodscount: data.baseGoodscount,
				goodsProData: data.goodsProData,
				binIdFrom: data.binIdFrom,
				kuWeiBianMa: data.kuWeiBianMa,
				binIdTo: data.binIdTo,
				cusCode: data.cusCode,
				goodsUnit: data.goodsUnit,
				baseUnit: data.baseUnit,
				actTypeCode: data.actTypeCode,
				downSta: data.downSta,
			};
			editVisible.value = true;
		},
		() => ElMessage.error("拣货详情加载失败"),
	);
}

async function submitEdit() {
	if (!editForm.value.goodsName || !editForm.value.imCusCode) {
		ElMessage.warning("商品名称和客户订单号不能为空");
		return;
	}
	const res = await modifyAdPick(editForm.value);
	if (res.data?.code === 10000) {
		ElMessage.success("修改成功");
		editVisible.value = false;
		loadData();
	} else {
		ElMessage.error(res.data?.message || "修改失败");
	}
}

function openBatch() {
	if (!selected.value.length) {
		ElMessage.warning("请先勾选拣货行");
		return;
	}
	batchForm.value = {
		goodsQua: "",
		goodsQuaok: "",
		baseGoodscount: "",
		goodsProData: "",
		binIdFrom: "",
		kuWeiBianMa: "",
	};
	batchVisible.value = true;
}

async function submitBatch() {
	const list = selected.value.map(row => ({
		goodsName: row.goodsName,
		imCusCode: row.imCusCode,
		goodsQua: batchForm.value.goodsQua || row.goodsQua,
		goodsQuaok: batchForm.value.goodsQuaok || row.goodsQuaok,
		baseGoodscount: batchForm.value.baseGoodscount || row.baseGoodscount,
		goodsProData: batchForm.value.goodsProData || row.goodsProData,
		binIdFrom: batchForm.value.binIdFrom || row.binIdFrom,
		kuWeiBianMa: batchForm.value.kuWeiBianMa || row.kuWeiBianMa,
	}));
	const res = await modifyAdPickList(list);
	if (res.data?.code === 10000) {
		ElMessage.success("批量修改成功");
		batchVisible.value = false;
		loadData();
	} else {
		ElMessage.error(res.data?.message || "批量修改失败");
	}
}

async function handleExport() {
	try {
		const source = selected.value.length ? selected.value : rows.value;
		const queries = source.map(row => ({
			orderId: row.orderId,
			goodsId: row.goodsId,
			goodsName: row.goodsName,
			customerOrderId: row.imCusCode,
			omBeiZhu: row.omBeiZhu,
			goodsQua: row.goodsQua,
			goodsQuaok: row.goodsQuaok,
			baseUnit: row.baseUnit,
			binIdFrom: row.binIdFrom,
			kuWeiBianMa: row.kuWeiBianMa,
			cusCode: row.cusCode,
		}));
		const blob = await exportAdPick(queries.length ? queries : [{}]);
		saveBlob(blob, "出库任务列表.xlsx");
		ElMessage.success("导出成功");
	} catch (e) {
		ElMessage.error("导出失败");
	}
}

function handleSelectionChange(val: PickRow[]) {
	selected.value = val;
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
	<section class="picking-root">
		<el-form :model="query" inline class="query-bar">
			<el-form-item label="出库单号">
				<el-input v-model="query.orderId" clearable style="width: 170px" />
			</el-form-item>
			<el-form-item label="商品编码">
				<el-input v-model="query.goodsId" clearable style="width: 140px" />
			</el-form-item>
			<el-form-item label="商品名称">
				<el-input v-model="query.goodsName" clearable style="width: 160px" />
			</el-form-item>
			<el-form-item label="客户订单号">
				<el-input v-model="query.imCusCode" clearable style="width: 150px" />
			</el-form-item>
			<el-form-item label="货主">
				<el-input v-model="query.cusCode" clearable style="width: 120px" />
			</el-form-item>
			<el-form-item>
				<el-button type="primary" @click="loadData">查询</el-button>
				<el-button @click="resetQuery">重置</el-button>
			</el-form-item>
		</el-form>

		<div class="tool-bar">
			<el-button type="primary" @click="openBatch">批量修改</el-button>
			<el-button type="success" @click="handleExport">导出</el-button>
			<span class="tip">已选 {{ selected.length }} 条</span>
		</div>

		<el-table
			v-loading="loading"
			:data="rows"
			border
			stripe
			style="width: 100%"
			@selection-change="handleSelectionChange"
		>
			<el-table-column type="selection" width="50" />
			<el-table-column prop="createDate" label="创建日期" width="170" />
			<el-table-column prop="orderId" label="出库单号" width="170" show-overflow-tooltip />
			<el-table-column prop="goodsId" label="商品编码" width="130" show-overflow-tooltip />
			<el-table-column prop="goodsName" label="商品名称" min-width="160" show-overflow-tooltip />
			<el-table-column prop="imCusCode" label="客户订单号" width="130" show-overflow-tooltip />
			<el-table-column prop="goodsQua" label="数量" width="90" align="right" />
			<el-table-column prop="goodsQuaok" label="完成数量" width="100" align="right" />
			<el-table-column prop="baseUnit" label="基本单位" width="90" />
			<el-table-column prop="goodsProData" label="生产日期" width="120" />
			<el-table-column prop="binIdFrom" label="源托盘" width="110" />
			<el-table-column prop="kuWeiBianMa" label="库位" width="120" />
			<el-table-column prop="cusCode" label="货主" width="100" />
			<el-table-column prop="cusName" label="货主名称" min-width="150" show-overflow-tooltip />
			<el-table-column label="操作" width="80" fixed="right">
				<template #default="{ row }">
					<el-button link type="primary" @click="openEdit(row)">修改</el-button>
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

		<el-dialog v-model="editVisible" title="修改拣货信息" width="560px">
			<el-form :model="editForm" label-width="110px">
				<el-form-item label="商品编码">
					<el-input v-model="editForm.goodsId" disabled />
				</el-form-item>
				<el-form-item label="商品名称">
					<el-input v-model="editForm.goodsName" />
				</el-form-item>
				<el-form-item label="客户订单号">
					<el-input v-model="editForm.imCusCode" />
				</el-form-item>
				<el-form-item label="数量">
					<el-input v-model="editForm.goodsQua" />
				</el-form-item>
				<el-form-item label="完成数量">
					<el-input v-model="editForm.goodsQuaok" />
				</el-form-item>
				<el-form-item label="生产日期">
					<el-input v-model="editForm.goodsProData" placeholder="yyyy-MM-dd" />
				</el-form-item>
				<el-form-item label="源托盘">
					<el-input v-model="editForm.binIdFrom" />
				</el-form-item>
				<el-form-item label="库位">
					<el-input v-model="editForm.kuWeiBianMa" />
				</el-form-item>
				<el-form-item label="目标托盘">
					<el-input v-model="editForm.binIdTo" />
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="editVisible = false">取消</el-button>
				<el-button type="primary" @click="submitEdit">保存</el-button>
			</template>
		</el-dialog>

		<el-dialog v-model="batchVisible" title="批量修改拣货" width="520px">
			<el-form :model="batchForm" label-width="110px">
				<el-form-item label="数量">
					<el-input v-model="batchForm.goodsQua" placeholder="留空则不修改" />
				</el-form-item>
				<el-form-item label="完成数量">
					<el-input v-model="batchForm.goodsQuaok" placeholder="留空则不修改" />
				</el-form-item>
				<el-form-item label="基本单位数量">
					<el-input v-model="batchForm.baseGoodscount" placeholder="留空则不修改" />
				</el-form-item>
				<el-form-item label="生产日期">
					<el-input v-model="batchForm.goodsProData" placeholder="留空则不修改" />
				</el-form-item>
				<el-form-item label="源托盘">
					<el-input v-model="batchForm.binIdFrom" placeholder="留空则不修改" />
				</el-form-item>
				<el-form-item label="库位">
					<el-input v-model="batchForm.kuWeiBianMa" placeholder="留空则不修改" />
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="batchVisible = false">取消</el-button>
				<el-button type="primary" @click="submitBatch">保存</el-button>
			</template>
		</el-dialog>
	</section>
</template>

<style lang="scss" scoped>
.picking-root {
	width: 100%;

	.query-bar {
		margin-top: 8px;
	}

	.tool-bar {
		display: flex;
		align-items: center;
		gap: 8px;
		margin: 4px 0 12px;
	}

	.tip {
		margin-left: 8px;
		color: #909399;
		font-size: 13px;
	}
}
</style>
