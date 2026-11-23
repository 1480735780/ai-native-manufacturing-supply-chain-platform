<script lang="ts" setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { exportInNoticeItems, listInNoticeItems, saveBlob } from "@/apis/purchase/index";

definePage({
	meta: {
		menuType: "page",
		text: "进货通知明细",
		icon: "IconSetting",
	},
});

interface NoticeItemRow {
	imNoticeId?: string;
	cusCode?: string;
	cusName?: string;
	noticeiSta?: string;
	goodsCode?: string;
	goodsName?: string;
	goodsCount?: number;
	goodsQmCount?: number;
	goodsUnit?: string;
	goodsFvol?: number;
	goodsWeight?: number;
	imCusCode?: string;
	baseGoodscount?: number;
	baseUnit?: string;
	goodsPrdData?: string;
}

const loading = ref(false);
const exporting = ref(false);
const rows = ref<NoticeItemRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);

const query = reactive({
	imNoticeId: "",
	cusCode: "",
	createName: "",
	goodsCode: "",
	goodsName: "",
	noticeiSta: "",
});

function loadData() {
	loading.value = true;
	listInNoticeItems(
		{
			pageIndex: pageIndex.value,
			pageSize: pageSize.value,
			...query,
		},
		(data: any) => {
			rows.value = data?.rows ?? [];
			total.value = data?.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("进货通知明细加载失败");
		},
	);
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	Object.assign(query, {
		imNoticeId: "",
		cusCode: "",
		createName: "",
		goodsCode: "",
		goodsName: "",
		noticeiSta: "",
	});
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

async function handleExport() {
	exporting.value = true;
	try {
		const blob = await exportInNoticeItems({ ...query });
		saveBlob(blob, `进货通知明细_${Date.now()}.xlsx`);
		ElMessage.success("导出成功");
	} catch (err: any) {
		ElMessage.error(err?.message || "导出失败");
	} finally {
		exporting.value = false;
	}
}

function statusTagType(status?: string) {
	if (status === "已完成") return "success";
	if (status === "收货中") return "warning";
	return "primary";
}

onMounted(() => {
	loadData();
});
</script>

<template>
	<section class="notification-details-root">
		<el-card shadow="never" class="query-card">
			<el-form :model="query" inline label-width="90px">
				<el-form-item label="通知单号">
					<el-input v-model="query.imNoticeId" clearable placeholder="请输入通知单号" style="width: 180px" />
				</el-form-item>
				<el-form-item label="客户编码">
					<el-input v-model="query.cusCode" clearable placeholder="请输入客户编码" style="width: 150px" />
				</el-form-item>
				<el-form-item label="客户名称">
					<el-input v-model="query.createName" clearable placeholder="请输入客户名称" style="width: 170px" />
				</el-form-item>
				<el-form-item label="商品编码">
					<el-input v-model="query.goodsCode" clearable placeholder="请输入商品编码" style="width: 150px" />
				</el-form-item>
				<el-form-item label="商品名称">
					<el-input v-model="query.goodsName" clearable placeholder="请输入商品名称" style="width: 150px" />
				</el-form-item>
				<el-form-item label="行项目状态">
					<el-select v-model="query.noticeiSta" clearable placeholder="全部" style="width: 130px">
						<el-option label="计划中" value="计划中" />
						<el-option label="收货中" value="收货中" />
						<el-option label="已完成" value="已完成" />
					</el-select>
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
		</div>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%">
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="imNoticeId" label="通知单号" width="170" show-overflow-tooltip />
			<el-table-column prop="cusCode" label="客户编码" width="110" />
			<el-table-column prop="cusName" label="客户名称" min-width="170" show-overflow-tooltip />
			<el-table-column label="行项目状态" width="110">
				<template #default="{ row }">
					<el-tag :type="statusTagType(row.noticeiSta)">{{ row.noticeiSta || "计划中" }}</el-tag>
				</template>
			</el-table-column>
			<el-table-column prop="goodsCode" label="商品编码" width="120" show-overflow-tooltip />
			<el-table-column prop="goodsName" label="商品名称" min-width="150" show-overflow-tooltip />
			<el-table-column prop="goodsCount" label="通知数量" width="100" align="right" />
			<el-table-column prop="goodsQmCount" label="验收数量" width="100" align="right" />
			<el-table-column prop="goodsUnit" label="单位" width="80" />
			<el-table-column prop="baseGoodscount" label="基本数量" width="100" align="right" />
			<el-table-column prop="baseUnit" label="基本单位" width="90" />
			<el-table-column prop="imCusCode" label="客户订单号" width="130" show-overflow-tooltip />
			<el-table-column prop="goodsPrdData" label="生产日期" width="170" />
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
.notification-details-root {
	width: 100%;

	.query-card {
		margin-bottom: 12px;
	}

	.tool-bar {
		display: flex;
		align-items: center;
		gap: 12px;
		margin-bottom: 12px;
	}
}
</style>
