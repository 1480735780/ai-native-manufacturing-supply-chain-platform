<script lang="ts" setup>
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import {
	listReceivedFees,
	exportReceivedFees,
	listCostNames,
	saveBlob,
} from "@/apis/cost-management/index";

definePage({
	meta: {
		menuType: "page",
		text: "已收款费用合计",
		icon: "IconSetting",
	},
});

interface ReceivedRow {
	id?: string;
	feedate?: string;
	customers?: string;
	customersname?: string;
	fees?: string;
	feesname?: string;
	billingquantity?: string;
	unityofquantity?: string;
	originalprice?: string;
	tax_exclusiveprice?: string;
	taxamount?: string;
	taxinclusiveprice?: string;
}

const loading = ref(false);
const exporting = ref(false);
const rows = ref<ReceivedRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);

const searchForm = reactive({
	customers: "",
	customersname: "",
	fees: "",
	feesname: "",
	dateRange: [] as string[],
});

const costNameOptions = ref<{ code: string; name: string }[]>([]);
const costNameMap = ref<Record<string, string>>({});

function formatDate(value?: string) {
	if (!value) return "";
	return String(value).replace("T", " ").replace(/\.\d+$/, "");
}

function buildQuery() {
	const query: Record<string, any> = {
		customers: searchForm.customers,
		customersname: searchForm.customersname,
		fees: searchForm.fees,
		feesname: searchForm.feesname,
	};
	if (searchForm.dateRange.length === 2) {
		query.feestartdate = `${searchForm.dateRange[0]} 00:00:00`;
		query.feeenddate = `${searchForm.dateRange[1]} 23:59:59`;
	}
	return query;
}

function loadData() {
	loading.value = true;
	listReceivedFees(
		{ pageIndex: pageIndex.value, pageSize: pageSize.value, ...buildQuery() },
		(data: any) => {
			rows.value = data?.rows ?? [];
			total.value = data?.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("已收款费用加载失败");
		},
	);
}

function loadCostNames() {
	listCostNames(
		{ pageIndex: 1, pageSize: 500 },
		(data: any) => {
			const list = data?.rows ?? [];
			costNameOptions.value = list.map((item: any) => ({
				code: item.cost_code,
				name: item.cost_name,
			}));
			const map: Record<string, string> = {};
			list.forEach((item: any) => {
				if (item.cost_code) map[item.cost_code] = item.cost_name;
			});
			costNameMap.value = map;
		},
		() => {},
	);
}

function handleCostChange(code: string) {
	searchForm.feesname = costNameMap.value[code] ?? "";
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	searchForm.customers = "";
	searchForm.customersname = "";
	searchForm.fees = "";
	searchForm.feesname = "";
	searchForm.dateRange = [];
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
		const blob = await exportReceivedFees(buildQuery());
		saveBlob(blob, `已收款费用合计_${Date.now()}.xlsx`);
		ElMessage.success("导出成功");
	} catch (err: any) {
		ElMessage.error(err?.message || "导出失败");
	} finally {
		exporting.value = false;
	}
}

onMounted(() => {
	loadData();
	loadCostNames();
});
</script>

<template>
	<section class="received-fees-root">
		<h2>已收款费用合计</h2>

		<el-form :inline="true" class="filter-bar">
			<el-form-item label="客户编码">
				<el-input v-model="searchForm.customers" placeholder="客户编码" clearable style="width: 130px" />
			</el-form-item>
			<el-form-item label="客户名称">
				<el-input v-model="searchForm.customersname" placeholder="客户名称" clearable style="width: 150px" />
			</el-form-item>
			<el-form-item label="费用名称">
				<el-select
					v-model="searchForm.fees"
					placeholder="选择费用名称"
					clearable
					filterable
					style="width: 180px"
					@change="handleCostChange"
				>
					<el-option
						v-for="item in costNameOptions"
						:key="item.code"
						:label="`${item.name}（${item.code}）`"
						:value="item.code"
					/>
				</el-select>
			</el-form-item>
			<el-form-item label="费用日期">
				<el-date-picker
					v-model="searchForm.dateRange"
					type="daterange"
					value-format="YYYY-MM-DD"
					start-placeholder="开始日期"
					end-placeholder="结束日期"
					style="width: 240px"
				/>
			</el-form-item>
			<el-form-item>
				<el-button type="primary" @click="handleSearch">查询</el-button>
				<el-button @click="handleReset">重置</el-button>
				<el-button type="warning" :loading="exporting" @click="handleExport">导出数据</el-button>
			</el-form-item>
		</el-form>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%">
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column label="费用日期" width="150">
				<template #default="{ row }">{{ formatDate(row.feedate) }}</template>
			</el-table-column>
			<el-table-column prop="customers" label="客户编码" width="120" />
			<el-table-column label="客户名称" min-width="170" show-overflow-tooltip>
				<template #default="{ row }">{{ row.customersname || row.customers }}</template>
			</el-table-column>
			<el-table-column prop="fees" label="费用编码" width="120" />
			<el-table-column label="费用名称" min-width="150" show-overflow-tooltip>
				<template #default="{ row }">{{ row.feesname || costNameMap[row.fees] || row.fees }}</template>
			</el-table-column>
			<el-table-column prop="billingquantity" label="计费数量" width="100" align="right" />
			<el-table-column prop="unityofquantity" label="计费单位" width="100" />
			<el-table-column prop="originalprice" label="原价" width="100" align="right" />
			<el-table-column prop="tax_exclusiveprice" label="不含税价" width="110" align="right" />
			<el-table-column prop="taxamount" label="税额" width="100" align="right" />
			<el-table-column prop="taxinclusiveprice" label="含税价" width="110" align="right" />
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
	</section>
</template>

<style lang="scss" scoped>
.received-fees-root {
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
