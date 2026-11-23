<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { listMovingBin, exportMovingBin, saveBlob } from "@/apis/inventory/index";

definePage({
	meta: {
		menuType: "page",
		text: "动仓盘点",
		icon: "IconSetting",
	},
});

interface MovingRow {
	id?: string;
	bin_id?: string;
	tin_id?: string;
	goods_id?: string;
	goods_name?: string;
	goods_specification?: string;
	goods_pro_date?: string;
	save_date?: string;
	due_date?: string;
	total_stock?: string;
	last_pick_time?: string;
	avail_stock?: string;
	to_be_taken_down?: string;
	goods_unit?: string;
}

const loading = ref(false);
const rows = ref<MovingRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const exporting = ref(false);

const query = ref({
	bin_id: "",
	tin_id: "",
	goods_id: "",
	goods_name: "",
});

function loadData() {
	loading.value = true;
	listMovingBin(
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
			ElMessage.error("动仓盘点数据加载失败");
		},
	);
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	query.value = { bin_id: "", tin_id: "", goods_id: "", goods_name: "" };
	pageIndex.value = 1;
	loadData();
}

async function handleExport() {
	exporting.value = true;
	try {
		const blob = await exportMovingBin(query.value);
		saveBlob(blob, "动仓盘点数据.xlsx");
	} catch {
		ElMessage.error("导出动仓盘点数据失败");
	} finally {
		exporting.value = false;
	}
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
	<section class="moving-count-root">
		<el-card shadow="never" class="query-card">
			<el-form :model="query" inline label-width="80px">
				<el-form-item label="储位">
					<el-input v-model="query.bin_id" clearable placeholder="请输入储位" style="width: 140px" />
				</el-form-item>
				<el-form-item label="托盘">
					<el-input v-model="query.tin_id" clearable placeholder="请输入托盘" style="width: 140px" />
				</el-form-item>
				<el-form-item label="商品编码">
					<el-input v-model="query.goods_id" clearable placeholder="请输入商品编码" style="width: 140px" />
				</el-form-item>
				<el-form-item label="商品名称">
					<el-input v-model="query.goods_name" clearable placeholder="请输入商品名称" style="width: 150px" />
				</el-form-item>
				<el-form-item>
					<el-button type="primary" @click="handleSearch">查询</el-button>
					<el-button @click="handleReset">重置</el-button>
					<el-button :loading="exporting" @click="handleExport">导出</el-button>
				</el-form-item>
			</el-form>
		</el-card>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%">
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="bin_id" label="储位" width="120" show-overflow-tooltip />
			<el-table-column prop="tin_id" label="托盘" width="120" show-overflow-tooltip />
			<el-table-column prop="goods_id" label="商品编码" width="120" show-overflow-tooltip />
			<el-table-column prop="goods_name" label="商品名称" min-width="160" show-overflow-tooltip />
			<el-table-column prop="goods_specification" label="规格" width="120" show-overflow-tooltip />
			<el-table-column prop="goods_pro_date" label="生产日期" width="120" />
			<el-table-column prop="save_date" label="入库日期" width="120" />
			<el-table-column prop="due_date" label="到期日期" width="120" />
			<el-table-column prop="total_stock" label="总库存" width="100" align="right" />
			<el-table-column prop="avail_stock" label="可用库存" width="100" align="right" />
			<el-table-column prop="to_be_taken_down" label="待下架" width="100" align="right" />
			<el-table-column prop="last_pick_time" label="最近拣货时间" width="170" />
			<el-table-column prop="goods_unit" label="单位" width="80" />
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
.moving-count-root {
	width: 100%;
}
</style>
