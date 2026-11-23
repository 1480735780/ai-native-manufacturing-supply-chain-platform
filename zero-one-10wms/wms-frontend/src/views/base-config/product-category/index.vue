<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { listGoodsCategories } from "@/apis/reference/index";

definePage({
	meta: {
		menuType: "page",
		text: "商品类目",
		icon: "IconSetting",
	},
});

interface Row {
	id?: number;
	category_code?: string;
	category_name?: string;
	category_level?: number;
	pid?: number;
	top_node?: string;
}

const loading = ref(false);
const rows = ref<Row[]>([]);

function loadData() {
	loading.value = true;
	listGoodsCategories(
		(data: any) => {
			rows.value = data.DTOList ?? data.rows ?? [];
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("商品类目数据加载失败");
		},
	);
}

onMounted(() => {
	loadData();
});
</script>

<template>
	<section class="product-category-root">
		<div class="tool-bar">
			<el-button type="primary" @click="loadData">刷新</el-button>
			<span class="tip">商品类目树（按层级展示）</span>
		</div>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%" row-key="id">
			<el-table-column prop="category_code" label="类目代码" width="200" />
			<el-table-column prop="category_name" label="类目名称" min-width="200" />
			<el-table-column prop="category_level" label="层级" width="100" align="center" />
			<el-table-column prop="pid" label="上级ID" width="120" align="center" />
			<el-table-column prop="top_node" label="是否顶级" width="110" align="center" />
		</el-table>
	</section>
</template>

<style lang="scss" scoped>
.product-category-root {
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
