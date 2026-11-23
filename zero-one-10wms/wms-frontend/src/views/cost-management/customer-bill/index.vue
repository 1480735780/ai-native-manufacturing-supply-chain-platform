<script lang="ts" setup>
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import {
	listCustomerBills,
	exportUnsettledBill,
	exportPeriodBill,
	saveBlob,
} from "@/apis/cost-management/index";

definePage({
	meta: {
		menuType: "page",
		text: "客户账单",
		icon: "IconSetting",
	},
});

interface CustomerRow {
	customercode?: string;
	fullchinesename?: string;
}

const loading = ref(false);
const exporting = ref(false);
const rows = ref<CustomerRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);

const searchForm = reactive({
	customercode: "",
	fullchinesename: "",
});

const periodVisible = ref(false);
const periodSaving = ref(false);
const periodForm = reactive({
	customercode: "",
	dateRange: [] as string[],
});

function loadData() {
	loading.value = true;
	listCustomerBills(
		{
			pageIndex: pageIndex.value,
			pageSize: pageSize.value,
			customercode: searchForm.customercode,
			fullchinesename: searchForm.fullchinesename,
		},
		(data: any) => {
			rows.value = data?.rows ?? [];
			total.value = data?.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("客户账单列表加载失败");
		},
	);
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	searchForm.customercode = "";
	searchForm.fullchinesename = "";
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

async function exportUnsettled(row: CustomerRow) {
	if (!row.customercode) {
		ElMessage.warning("该客户缺少客户编码");
		return;
	}
	exporting.value = true;
	try {
		const blob = await exportUnsettledBill(row.customercode);
		saveBlob(blob, `未清账单_${row.customercode}_${Date.now()}.xlsx`);
		ElMessage.success("导出成功");
	} catch (err: any) {
		ElMessage.error(err?.message || "导出失败");
	} finally {
		exporting.value = false;
	}
}

function openPeriod(row?: CustomerRow) {
	periodForm.customercode = row?.customercode ?? "";
	periodForm.dateRange = [];
	periodVisible.value = true;
}

async function submitPeriod() {
	if (!periodForm.customercode) {
		ElMessage.warning("请输入客户编码");
		return;
	}
	if (periodForm.dateRange.length !== 2) {
		ElMessage.warning("请选择账单期间");
		return;
	}
	periodSaving.value = true;
	try {
		const blob = await exportPeriodBill({
			customercode: periodForm.customercode,
			startdate: `${periodForm.dateRange[0]} 00:00:00`,
			enddate: `${periodForm.dateRange[1]} 23:59:59`,
		});
		saveBlob(blob, `期间账单_${periodForm.customercode}_${Date.now()}.xlsx`);
		ElMessage.success("导出成功");
		periodVisible.value = false;
	} catch (err: any) {
		ElMessage.error(err?.message || "导出失败");
	} finally {
		periodSaving.value = false;
	}
}

onMounted(() => {
	loadData();
});
</script>

<template>
	<section class="customer-bill-root">
		<h2>客户账单</h2>

		<el-form :inline="true" class="filter-bar">
			<el-form-item label="客户编码">
				<el-input v-model="searchForm.customercode" placeholder="客户编码" clearable style="width: 150px" />
			</el-form-item>
			<el-form-item label="客户名称">
				<el-input
					v-model="searchForm.fullchinesename"
					placeholder="中文全称"
					clearable
					style="width: 180px"
				/>
			</el-form-item>
			<el-form-item>
				<el-button type="primary" @click="handleSearch">查询</el-button>
				<el-button @click="handleReset">重置</el-button>
				<el-button type="warning" @click="openPeriod()">导出期间账单</el-button>
			</el-form-item>
		</el-form>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%">
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="customercode" label="客户编码" width="160" />
			<el-table-column prop="fullchinesename" label="客户名称" min-width="260" show-overflow-tooltip />
			<el-table-column label="操作" width="220" fixed="right">
				<template #default="{ row }">
					<el-button link type="primary" :loading="exporting" @click="exportUnsettled(row)">
						导出未清账单
					</el-button>
					<el-button link type="primary" @click="openPeriod(row)">导出期间账单</el-button>
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

		<el-dialog v-model="periodVisible" title="导出期间账单" width="460px" :close-on-click-modal="false">
			<el-form :model="periodForm" label-width="90px">
				<el-form-item label="客户编码" required>
					<el-input v-model="periodForm.customercode" placeholder="请输入客户编码" />
				</el-form-item>
				<el-form-item label="账单期间" required>
					<el-date-picker
						v-model="periodForm.dateRange"
						type="daterange"
						value-format="YYYY-MM-DD"
						start-placeholder="开始日期"
						end-placeholder="结束日期"
						style="width: 100%"
					/>
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="periodVisible = false">取消</el-button>
				<el-button type="primary" :loading="periodSaving" @click="submitPeriod">开始导出</el-button>
			</template>
		</el-dialog>
	</section>
</template>

<style lang="scss" scoped>
.customer-bill-root {
	width: 100%;

	.filter-bar {
		margin-top: 12px;
	}

	.pagination-bar {
		display: flex;
		justify-content: flex-end;
		margin-top: 16px;
	}
}
</style>
