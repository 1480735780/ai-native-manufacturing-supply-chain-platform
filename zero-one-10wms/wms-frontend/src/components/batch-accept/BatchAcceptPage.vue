<script lang="ts" setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { batchAcceptItems, listToAcceptItems } from "@/apis/purchase/index";

interface Props {
	/** 页面标题（提示文案使用） */
	title?: string;
	/** 锁定的订单类型编码；传入后列表强制按该类型过滤（03=退货通知） */
	fixedOrderTypeCode?: string;
}

const props = withDefaults(defineProps<Props>(), {
	title: "待验收货物",
	fixedOrderTypeCode: "",
});

interface ToAcceptRow {
	id?: string;
	createDate?: string;
	imNoticeId?: string;
	imCusCode?: string;
	imBeizhu?: string;
	cusCode?: string;
	goodsCode?: string;
	goodsName?: string;
	goodsCount?: number;
	goodsQmCount?: number;
	goodsWqmCount?: number;
	goodsPrdData?: string;
	goodsBatch?: string;
	binPlan?: string;
	tinId?: string;
	goodsUnit?: string;
	acceptCount?: number;
}

const loading = ref(false);
const rows = ref<ToAcceptRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const selectedRows = ref<ToAcceptRow[]>([]);

const query = reactive({
	imNoticeId: "",
	goodsCode: "",
	goodsName: "",
});

const acceptVisible = ref(false);
const acceptSaving = ref(false);
const acceptRows = ref<ToAcceptRow[]>([]);
const acceptForm = reactive({
	binId: "",
	proData: "",
	goodsBatch: "",
	recDeg: "",
	tinId: "",
	itemText: "",
});

