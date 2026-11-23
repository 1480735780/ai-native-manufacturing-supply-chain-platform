<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { listImportNotices } from "@/apis/purchase/index";

definePage({
	meta: {
		menuType: "page",
		text: "预约进货",
		icon: "IconSetting",
	},
});

interface NoticeRow {
	noticeId?: string;
	cusName?: string;
	orderTypeCode?: string;
	imData?: string;
	imCarNo?: string;
	imCarDri?: string;
	supName?: string;
	imSta?: string;
	imBeiZhu?: string;
	createName?: string;
	createDate?: string;
}

const loading = ref(false);
const rows = ref<NoticeRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const noticeId = ref("");

function loadData() {
	loading.value = true;
	const params: Record<string, unknown> = {
		pageIndex: pageIndex.value,
		pageSize: pageSize.value,
		orderTypeCode: "01",
	};
	if (noticeId.value) {
		params.noticeId = noticeId.value;
	}
	listImportNotices(
		params,
		(data: any) => {
			rows.value = data.rows ?? [];
			total.value = data.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("预约进货数据加载失败");
		},
	);
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	noticeId.value = "";
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

onMounted(() => {
	loadData();
});
</script>

<template>
	<section class="apointment-purchase-root">
		<el-card shadow="never" class="query-card">
			<el-form :model="{ noticeId }" inline>
				<el-form-item label="进货通知单号">
					<el-input v-model="noticeId" clearable placeholder="请输入通知单号" style="width: 200px" />
				</el-form-item>
				<el-form-item>
					<el-button type="primary" @click="handleSearch">查询</el-button>
					<el-button @click="handleReset">重置</el-button>
				</el-form-item>
			</el-form>
		</el-card>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%">
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="noticeId" label="进货通知单号" width="170" show-overflow-tooltip />
			<el-table-column prop="cusName" label="货主" min-width="180" show-overflow-tooltip />
			<el-table-column prop="supName" label="供应商名称" min-width="160" show-overflow-tooltip />
			<el-table-column prop="imData" label="预计到货时间" width="170" />
			<el-table-column prop="imCarNo" label="车号" width="110" />
			<el-table-column prop="imCarDri" label="司机" width="90" />
			<el-table-column prop="orderTypeCode" label="订单类型" width="100" />
			<el-table-column prop="imSta" label="单据状态" width="100" />
			<el-table-column prop="imBeiZhu" label="备注" min-width="150" show-overflow-tooltip />
			<el-table-column prop="createName" label="创建人" width="100" />
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
	</section>
</template>

<style lang="scss" scoped>
.apointment-purchase-root {
	width: 100%;
}
</style>
