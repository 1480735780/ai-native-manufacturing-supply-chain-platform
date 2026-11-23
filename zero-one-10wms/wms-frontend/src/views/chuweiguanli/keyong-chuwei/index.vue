<script lang="ts" setup>
import { onMounted, reactive, ref } from "vue";
import { queryUsefulBinList } from "@/apis/chuweiguanli";

definePage({
	meta: {
		menuType: "page",
		text: "可用储位",
		icon: "IconSetting",
	},
});

const keyword = reactive({
	bin_store: "",
	ku_wei_bian_ma: "",
});

const loading = ref(false);
const rows = ref<any[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);

const loadData = () => {
	loading.value = true;
	queryUsefulBinList(
		{ pageIndex: pageIndex.value, pageSize: pageSize.value, ...keyword },
		data => {
			rows.value = data.rows || [];
			total.value = Number(data.total) || 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
		},
	);
};

const handleSearch = () => {
	pageIndex.value = 1;
	loadData();
};

const handlePageChange = (page: number) => {
	pageIndex.value = page;
	loadData();
};

const handleSizeChange = (size: number) => {
	pageSize.value = size;
	pageIndex.value = 1;
	loadData();
};

const detailText = (value: any) =>
	value === null || value === undefined || value === "" ? "-" : value;

onMounted(() => {
	loadData();
});
</script>

<template>
	<section class="chuwei-page">
		<h2>可用储位</h2>
		<div class="toolbar">
			<el-input v-model="keyword.bin_store" placeholder="所属仓库" clearable style="width: 160px" @keyup.enter="handleSearch" />
			<el-input v-model="keyword.ku_wei_bian_ma" placeholder="库位编码" clearable style="width: 170px" @keyup.enter="handleSearch" />
			<el-button type="primary" @click="handleSearch">查询</el-button>
		</div>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%">
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="bin_store" label="所属仓库" min-width="110" show-overflow-tooltip />
			<el-table-column prop="ku_wei_bian_ma" label="库位编码" min-width="130" show-overflow-tooltip />
			<el-table-column prop="ku_wei_shu_xing" label="库位属性" min-width="100" />
			<el-table-column prop="suo_shu_ke_hu" label="所属客户" min-width="110" show-overflow-tooltip />
			<el-table-column prop="zui_da_ti_ji" label="最大体积" width="90" />
			<el-table-column prop="shang_jia_ci_xu" label="上架次序" width="90" />
			<el-table-column prop="chang" label="长(cm)" width="90" />
			<el-table-column prop="kuan" label="宽(cm)" width="90" />
			<el-table-column prop="gao" label="高(cm)" width="90" />
			<el-table-column prop="zui_da_tuo_pan" label="最大托盘" width="90" />
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
.chuwei-page {
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
}
</style>
