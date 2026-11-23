<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { listCustomerStock } from "@/apis/customer-report/index";

definePage({
	meta: {
		menuType: "page",
		text: "客户库存",
		icon: "IconSetting",
	},
});

interface CustomerStockRow {
	id?: string;
	cusCode?: string;
	zhongWenQch?: string;
	goodsId?: string;
	shpMingCheng?: string;
	baseGoodscount?: number;
	baseUnit?: string;
	kuWeiBianMa?: string;
	binId?: string;
	goodsProData?: string;
	bzhiQi?: string;
	dqr?: string;
	kuctype?: string;
}

const loading = ref(false);
const rows = ref<CustomerStockRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);

const emptyQuery = {
	cusCode: "",
	zhongWenQch: "",
	goodsId: "",
	shpMingCheng: "",
};
const query = ref({ ...emptyQuery });

function loadData() {
	loading.value = true;
	listCustomerStock(
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
			ElMessage.error("客户库存数据加载失败");
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
	<section class="customer-stock-root">
		<h2>客户库存</h2>

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

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%">
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="cusCode" label="客户编码" width="110" show-overflow-tooltip />
			<el-table-column prop="zhongWenQch" label="客户名称" min-width="180" show-overflow-tooltip />
			<el-table-column prop="goodsId" label="商品编码" width="110" show-overflow-tooltip />
			<el-table-column prop="shpMingCheng" label="商品名称" min-width="140" show-overflow-tooltip />
			<el-table-column prop="baseGoodscount" label="库存数量" width="100" align="right" />
			<el-table-column prop="baseUnit" label="单位" width="70" />
			<el-table-column prop="kuWeiBianMa" label="储位" width="110" show-overflow-tooltip />
			<el-table-column prop="binId" label="托盘" width="100" show-overflow-tooltip />
			<el-table-column prop="kuctype" label="库存类型" width="110" show-overflow-tooltip />
			<el-table-column prop="goodsProData" label="生产日期" width="110" />
			<el-table-column prop="bzhiQi" label="保质期(天)" width="100" align="right" />
			<el-table-column prop="dqr" label="到期日" width="110" />
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
.customer-stock-root {
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
