<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { listGoodsTypes } from "@/apis/reference/index";

definePage({
	meta: {
		menuType: "page",
		text: "产品属性",
		icon: "IconSetting",
	},
});

interface Row {
	id?: string;
	goods_type_code?: string;
	goods_type_name?: string;
}

const loading = ref(false);
const rows = ref<Row[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);

function loadData() {
	loading.value = true;
	listGoodsTypes(
		{ pageIndex: pageIndex.value, pageSize: pageSize.value },
		(data: any) => {
			rows.value = data.rows ?? [];
			total.value = data.total ?? rows.value.length;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("产品属性数据加载失败");
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
	<section class="product-attribute-root">
		<div class="tool-bar">
			<el-button type="primary" @click="loadData">刷新</el-button>
			<span class="tip">产品属性基础资料</span>
		</div>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%">
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="goods_type_code" label="属性代码" width="180" />
			<el-table-column prop="goods_type_name" label="属性名称" min-width="180" />
			<el-table-column prop="id" label="ID" min-width="200" show-overflow-tooltip />
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
.product-attribute-root {
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