function loadData() {
	loading.value = true;
	const params: Record<string, unknown> = {
		page: pageIndex.value,
		size: pageSize.value,
		...query,
	};
	if (props.fixedOrderTypeCode) {
		params.orderTypeCode = props.fixedOrderTypeCode;
	}
	listToAcceptItems(
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
	query.imNoticeId = "";
	query.goodsCode = "";
	query.goodsName = "";
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

function handleSelectionChange(selection: ToAcceptRow[]) {
	selectedRows.value = selection;
}

function openAccept() {
	if (selectedRows.value.length === 0) {
		ElMessage.warning("请先勾选要验收的货物");
		return;
	}
	acceptRows.value = selectedRows.value.map((row) => ({
		...row,
		acceptCount: row.goodsWqmCount && row.goodsWqmCount > 0 ? row.goodsWqmCount : row.goodsCount,
	}));
	acceptForm.binId = "";
	acceptForm.proData = "";
	acceptForm.goodsBatch = "";
	acceptForm.recDeg = "";
	acceptForm.tinId = "";
	acceptForm.itemText = "";
	acceptVisible.value = true;
}

async function submitAccept() {
	for (const row of acceptRows.value) {
		if (!row.acceptCount || Number(row.acceptCount) <= 0) {
			ElMessage.warning(`商品 ${row.goodsName || row.goodsCode} 的验收数量必须大于 0`);
			return;
		}
	}
	acceptSaving.value = true;
	try {
		const payload = acceptRows.value.map((row) => ({
			id: row.id,
			imNoticeId: row.imNoticeId,
			goodsId: row.goodsCode,
			cusCode: row.cusCode,
			binId: acceptForm.binId,
			imQuat: String(row.acceptCount),
			proData: acceptForm.proData,
			goodsBatch: acceptForm.goodsBatch,
			recDeg: acceptForm.recDeg,
			itemText: acceptForm.itemText,
			tinId: acceptForm.tinId,
			tinZhl: "",
		}));
		await batchAcceptItems(payload);
		ElMessage.success("批量验收成功");
		acceptVisible.value = false;
		loadData();
	} catch (err: any) {
		ElMessage.error(err?.data?.message || err?.message || "批量验收失败");
	} finally {
		acceptSaving.value = false;
	}
}

onMounted(() => {
	loadData();
});
</script>

<template>
	<section class="batch-accept-root">
		<el-card shadow="never" class="query-card">
			<el-form :model="query" inline label-width="90px">
				<el-form-item label="通知单号">
					<el-input v-model="query.imNoticeId" clearable placeholder="请输入通知单号" style="width: 180px" />
				</el-form-item>
				<el-form-item label="商品编码">
					<el-input v-model="query.goodsCode" clearable placeholder="请输入商品编码" style="width: 150px" />
				</el-form-item>
				<el-form-item label="商品名称">
					<el-input v-model="query.goodsName" clearable placeholder="请输入商品名称" style="width: 150px" />
				</el-form-item>
				<el-form-item>
					<el-button type="primary" @click="handleSearch">查询</el-button>
					<el-button @click="handleReset">重置</el-button>
				</el-form-item>
			</el-form>
		</el-card>

		<div class="tool-bar">
			<el-button type="success" @click="openAccept">批量验收</el-button>
			<el-button @click="loadData">刷新</el-button>
			<span class="tip">勾选{{ title }}后，可批量提交验收</span>
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
			<el-table-column prop="imNoticeId" label="到货通知单号" width="170" show-overflow-tooltip />
			<el-table-column prop="cusCode" label="客户编码" width="110" />
			<el-table-column prop="goodsCode" label="商品编码" width="120" show-overflow-tooltip />
			<el-table-column prop="goodsName" label="商品名称" min-width="160" show-overflow-tooltip />
			<el-table-column prop="goodsCount" label="预约数量" width="100" align="right" />
			<el-table-column prop="goodsQmCount" label="已登记" width="90" align="right" />
			<el-table-column prop="goodsWqmCount" label="未收货" width="90" align="right" />
			<el-table-column prop="goodsUnit" label="单位" width="80" />
			<el-table-column prop="binPlan" label="计划储位" width="110" show-overflow-tooltip />
			<el-table-column prop="goodsBatch" label="批次" width="110" show-overflow-tooltip />
			<el-table-column prop="goodsPrdData" label="生产日期" width="120" />
			<el-table-column prop="createDate" label="创建日期" width="170" />
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

		<el-dialog v-model="acceptVisible" title="批量验收" width="900px" :close-on-click-modal="false" destroy-on-close>
			<el-form :model="acceptForm" inline label-width="90px">
				<el-form-item label="储位">
					<el-input v-model="acceptForm.binId" placeholder="请输入储位" style="width: 150px" />
				</el-form-item>
				<el-form-item label="生产日期">
					<el-date-picker
						v-model="acceptForm.proData"
						type="date"
						value-format="YYYY-MM-DD"
						placeholder="选择生产日期"
						style="width: 160px"
					/>
				</el-form-item>
				<el-form-item label="批次">
					<el-input v-model="acceptForm.goodsBatch" placeholder="请输入批次" style="width: 150px" />
				</el-form-item>
				<el-form-item label="收货温度">
					<el-input v-model="acceptForm.recDeg" placeholder="如 25" style="width: 120px" />
				</el-form-item>
				<el-form-item label="托盘">
					<el-input v-model="acceptForm.tinId" placeholder="请输入托盘" style="width: 130px" />
				</el-form-item>
				<el-form-item label="备注">
					<el-input v-model="acceptForm.itemText" placeholder="请输入备注" style="width: 200px" />
				</el-form-item>
			</el-form>

			<el-table :data="acceptRows" border stripe style="width: 100%">
				<el-table-column type="index" label="序号" width="60" />
				<el-table-column prop="imNoticeId" label="通知单号" width="170" show-overflow-tooltip />
				<el-table-column prop="goodsCode" label="商品编码" width="120" show-overflow-tooltip />
				<el-table-column prop="goodsName" label="商品名称" min-width="150" show-overflow-tooltip />
				<el-table-column prop="goodsWqmCount" label="未收货" width="90" align="right" />
				<el-table-column label="本次验收" width="140">
					<template #default="{ row }">
						<el-input-number
							v-model="row.acceptCount"
							:min="1"
							:precision="0"
							controls-position="right"
							style="width: 110px"
						/>
					</template>
				</el-table-column>
				<el-table-column prop="goodsUnit" label="单位" width="80" />
			</el-table>

			<template #footer>
				<el-button @click="acceptVisible = false">取消</el-button>
				<el-button type="primary" :loading="acceptSaving" @click="submitAccept">提交验收</el-button>
			</template>
		</el-dialog>
	</section>
</template>

<style lang="scss" scoped>
.batch-accept-root {
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
}
</style>
