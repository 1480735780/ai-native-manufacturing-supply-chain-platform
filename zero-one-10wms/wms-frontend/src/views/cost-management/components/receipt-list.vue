<script lang="ts" setup>
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import {
	listCostDetails,
	listCostNames,
	listCustomerBills,
	chargeCostDetails,
	dischargeCostDetails,
} from "@/apis/cost-management/index";

interface Props {
	mode: "received" | "unpaid";
}

const props = defineProps<Props>();

interface CostRow {
	id?: string;
	create_date?: string;
	cus_code?: string;
	cus_name?: string;
	cost_code?: string;
	cost_name?: string;
	cost_data?: string;
	day_cost_hsj?: string;
	cost_sl?: string;
	cost_unit?: string;
	cost_js?: string;
}

const loading = ref(false);
const acting = ref(false);
const allRows = ref<CostRow[]>([]);
const pageIndex = ref(1);
const pageSize = ref(10);
const keyword = ref("");
const selectedRows = ref<CostRow[]>([]);
const costNameMap = ref<Record<string, string>>({});
const customerNameMap = ref<Record<string, string>>({});

const isReceived = computed(() => props.mode === "received");

const filteredRows = computed(() => {
	const key = keyword.value.trim();
	return allRows.value.filter(row => {
		const matchedReceipt = isReceived.value ? row.cost_js === "Y" : row.cost_js !== "Y";
		if (!matchedReceipt) return false;
		if (!key) return true;
		return (
			(row.cus_code ?? "").includes(key) ||
			(row.cus_name ?? "").includes(key) ||
			(row.cost_code ?? "").includes(key) ||
			(row.cost_name ?? "").includes(key)
		);
	});
});

const rows = computed(() => {
	const start = (pageIndex.value - 1) * pageSize.value;
	return filteredRows.value.slice(start, start + pageSize.value);
});

const total = computed(() => filteredRows.value.length);

const selectedIds = computed(() =>
	selectedRows.value.map(item => item.id).filter((id): id is string => !!id),
);

function formatDateTime(value?: string) {
	if (!value) return "";
	return String(value).replace("T", " ").replace(/\.\d+$/, "");
}

function costNameOf(row: CostRow) {
	return row.cost_name || costNameMap.value[row.cost_code ?? ""] || row.cost_code || "";
}

function customerNameOf(row: CostRow) {
	return row.cus_name || customerNameMap.value[row.cus_code ?? ""] || row.cus_code || "";
}

function loadData() {
	loading.value = true;
	listCostDetails(
		{ pageIndex: 1, pageSize: 1000 },
		(data: any) => {
			allRows.value = data?.rows ?? [];
			pageIndex.value = 1;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("费用数据加载失败");
		},
	);
}

function loadCostNames() {
	listCostNames(
		{ pageIndex: 1, pageSize: 500 },
		(data: any) => {
			const map: Record<string, string> = {};
			(data?.rows ?? []).forEach((item: any) => {
				if (item.cost_code) map[item.cost_code] = item.cost_name;
			});
			costNameMap.value = map;
		},
		() => {},
	);
}

function loadCustomerNames() {
	listCustomerBills(
		{ pageIndex: 1, pageSize: 500 },
		(data: any) => {
			const map: Record<string, string> = {};
			(data?.rows ?? []).forEach((item: any) => {
				if (item.customercode) map[item.customercode] = item.fullchinesename;
			});
			customerNameMap.value = map;
		},
		() => {},
	);
}

function handleSelectionChange(selection: CostRow[]) {
	selectedRows.value = selection;
}

function handlePageChange(page: number) {
	pageIndex.value = page;
}

function handleSizeChange(size: number) {
	pageSize.value = size;
	pageIndex.value = 1;
}

async function submitAction() {
	if (selectedIds.value.length === 0) {
		ElMessage.warning("请先勾选记录");
		return;
	}
	acting.value = true;
	try {
		if (isReceived.value) {
			await dischargeCostDetails(selectedIds.value);
			ElMessage.success("批量取消收款成功");
		} else {
			await chargeCostDetails(selectedIds.value);
			ElMessage.success("批量收款成功");
		}
		loadData();
	} catch (err: any) {
		ElMessage.error(err?.message || "操作失败");
	} finally {
		acting.value = false;
	}
}

onMounted(() => {
	loadData();
	loadCostNames();
	loadCustomerNames();
});
</script>

<template>
	<section class="receipt-list-root">
		<div class="tool-bar">
			<el-input
				v-model="keyword"
				placeholder="客户 / 费用编码或名称"
				clearable
				style="width: 220px"
				@clear="handlePageChange(1)"
			/>
			<el-button type="primary" @click="loadData">刷新</el-button>
			<el-button v-if="isReceived" :loading="acting" @click="submitAction">批量取消收款</el-button>
			<el-button v-else type="primary" :loading="acting" @click="submitAction">批量收款</el-button>
			<span class="tip">{{ isReceived ? "仅显示已收款费用" : "仅显示未收款费用" }}</span>
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
			<el-table-column type="index" label="序号" width="55" />
			<el-table-column prop="cus_code" label="客户编码" width="110" />
			<el-table-column label="客户名称" min-width="160" show-overflow-tooltip>
				<template #default="{ row }">{{ customerNameOf(row) }}</template>
			</el-table-column>
			<el-table-column prop="cost_code" label="费用编码" width="120" />
			<el-table-column label="费用名称" min-width="140" show-overflow-tooltip>
				<template #default="{ row }">{{ costNameOf(row) }}</template>
			</el-table-column>
			<el-table-column label="费用日期" width="120">
				<template #default="{ row }">{{ (row.cost_data ?? "").slice(0, 10) }}</template>
			</el-table-column>
			<el-table-column prop="cost_sl" label="数量" width="90" align="right" />
			<el-table-column prop="cost_unit" label="单位" width="70" />
			<el-table-column prop="day_cost_hsj" label="含税价" width="110" align="right" />
			<el-table-column label="收款状态" width="100" align="center">
				<template #default="{ row }">
					<el-tag :type="row.cost_js === 'Y' ? 'success' : 'info'">
						{{ row.cost_js === "Y" ? "已收款" : "未收款" }}
					</el-tag>
				</template>
			</el-table-column>
			<el-table-column label="创建时间" width="160">
				<template #default="{ row }">{{ formatDateTime(row.create_date) }}</template>
			</el-table-column>
		</el-table>

		<div class="pagination-bar">
			<el-pagination
				:current-page="pageIndex"
				:page-size="pageSize"
				:page-sizes="[10, 20, 50]"
				:total="total"
				layout="total, sizes, prev, pager, next"
				@current-change="handlePageChange"
				@size-change="handleSizeChange"
			/>
		</div>
	</section>
</template>

<style lang="scss" scoped>
.receipt-list-root {
	width: 100%;

	.tool-bar {
		display: flex;
		align-items: center;
		gap: 8px;
		margin: 12px 0;
	}

	.tip {
		color: #909399;
		font-size: 13px;
	}

	.pagination-bar {
		display: flex;
		justify-content: flex-end;
		margin-top: 16px;
	}
}
</style>
