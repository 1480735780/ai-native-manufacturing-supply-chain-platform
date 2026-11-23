<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { listOutDetails, exportOutDetails, saveBlob } from "@/apis/outbound/index";

definePage({
	meta: {
		menuType: "page",
		text: "出库明细",
		icon: "IconSetting",
	},
});

interface DetailRow {
	id?: string;
	omSta?: string;
	omNoticeId?: string;
	imCusCode?: string;
	cusCode?: string;
	ocusName?: string;
	omBeizhu?: string;
	delvAddr?: string;
	goodsId?: string;
	goodsName?: string;
	baseGoodscount?: string;
	goodsUnit?: string;
	sumGoodscount?: string;
}

const loading = ref(false);
const rows = ref<DetailRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const query = ref({
	omNoticeId: "",
	imCusCode: "",
	cusCode: "",
	ocusName: "",
	goodsId: "",
	goodsName: "",
});

function loadData() {
	loading.value = true;
	listOutDetails(
		{ pageIndex: pageIndex.value, pageSize: pageSize.value, ...query.value },
		(data: any) => {
			rows.value = data.rows ?? [];
			total.value = data.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("出库明细加载失败");
		},
	);
}

function resetQuery() {
	query.value = {
		omNoticeId: "",
		imCusCode: "",
		cusCode: "",
		ocusName: "",
		goodsId: "",
		goodsName: "",
	};
	pageIndex.value = 1;
	loadData();
}

async function handleExport() {
	try {
		const blob = await exportOutDetails({ ...query.value });
		saveBlob(blob, "出库明细.xlsx");
		ElMessage.success("导出成功");
	} catch (e) {
		ElMessage.error("导出失败");
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

onMounted(loadData);
</script>

<template>
	<section class="outdetail-root">
		<el-form :model="query" inline class="query-bar">
			<el-form-item label="出库单号">
				<el-input v-model="query.omNoticeId" clearable style="width: 170px" />
			</el-form-item>
			<el-form-item label="第三方单号">
				<el-input v-model="query.imCusCode" clearable style="width: 150px" />
			</el-form-item>
			<el-form-item label="客户名称">
				<el-input v-model="query.ocusName" clearable style="width: 160px" />
			</el-form-item>
			<el-form-item label="商品编码">
				<el-input v-model="query.goodsId" clearable style="width: 140px" />
			</el-form-item>
			<el-form-item label="商品名称">
				<el-input v-model="query.goodsName" clearable style="width: 160px" />
			</el-form-item>
			<el-form-item>
				<el-button type="primary" @click="loadData">查询</el-button>
				<el-button @click="resetQuery">重置</el-button>
				<el-button type="success" @click="handleExport">导出</el-button>
			</el-form-item>
		</el-form>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%">
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="omNoticeId" label="出库单号" width="180" show-overflow-tooltip />
			<el-table-column prop="imCusCode" label="第三方单号" width="140" show-overflow-tooltip />
			<el-table-column prop="cusCode" label="第三方客户" width="120" />
			<el-table-column prop="ocusName" label="客户名称" min-width="160" show-overflow-tooltip />
			<el-table-column prop="goodsId" label="商品编码" width="130" show-overflow-tooltip />
			<el-table-column prop="goodsName" label="商品名称" min-width="170" show-overflow-tooltip />
			<el-table-column prop="baseGoodscount" label="出货数量" width="110" align="right" />
			<el-table-column prop="goodsUnit" label="单位" width="80" />
			<el-table-column prop="sumGoodscount" label="拣货数量" width="110" align="right" />
			<el-table-column prop="omSta" label="状态" width="100" />
			<el-table-column prop="delvAddr" label="收货地址" min-width="180" show-overflow-tooltip />
			<el-table-column prop="omBeizhu" label="备注" min-width="150" show-overflow-tooltip />
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
.outdetail-root {
	width: 100%;

	.query-bar {
		margin-top: 8px;
	}
}
</style>
