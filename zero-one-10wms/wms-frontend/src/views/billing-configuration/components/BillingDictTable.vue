<script lang="ts" setup>
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { listBillingCosts, listCostTypes } from "@/apis/billing/index";

interface Props {
	title: string;
	tip?: string;
	mode?: "cost" | "costType";
}

interface Row {
	id?: string | number;
	cost_code?: string;
	cost_name?: string;
	cost_type_code?: string;
	cost_type?: string;
	create_name?: string;
	create_date?: string;
}

const props = withDefaults(defineProps<Props>(), {
	tip: "",
	mode: "cost",
});

const loading = ref(false);
const allRows = ref<Row[]>([]);
const pageIndex = ref(1);
const pageSize = ref(10);

const total = computed(() => allRows.value.length);
const rows = computed(() => {
	const start = (pageIndex.value - 1) * pageSize.value;
	return allRows.value.slice(start, start + pageSize.value);
});

function loadData() {
	loading.value = true;
	const fetcher = props.mode === "costType" ? listCostTypes : listBillingCosts;
	fetcher(
		{ pageIndex: 1, pageSize: 500 },
		(data: any) => {
			allRows.value = data.rows ?? data.data ?? [];
			pageIndex.value = 1;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error(`${props.title}数据加载失败`);
		},
	);
}

function handlePageChange(val: number) {
	pageIndex.value = val;
}

function handleSizeChange(val: number) {
	pageSize.value = val;
	pageIndex.value = 1;
}

onMounted(() => {
	loadData();
});
</script>

<template>
	<section class="billing-dict-root">
		<div class="tool-bar">
			<el-button type="primary" @click="loadData">刷新</el-button>
			<span class="tip">{{ tip || title }}</span>
		</div>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%">
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="cost_code" label="费用编码" width="180" show-overflow-tooltip />
			<el-table-column prop="cost_name" label="费用名称" min-width="180" show-overflow-tooltip />
			<el-table-column v-if="mode === 'cost'" prop="cost_type_code" label="费用类型编码" min-width="180" />
			<el-table-column v-else prop="cost_type" label="费用类型" min-width="180" />
			<el-table-column v-if="mode === 'costType'" prop="create_name" label="创建人" width="120" />
			<el-table-column v-if="mode === 'costType'" prop="create_date" label="创建日期" width="180" />
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
.billing-dict-root {
	width: 100%;

	.tool-bar {
		display: flex;
		align-items: center;
		gap: 16px;
		margin: 12px 0;
	}

	.tip {
		color: #909399;
		font-size: 13px;
	}
}
</style>
