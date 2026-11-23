<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { listStock, exportStock } from "@/apis/stock/index";
import { saveBlob } from "@/apis/purchase/index";

definePage({
	meta: {
		menuType: "page",
		text: "库存查询",
		icon: "IconSetting",
	},
});

interface StockRow {
	kuctype?: string;
	kuWeiBianMa?: string;
	binId?: string;
	cusCode?: string;
	zhongWenQch?: string;
	goodsCode?: string;
	shpMingCheng?: string;
	baseGoodscount?: number;
	baseUnit?: string;
	goodsProData?: string;
	bzhiQi?: string;
	dqr?: string;
}

const loading = ref(false);
const exporting = ref(false);
const rows = ref<StockRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);

const query = ref({
	kuWeiBianMa: "",
	binId: "",
	cusCode: "",
	zhongWenQch: "",
	goodsCode: "",
	shpMingCheng: "",
});

function kucunTypeText(value?: string) {
	if (value === "1") return "托盘上";
	if (value === "2") return "货架上";
	return value ?? "";
}

function loadData() {
	loading.value = true;
	listStock(
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
			ElMessage.error("库存数据加载失败");
		},
	);
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	query.value = {
		kuWeiBianMa: "",
		binId: "",
		cusCode: "",
		zhongWenQch: "",
		goodsCode: "",
		shpMingCheng: "",
	};
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
		const blob = await exportStock({ ...query.value });
		saveBlob(blob, `库存查询_${Date.now()}.xlsx`);
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
	<section class="stock-inquiry-root">
		<el-card shadow="never" class="query-card">
			<el-form :model="query" inline label-width="80px">
				<el-form-item label="储位">
					<el-input v-model="query.kuWeiBianMa" clearable placeholder="请输入储位" style="width: 150px" />
				</el-form-item>
				<el-form-item label="托盘">
					<el-input v-model="query.binId" clearable placeholder="请输入托盘" style="width: 150px" />
				</el-form-item>
				<el-form-item label="客户编码">
					<el-input v-model="query.cusCode" clearable placeholder="请输入客户编码" style="width: 150px" />
				</el-form-item>
				<el-form-item label="客户名称">
					<el-input v-model="query.zhongWenQch" clearable placeholder="请输入客户名称" style="width: 170px" />
				</el-form-item>
				<el-form-item label="商品编码">
					<el-input v-model="query.goodsCode" clearable placeholder="请输入商品编码" style="width: 150px" />
				</el-form-item>
				<el-form-item label="商品名称">
					<el-input v-model="query.shpMingCheng" clearable placeholder="请输入商品名称" style="width: 150px" />
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

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%; margin-top: 12px">
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column label="库存类型" width="100">
				<template #default="{ row }">{{ kucunTypeText(row.kuctype) }}</template>
			</el-table-column>
			<el-table-column prop="kuWeiBianMa" label="储位" width="110" show-overflow-tooltip />
			<el-table-column prop="binId" label="托盘" width="110" show-overflow-tooltip />
			<el-table-column prop="cusCode" label="客户编码" width="100" />
			<el-table-column prop="zhongWenQch" label="客户名称" min-width="170" show-overflow-tooltip />
			<el-table-column prop="goodsCode" label="商品编码" width="110" show-overflow-tooltip />
			<el-table-column prop="shpMingCheng" label="商品名称" min-width="130" show-overflow-tooltip />
			<el-table-column prop="baseGoodscount" label="数量" width="90" align="right" />
			<el-table-column prop="baseUnit" label="单位" width="70" />
			<el-table-column prop="goodsProData" label="生产日期" width="110" />
			<el-table-column prop="bzhiQi" label="保质期(天)" width="100" align="right" />
			<el-table-column prop="dqr" label="到期日" width="110" />
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
.stock-inquiry-root {
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
