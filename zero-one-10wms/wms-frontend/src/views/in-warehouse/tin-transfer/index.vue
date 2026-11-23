<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { listTinTransfer, generateTinTransfer } from "@/apis/kuneiguanli/index";

definePage({
	meta: {
		menuType: "page",
		text: "托盘转移",
		icon: "IconSetting",
	},
});

interface TinRow {
	id?: string;
	moveDate?: string;
	inventoryType?: string;
	bin?: string;
	tin?: string;
	cusCode?: string;
	cusName?: string;
	goodsID?: string;
	goodsNum?: number;
	goodsName?: string;
	produceDate?: string;
	produceShelfLife?: string;
	produceUnit?: string;
	moveSta?: string;
}

const loading = ref(false);
const rows = ref<TinRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const selectedRows = ref<TinRow[]>([]);
const targetBin = ref("");
const tableRef = ref();

const query = ref({
	inventoryType: "",
	bin: "",
	tin: "",
	cusCode: "",
	cusName: "",
	goodsID: "",
	goodsName: "",
	produceDate: "",
	toProduceDate: "",
});

function loadData() {
	loading.value = true;
	listTinTransfer(
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
			ElMessage.error("可转移列表加载失败");
		},
	);
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	query.value = {
		inventoryType: "",
		bin: "",
		tin: "",
		cusCode: "",
		cusName: "",
		goodsID: "",
		goodsName: "",
		produceDate: "",
		toProduceDate: "",
	};
	pageIndex.value = 1;
	loadData();
}

function handleSelectionChange(selection: TinRow[]) {
	selectedRows.value = selection;
}

function handleGenerate() {
	if (selectedRows.value.length === 0) {
		ElMessage.warning("请先勾选需要转移的库存行");
		return;
	}
	if (!targetBin.value.trim()) {
		ElMessage.warning("请填写目标储位");
		return;
	}

	const items = selectedRows.value.map((row) => ({
		id: row.id,
		inventoryType: row.inventoryType,
		bin: row.bin,
		tin: row.tin,
		cusCode: row.cusCode,
		cusName: row.cusName,
		goodsID: row.goodsID,
		goodsNum: row.goodsNum,
		goodsName: row.goodsName,
		produceDate: row.produceDate,
		produceShelfLife: row.produceShelfLife,
		produceUnit: row.produceUnit,
		toBin: targetBin.value.trim(),
	}));

	loading.value = true;
	generateTinTransfer(
		{ items },
		(data: any) => {
			loading.value = false;
			ElMessage.success(`已生成 ${data} 条托盘转移任务`);
			tableRef.value?.clearSelection();
			selectedRows.value = [];
			loadData();
		},
		() => {
			loading.value = false;
			ElMessage.error("生成托盘转移任务失败");
		},
	);
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
	<section class="tin-transfer-root">
		<el-card shadow="never" class="query-card">
			<el-form :model="query" inline label-width="80px">
				<el-form-item label="库存类型">
					<el-input v-model="query.inventoryType" clearable placeholder="库存类型" style="width: 130px" />
				</el-form-item>
				<el-form-item label="储位">
					<el-input v-model="query.bin" clearable placeholder="储位" style="width: 130px" />
				</el-form-item>
				<el-form-item label="托盘">
					<el-input v-model="query.tin" clearable placeholder="托盘" style="width: 130px" />
				</el-form-item>
				<el-form-item label="货主编码">
					<el-input v-model="query.cusCode" clearable placeholder="货主编码" style="width: 130px" />
				</el-form-item>
				<el-form-item label="货主名称">
					<el-input v-model="query.cusName" clearable placeholder="货主名称" style="width: 150px" />
				</el-form-item>
				<el-form-item label="商品编码">
					<el-input v-model="query.goodsID" clearable placeholder="商品编码" style="width: 140px" />
				</el-form-item>
				<el-form-item label="商品名称">
					<el-input v-model="query.goodsName" clearable placeholder="商品名称" style="width: 150px" />
				</el-form-item>
				<el-form-item label="生产日期">
					<el-date-picker
						v-model="query.produceDate"
						type="date"
						value-format="YYYY-MM-DD"
						placeholder="开始日期"
						style="width: 140px"
					/>
				</el-form-item>
				<el-form-item label="至">
					<el-date-picker
						v-model="query.toProduceDate"
						type="date"
						value-format="YYYY-MM-DD"
						placeholder="结束日期"
						style="width: 140px"
					/>
				</el-form-item>
				<el-form-item>
					<el-button type="primary" @click="handleSearch">查询</el-button>
					<el-button @click="handleReset">重置</el-button>
				</el-form-item>
			</el-form>
		</el-card>

		<el-card shadow="never" class="tool-card">
			<div class="tool-bar">
				<el-input
					v-model="targetBin"
					clearable
					placeholder="请输入目标储位"
					style="width: 200px"
				/>
				<el-button type="primary" :disabled="selectedRows.length === 0" @click="handleGenerate">
					批量生成任务（{{ selectedRows.length }}）
				</el-button>
				<span class="tip">勾选库存行后填写目标储位，批量生成托盘转移任务</span>
			</div>
		</el-card>

		<el-table
			ref="tableRef"
			v-loading="loading"
			:data="rows"
			border
			stripe
			style="width: 100%"
			@selection-change="handleSelectionChange"
		>
			<el-table-column type="selection" width="50" />
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="moveDate" label="移动日期" width="170" />
			<el-table-column prop="inventoryType" label="库存类型" width="100" />
			<el-table-column prop="bin" label="储位" width="120" show-overflow-tooltip />
			<el-table-column prop="tin" label="托盘" width="120" show-overflow-tooltip />
			<el-table-column prop="cusCode" label="货主编码" width="110" />
			<el-table-column prop="cusName" label="货主名称" min-width="150" show-overflow-tooltip />
			<el-table-column prop="goodsID" label="商品编码" width="120" show-overflow-tooltip />
			<el-table-column prop="goodsName" label="商品名称" min-width="150" show-overflow-tooltip />
			<el-table-column prop="goodsNum" label="数量" width="90" align="right" />
			<el-table-column prop="produceUnit" label="单位" width="80" />
			<el-table-column prop="produceDate" label="生产日期" width="120" />
			<el-table-column prop="produceShelfLife" label="保质期" width="90" />
			<el-table-column prop="moveSta" label="状态" width="100" />
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
.tin-transfer-root {
	width: 100%;
}
.query-card {
	margin-bottom: 12px;
}
.tool-card {
	margin-bottom: 12px;
}
.tool-bar {
	display: flex;
	align-items: center;
	gap: 12px;
}
.tip {
	color: var(--el-text-color-secondary);
	font-size: 12px;
}
</style>
