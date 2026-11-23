<script lang="ts" setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { exportNotShelvedItems, listNotShelvedItems, saveBlob } from "@/apis/purchase/index";

definePage({
	meta: {
		menuType: "page",
		text: "收货上架",
		icon: "IconSetting",
	},
});

interface NotShelvedRow {
	id?: string;
	binSta?: string;
	binId?: string;
	tinId?: string;
	cusCode?: string;
	cusName?: string;
	goodsId?: string;
	goodsName?: string;
	qmOkQuat?: string;
	goodsUnit?: string;
	proData?: string;
	createDate?: string;
	goodsBatch?: string;
}

const loading = ref(false);
const exporting = ref(false);
const rows = ref<NotShelvedRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);

const query = reactive({
	imNoticeId: "",
	goodsId: "",
	goodsName: "",
	binId: "",
	cusCode: "",
});

function formatDateTime(value?: string) {
	if (!value) return "";
	return String(value).replace("T", " ");
}

function statusText(value?: string) {
	if (value === "N") return "未上架";
	if (value === "I") return "上架中";
	if (value === "Y") return "已上架";
	return value ?? "";
}

function loadData() {
	loading.value = true;
	listNotShelvedItems(
		{ pageIndex: pageIndex.value, pageSize: pageSize.value, ...query },
		(data: any) => {
			rows.value = data?.rows ?? [];
			total.value = data?.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("收货上架数据加载失败");
		},
	);
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	Object.assign(query, { imNoticeId: "", goodsId: "", goodsName: "", binId: "", cusCode: "" });
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

async function handleExport() {
	exporting.value = true;
	try {
		const blob = await exportNotShelvedItems({ ...query });
		saveBlob(blob, `收货上架_${Date.now()}.xlsx`);
		ElMessage.success("导出成功");
	} catch (err: any) {
		ElMessage.error(err?.message || "导出失败");
	} finally {
		exporting.value = false;
	}
}

onMounted(() => {
	loadData();
});
</script>

<template>
	<section class="received-unsold-root">
		<el-card shadow="never" class="query-card">
			<el-form :model="query" inline label-width="90px">
				<el-form-item label="通知单号">
					<el-input v-model="query.imNoticeId" clearable placeholder="请输入通知单号" style="width: 170px" />
				</el-form-item>
				<el-form-item label="商品编码">
					<el-input v-model="query.goodsId" clearable placeholder="请输入商品编码" style="width: 150px" />
				</el-form-item>
				<el-form-item label="商品名称">
					<el-input v-model="query.goodsName" clearable placeholder="请输入商品名称" style="width: 150px" />
				</el-form-item>
				<el-form-item label="储位">
					<el-input v-model="query.binId" clearable placeholder="请输入储位" style="width: 140px" />
				</el-form-item>
				<el-form-item label="客户编码">
					<el-input v-model="query.cusCode" clearable placeholder="请输入客户编码" style="width: 140px" />
				</el-form-item>
				<el-form-item>
					<el-button type="primary" @click="handleSearch">查询</el-button>
					<el-button @click="handleReset">重置</el-button>
				</el-form-item>
			</el-form>
		</el-card>

		<div class="tool-bar">
			<el-button type="warning" :loading="exporting" @click="handleExport">导出数据</el-button>
			<el-button @click="loadData">刷新</el-button>
			<span class="tip">已收货验收但尚未上架的商品</span>
		</div>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%">
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column label="库存状态" width="100">
				<template #default="{ row }">
					<el-tag type="warning">{{ statusText(row.binSta) }}</el-tag>
				</template>
			</el-table-column>
			<el-table-column prop="imNoticeId" label="通知单号" width="160" show-overflow-tooltip />
			<el-table-column prop="binId" label="储位" width="110" show-overflow-tooltip />
			<el-table-column prop="tinId" label="托盘" width="110" show-overflow-tooltip />
			<el-table-column prop="cusCode" label="客户编码" width="100" />
			<el-table-column prop="cusName" label="客户名称" min-width="160" show-overflow-tooltip />
			<el-table-column prop="goodsId" label="商品编码" width="110" show-overflow-tooltip />
			<el-table-column prop="goodsName" label="商品名称" min-width="130" show-overflow-tooltip />
			<el-table-column prop="qmOkQuat" label="数量" width="90" align="right" />
			<el-table-column prop="goodsUnit" label="单位" width="70" />
			<el-table-column prop="goodsBatch" label="批次" width="110" show-overflow-tooltip />
			<el-table-column prop="proData" label="生产日期" width="110" />
			<el-table-column label="收货日期" width="160">
				<template #default="{ row }">{{ formatDateTime(row.createDate) }}</template>
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
	</section>
</template>

<style lang="scss" scoped>
.received-unsold-root {
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
