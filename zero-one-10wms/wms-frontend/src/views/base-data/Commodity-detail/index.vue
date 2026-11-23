<script lang="ts" setup>
import { onMounted, reactive, ref } from "vue";
import { listGoods, getGoodsDetail } from "@/apis/base-data/index.js";
import { useBaseDataPage } from "../composables/use-base-data-page";
import { usePermission } from "@/composables/use-permission";

definePage({
	meta: {
		menuType: "page",
		text: "商品明细",
		icon: "IconSetting",
	},
});

const keyword = reactive({
	shpMingCheng: "",
	shpBianMa: "",
});

const { loading, rows, total, pageIndex, pageSize, setQueryBuilder, loadData, handleSearch, handlePageChange, handleSizeChange } =
	useBaseDataPage({
		listApi: listGoods,
		rowKey: (row) => row.shpBianMa,
		rowLabel: (row) => row.shpMingCheng || row.shpBianMa,
		fileName: "商品明细",
		loadFailText: "商品明细数据加载失败",
	});

/** 只读页面：商品明细仅提供查看能力 */
const { canWrite } = usePermission();
void canWrite;

setQueryBuilder(() => ({
	shpMingCheng: keyword.shpMingCheng,
	shpBianMa: keyword.shpBianMa,
}));

/* ============================ 详情抽屉 ============================ */

const detailVisible = ref(false);
const detailLoading = ref(false);
const detail = ref<any>({});

function openDetail(row: any) {
	detailVisible.value = true;
	detailLoading.value = true;
	detail.value = { ...row };
	getGoodsDetail(
		row.shpBianMa,
		(data: any) => {
			detail.value = data ?? row;
			detailLoading.value = false;
		},
		() => {
			detailLoading.value = false;
		},
	);
}

function detailText(value: any) {
	return value === null || value === undefined || value === "" ? "-" : value;
}

onMounted(() => {
	loadData();
});
</script>

<template>
	<section class="base-data-page">
		<h2>商品明细</h2>
		<div class="toolbar">
			<el-input v-model="keyword.shpMingCheng" placeholder="商品名称" clearable style="width: 180px" @keyup.enter="handleSearch" />
			<el-input v-model="keyword.shpBianMa" placeholder="商品编码" clearable style="width: 170px" @keyup.enter="handleSearch" />
			<el-button type="primary" @click="handleSearch">查询</el-button>
		</div>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%">
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="shpBianMa" label="商品编码" min-width="140" show-overflow-tooltip />
			<el-table-column prop="shpMingCheng" label="商品名称" min-width="180" show-overflow-tooltip />
			<el-table-column prop="ywMingCheng" label="英文名" min-width="140" show-overflow-tooltip />
			<el-table-column prop="shpPinPai" label="品牌" min-width="120" show-overflow-tooltip />
			<el-table-column prop="categoryCode" label="商品类目" min-width="120" show-overflow-tooltip />
			<el-table-column prop="shlDanWei" label="计量单位" width="90" />
			<el-table-column prop="shpGuiGe" label="规格" min-width="110" show-overflow-tooltip />
			<el-table-column prop="shpTiaoMa" label="条码" min-width="130" show-overflow-tooltip />
			<el-table-column prop="bzhiQi" label="保质期" width="80" />
			<el-table-column prop="chpShuXing" label="产品属性" min-width="100" show-overflow-tooltip />
			<el-table-column label="操作" width="90" fixed="right">
				<template #default="{ row }">
					<el-button link type="primary" @click="openDetail(row)">查看</el-button>
				</template>
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

		<el-drawer v-model="detailVisible" title="商品明细详情" size="560px">
			<div v-loading="detailLoading" class="detail-list">
				<p class="detail-group">基础信息</p>
				<p><span>商品编码</span>{{ detailText(detail.shpBianMa) }}</p>
				<p><span>商品名称</span>{{ detailText(detail.shpMingCheng) }}</p>
				<p><span>英文名</span>{{ detailText(detail.ywMingCheng) }}</p>
				<p><span>日文名</span>{{ detailText(detail.rwMingCheng) }}</p>
				<p><span>商品品牌</span>{{ detailText(detail.shpPinPai) }}</p>
				<p><span>商品类目</span>{{ detailText(detail.categoryCode) }}</p>
				<p><span>产品属性</span>{{ detailText(detail.chpShuXing) }}</p>
				<p><span>条码</span>{{ detailText(detail.shpTiaoMa) }}</p>
				<p class="detail-group">规格与单位</p>
				<p><span>计量单位</span>{{ detailText(detail.shlDanWei) }}</p>
				<p><span>规格</span>{{ detailText(detail.shpGuiGe) }}</p>
				<p><span>保质期</span>{{ detailText(detail.bzhiQi) }}</p>
				<p><span>体积(cm³)</span>{{ detailText(detail.tiJiCm) }}</p>
				<p><span>重量(kg)</span>{{ detailText(detail.zhlKg) }}</p>
				<p><span>拆零单位</span>{{ detailText(detail.jshDanWei) }}</p>
				<p><span>拆零数量</span>{{ detailText(detail.chlShl) }}</p>
				<p class="detail-group">库存与其他</p>
				<p><span>货主客户</span>{{ detailText(detail.sysCompanyCode) }}</p>
				<p><span>SKU</span>{{ detailText(detail.sku) }}</p>
				<p><span>最小库存</span>{{ detailText(detail.minStock) }}</p>
				<p><span>验收天数</span>{{ detailText(detail.acceptanceDays) }}</p>
				<p><span>码盘单层</span>{{ detailText(detail.mpDanCeng) }}</p>
				<p><span>码盘层高</span>{{ detailText(detail.mpCengGao) }}</p>
			</div>
			<template #footer>
				<el-button @click="detailVisible = false">关闭</el-button>
			</template>
		</el-drawer>
	</section>
</template>

<style lang="scss" scoped>
.base-data-page {
	width: 100%;
	.toolbar {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		margin: 12px 0;
	}
	.pagination-bar {
		display: flex;
		justify-content: flex-end;
		margin-top: 12px;
	}
	.detail-list {
		p {
			display: flex;
			gap: 12px;
			margin: 0;
			padding: 10px 0;
			border-bottom: 1px solid var(--el-border-color-lighter);
			span:first-child {
				width: 96px;
				color: var(--el-text-color-secondary);
				flex-shrink: 0;
			}
		}
		.detail-group {
			margin-top: 8px;
			font-weight: 600;
			color: var(--el-text-color-primary);
			background: var(--el-fill-color-light);
			padding-left: 8px;
		}
	}
}
</style>
