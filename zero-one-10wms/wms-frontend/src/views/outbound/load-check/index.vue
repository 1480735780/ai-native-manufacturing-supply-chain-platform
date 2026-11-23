<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { listLoadChecks, batchCheckLoad, oneClickReview } from "@/apis/outbound/index";

definePage({
	meta: {
		menuType: "page",
		text: "装车复核",
		icon: "IconSetting",
	},
});

interface CheckRow {
	id?: string;
	createName?: string;
	createDate?: string;
	updateName?: string;
	updateDate?: string;
	orderId?: string;
	goodsId?: string;
	goodsName?: string;
	imCusCode?: string;
	omBeiZhu?: string;
	goodsQuaok?: string;
	goodsUnit?: string;
	goodsProData?: string;
	binIdFrom?: string;
	kuWeiBianMa?: string;
	cusCode?: string;
	binIdTo?: string;
}

const loading = ref(false);
const rows = ref<CheckRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const selected = ref<CheckRow[]>([]);
const query = ref({
	orderId: "",
	goodsId: "",
	goodsName: "",
	imCusCode: "",
	cusCode: "",
	kuWeiBianMa: "",
});

function loadData() {
	loading.value = true;
	listLoadChecks(
		{ pageIndex: pageIndex.value, pageSize: pageSize.value, ...query.value },
		(data: any) => {
			rows.value = data.rows ?? [];
			total.value = data.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("复核列表加载失败");
		},
	);
}

function resetQuery() {
	query.value = { orderId: "", goodsId: "", goodsName: "", imCusCode: "", cusCode: "", kuWeiBianMa: "" };
	pageIndex.value = 1;
	loadData();
}

async function handleBatchCheck() {
	if (!selected.value.length) {
		ElMessage.warning("请先勾选复核行");
		return;
	}
	const payload = selected.value.map(row => ({
		id: row.id,
		goodsQuaok: row.goodsQuaok,
		omNoticeId: row.orderId,
	}));
	const res = await batchCheckLoad(payload);
	if (res.data?.code === 10000) {
		ElMessage.success("复核成功");
		loadData();
	} else {
		ElMessage.error(res.data?.message || "复核失败");
	}
}

async function handleOneClick() {
	if (!selected.value.length) {
		ElMessage.warning("请先勾选通知单");
		return;
	}
	const noticeIds = Array.from(new Set(selected.value.map(r => r.orderId).filter(Boolean))) as string[];
	await ElMessageBox.confirm(`确认一键复核 ${noticeIds.length} 个通知单？`, "提示", { type: "warning" });
	const res = await oneClickReview(noticeIds);
	if (res.data?.code === 10000) {
		ElMessage.success("一键复核成功");
		loadData();
	} else {
		ElMessage.error(res.data?.message || "一键复核失败");
	}
}

function handleSelectionChange(val: CheckRow[]) {
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
	<section class="check-root">
		<el-form :model="query" inline class="query-bar">
			<el-form-item label="原始单据">
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
			<el-form-item label="库位">
				<el-input v-model="query.kuWeiBianMa" clearable style="width: 130px" />
			</el-form-item>
			<el-form-item>
				<el-button type="primary" @click="loadData">查询</el-button>
				<el-button @click="resetQuery">重置</el-button>
			</el-form-item>
		</el-form>

		<div class="tool-bar">
			<el-button type="primary" @click="handleBatchCheck">批量复核</el-button>
			<el-button type="success" @click="handleOneClick">一键复核</el-button>
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
			<el-table-column prop="orderId" label="原始单据" width="170" show-overflow-tooltip />
			<el-table-column prop="goodsId" label="商品编码" width="130" show-overflow-tooltip />
			<el-table-column prop="goodsName" label="商品名称" min-width="160" show-overflow-tooltip />
			<el-table-column prop="imCusCode" label="客户订单号" width="130" show-overflow-tooltip />
			<el-table-column prop="goodsQuaok" label="数量" width="90" align="right" />
			<el-table-column prop="goodsUnit" label="单位" width="70" />
			<el-table-column prop="goodsProData" label="生产日期" width="120" />
			<el-table-column prop="binIdFrom" label="源托盘" width="110" />
			<el-table-column prop="kuWeiBianMa" label="库位" width="120" />
			<el-table-column prop="binIdTo" label="目标托盘" width="110" />
			<el-table-column prop="cusCode" label="货主" width="100" />
			<el-table-column prop="createName" label="下架人" width="100" />
			<el-table-column prop="createDate" label="下架时间" width="170" />
			<el-table-column prop="updateName" label="复核人" width="100" />
			<el-table-column prop="updateDate" label="复核时间" width="170" />
			<el-table-column prop="omBeiZhu" label="备注" min-width="140" show-overflow-tooltip />
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
	</section>
</template>

<style lang="scss" scoped>
.check-root {
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
