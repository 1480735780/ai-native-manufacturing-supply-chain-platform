<script lang="ts" setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { queryChuweiList, getStoreNameList, exportChuweiDetail, importChuweiDetail, saveBlob } from "@/apis/chuweiguanli";

definePage({
	meta: {
		menuType: "page",
		text: "储位信息",
		icon: "IconSetting",
	},
});

const keyword = reactive({
	bin_store: "",
	ku_wei_bian_ma: "",
	ku_wei_lei_xing: "",
});

const loading = ref(false);
const rows = ref<any[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const storeOptions = ref<string[]>([]);

const loadData = () => {
	loading.value = true;
	queryChuweiList(
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

/** 导出储位明细：后端返回 Excel 文件流，直接触发浏览器下载 */
const exporting = ref(false);
const handleExport = () => {
	exporting.value = true;
	exportChuweiDetail(
		blob => {
			exporting.value = false;
			saveBlob(blob, `储位明细_${Date.now()}.xlsx`);
			ElMessage.success("导出成功，已开始下载");
		},
		() => {
			exporting.value = false;
			ElMessage.error("导出失败，请稍后重试");
		},
	);
};

/** 导入储位明细 */
const importing = ref(false);
const uploadRef = ref();
const handleImportFile = (uploadFile: any) => {
	const file = uploadFile.raw;
	if (!file || !/\.xlsx?$/i.test(file.name)) {
		ElMessage.warning("请选择 xlsx 格式的 Excel 文件");
		return;
	}
	importing.value = true;
	importChuweiDetail(
		file,
		res => {
			importing.value = false;
			if (res.data !== undefined && res.data !== null) {
				ElMessage.success("导入成功");
				handleSearch();
			} else {
				ElMessage.error("导入失败：" + (res.message || "请检查文件内容格式"));
			}
		},
		() => {
			importing.value = false;
			ElMessage.error("导入失败，请稍后重试");
		},
	);
};

onMounted(() => {
	getStoreNameList(
		data => {
			storeOptions.value = data.rows || data || [];
		},
		() => {},
	);
	loadData();
});
</script>

<template>
	<section class="chuwei-page">
		<h2>储位信息</h2>
		<div class="toolbar">
			<el-select v-model="keyword.bin_store" placeholder="所属仓库" clearable filterable style="width: 160px">
				<el-option v-for="item in storeOptions" :key="item" :label="item" :value="item" />
			</el-select>
			<el-input v-model="keyword.ku_wei_bian_ma" placeholder="库位编码" clearable style="width: 170px" @keyup.enter="handleSearch" />
			<el-input v-model="keyword.ku_wei_lei_xing" placeholder="库位类型" clearable style="width: 140px" @keyup.enter="handleSearch" />
			<el-button type="primary" @click="handleSearch">查询</el-button>
			<div class="toolbar-spacer"></div>
			<el-upload
				ref="uploadRef"
				:show-file-list="false"
				:auto-upload="false"
				accept=".xlsx,.xls"
				:on-change="handleImportFile"
			>
				<el-button :loading="importing" type="success" plain>导入储位明细</el-button>
			</el-upload>
			<el-button :loading="exporting" type="warning" plain @click="handleExport">导出储位明细</el-button>
		</div>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%">
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="bin_store" label="所属仓库" min-width="110" show-overflow-tooltip />
			<el-table-column prop="ku_wei_bian_ma" label="库位编码" min-width="130" show-overflow-tooltip />
			<el-table-column prop="ku_wei_tiao_ma" label="库位条码" min-width="130" show-overflow-tooltip />
			<el-table-column prop="ku_wei_lei_xing" label="库位类型" min-width="100" />
			<el-table-column prop="ku_wei_shu_xing" label="库位属性" min-width="100" />
			<el-table-column prop="shang_jia_ci_xu" label="上架次序" width="90" />
			<el-table-column prop="qu_huo_ci_xu" label="取货次序" width="90" />
			<el-table-column prop="suo_shu_ke_hu" label="所属客户" min-width="110" show-overflow-tooltip />
			<el-table-column prop="zui_da_ti_ji" label="最大体积" width="90" />
			<el-table-column prop="zui_da_zhong_liang" label="最大重量" width="90" />
			<el-table-column prop="zui_da_tuo_pan" label="最大托盘" width="90" />
			<el-table-column prop="ting_yong" label="是否停用" width="90">
				<template #default="{ row }">{{ detailText(row.ting_yong) }}</template>
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
	</section>
</template>

<style lang="scss" scoped>
.chuwei-page {
	width: 100%;
	.toolbar {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 8px;
		margin: 12px 0;
		.toolbar-spacer {
			flex: 1;
		}
	}
	.pagination-bar {
		display: flex;
		justify-content: flex-end;
		margin-top: 12px;
	}
}
</style>
