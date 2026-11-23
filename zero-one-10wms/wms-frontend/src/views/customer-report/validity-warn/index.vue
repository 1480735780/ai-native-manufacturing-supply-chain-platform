<script lang="ts" setup>
import { computed, ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { listExpiryWarning } from "@/apis/customer-report/index";

definePage({
	meta: {
		menuType: "page",
		text: "效期预警",
		icon: "IconSetting",
	},
});

interface ExpiryWarningRow {
	id?: string;
	cusCode?: string;
	zhongWenQch?: string;
	goodsId?: string;
	shpBianMakh?: string;
	shpMingCheng?: string;
	baseGoodscount?: number;
	baseUnit?: string;
	kuctype?: string;
	goodsProData?: string;
	bzhiQi?: string;
	dqr?: string;
	resDate?: number;
	guoqibili?: string;
}

const loading = ref(false);
const rows = ref<ExpiryWarningRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
/** 是否只显示已过期/临期（剩余天数<=30天）的记录 */
const onlyWarning = ref(false);

const emptyQuery = {
	cusCode: "",
	zhongWenQch: "",
	goodsId: "",
	shpMingCheng: "",
};
const query = ref({ ...emptyQuery });

function formatRatio(value: any) {
	const num = Number(value);
	if (Number.isNaN(num)) return "";
	return `${(num * 100).toFixed(2)}%`;
}

function rowClassName({ row }: { row: ExpiryWarningRow }) {
	if (row.resDate === null || row.resDate === undefined) return "";
	if (row.resDate < 0) return "expired-row";
	if (row.resDate <= 30) return "warning-row";
	return "";
}

const displayRows = computed(() => {
	if (!onlyWarning.value) return rows.value;
	return rows.value.filter((row) => typeof row.resDate === "number" && row.resDate <= 30);
});

function loadData() {
	loading.value = true;
	listExpiryWarning(
		{
			pageIndex: pageIndex.value,
			pageSize: pageSize.value,
			...query.value,
		},
		(data: any) => {
			rows.value = data.rows ?? [];
			total.value = data.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("效期预警数据加载失败");
		},
	);
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	query.value = { ...emptyQuery };
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

onMounted(() => {
	loadData();
});
</script>

<template>
	<section class="validity-warn-root">
		<h2>效期预警</h2>

		<el-form :inline="true" class="filter-bar">
			<el-form-item label="客户编码">
				<el-input v-model="query.cusCode" placeholder="请输入客户编码" clearable style="width: 160px" />
			</el-form-item>
			<el-form-item label="客户名称">
				<el-input v-model="query.zhongWenQch" placeholder="请输入客户名称" clearable style="width: 200px" />
			</el-form-item>
			<el-form-item label="商品编码">
				<el-input v-model="query.goodsId" placeholder="请输入商品编码" clearable style="width: 160px" />
			</el-form-item>
			<el-form-item label="商品名称">
				<el-input v-model="query.shpMingCheng" placeholder="请输入商品名称" clearable style="width: 160px" />
			</el-form-item>
			<el-form-item>
				<el-button type="primary" @click="handleSearch">查询</el-button>
				<el-button @click="handleReset">重置</el-button>
			</el-form-item>
		</el-form>

		<div class="tool-bar">
			<el-checkbox v-model="onlyWarning">只看临期/过期（剩余天数 ≤ 30 天）</el-checkbox>
			<span class="tip">红色：已过期；橙色：30 天内到期</span>
		</div>

		<el-table
			v-loading="loading"
			:data="displayRows"
			:row-class-name="rowClassName"
			border
			stripe
			style="width: 100%"
		>
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="cusCode" label="客户编码" width="110" show-overflow-tooltip />
			<el-table-column prop="zhongWenQch" label="客户名称" min-width="180" show-overflow-tooltip />
			<el-table-column prop="goodsId" label="商品编码" width="110" show-overflow-tooltip />
			<el-table-column prop="shpBianMakh" label="客户商品编码" width="120" show-overflow-tooltip />
			<el-table-column prop="shpMingCheng" label="商品名称" min-width="140" show-overflow-tooltip />
			<el-table-column prop="baseGoodscount" label="库存数量" width="100" align="right" />
			<el-table-column prop="baseUnit" label="基本单位" width="90" />
			<el-table-column prop="kuctype" label="库存类型" width="110" show-overflow-tooltip />
			<el-table-column prop="goodsProData" label="生产日期" width="110" />
			<el-table-column prop="bzhiQi" label="保质期(天)" width="100" align="right" />
			<el-table-column prop="dqr" label="到期日" width="110" />
			<el-table-column label="剩余天数" width="130">
				<template #default="{ row }">
					<el-tag v-if="row.resDate < 0" type="danger">已过期 {{ Math.abs(row.resDate) }} 天</el-tag>
					<el-tag v-else-if="row.resDate <= 30" type="warning">{{ row.resDate }} 天</el-tag>
					<span v-else-if="row.resDate !== null && row.resDate !== undefined">{{ row.resDate }} 天</span>
					<span v-else>-</span>
				</template>
			</el-table-column>
			<el-table-column label="剩余比例" width="100" align="right">
				<template #default="{ row }">{{ formatRatio(row.guoqibili) }}</template>
			</el-table-column>
		</el-table>

		<div class="pagination-bar">
			<el-pagination
				:current-page="pageIndex"
				:page-size="pageSize"
				:page-sizes="[10, 20, 50, 100]"
				:total="total"
				layout="total, sizes, prev, pager, next, jumper"
				@current-change="handlePageChange"
				@size-change="handleSizeChange"
			/>
		</div>
	</section>
</template>

<style lang="scss" scoped>
.validity-warn-root {
	width: 100%;

	.filter-bar {
		margin-top: 12px;
	}

	.tool-bar {
		display: flex;
		align-items: center;
		gap: 16px;
		margin-bottom: 12px;
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

	:deep(.expired-row) {
		background-color: #fef0f0;
	}

	:deep(.warning-row) {
		background-color: #fdf6ec;
	}
}
</style>
