<script lang="ts" setup>
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import {
	listCostSums,
	downloadCostSum,
	listCostNames,
	saveBlob,
} from "@/apis/cost-management/index";

definePage({
	meta: {
		menuType: "page",
		text: "费用合计",
		icon: "IconSetting",
	},
});

interface CostSumRow {
	costdate?: string;
	client?: string;
	clientname?: string;
	cost?: string;
	costname?: string;
	number?: string;
	unit?: string;
	orgprice?: string;
	notax?: string;
	tax?: string;
	taxprice?: string;
}

const loading = ref(false);
const exporting = ref(false);
const rows = ref<CostSumRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);

const searchForm = reactive({
	client: "",
	clientname: "",
	cost: "",
	costname: "",
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
		client: searchForm.client,
		clientname: searchForm.clientname,
		cost: searchForm.cost,
		costname: searchForm.costname,
	};
	if (searchForm.dateRange.length === 2) {
		query.datebegin = `${searchForm.dateRange[0]} 00:00:00`;
		query.dateend = `${searchForm.dateRange[1]} 23:59:59`;
	}
	return query;
}

function loadData() {
	loading.value = true;
	listCostSums(
		{ pageIndex: pageIndex.value, pageSize: pageSize.value, ...buildQuery() },
		(data: any) => {
			rows.value = data?.rows ?? [];
			total.value = data?.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("费用合计加载失败");
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
	searchForm.costname = costNameMap.value[code] ?? "";
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	searchForm.client = "";
	searchForm.clientname = "";
	searchForm.cost = "";
	searchForm.costname = "";
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
		const blob = await downloadCostSum(buildQuery());
		saveBlob(blob, `费用合计_${Date.now()}.xlsx`);
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
	<section class="cost-sum-root">
		<h2>费用合计</h2>

		<el-form :inline="true" class="filter-bar">
			<el-form-item label="客户编码">
				<el-input v-model="searchForm.client" placeholder="客户编码" clearable style="width: 130px" />
			</el-form-item>
			<el-form-item label="客户名称">
				<el-input v-model="searchForm.clientname" placeholder="客户名称" clearable style="width: 150px" />
			</el-form-item>
			<el-form-item label="费用名称">
				<el-select
					v-model="searchForm.cost"
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
				<template #default="{ row }">{{ formatDate(row.costdate) }}</template>
			</el-table-column>
			<el-table-column prop="client" label="客户编码" width="120" />
			<el-table-column label="客户名称" min-width="170" show-overflow-tooltip>
				<template #default="{ row }">{{ row.clientname || row.client }}</template>
			</el-table-column>
			<el-table-column prop="cost" label="费用编码" width="120" />
			<el-table-column label="费用名称" min-width="150" show-overflow-tooltip>
				<template #default="{ row }">{{ row.costname || costNameMap[row.cost] || row.cost }}</template>
			</el-table-column>
			<el-table-column prop="number" label="数量" width="100" align="right" />
			<el-table-column prop="unit" label="单位" width="80" />
			<el-table-column prop="orgprice" label="原价" width="100" align="right" />
			<el-table-column prop="notax" label="不含税价" width="110" align="right" />
			<el-table-column prop="tax" label="税额" width="100" align="right" />
			<el-table-column prop="taxprice" label="含税价" width="110" align="right" />
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
.cost-sum-root {
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
