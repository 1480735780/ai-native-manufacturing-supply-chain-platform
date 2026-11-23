<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { listOverallInventory, createOverallTasks } from "@/apis/inventory/index";

definePage({
	meta: {
		menuType: "page",
		text: "综合盘点",
		icon: "IconSetting",
	},
});

interface OverallRow {
	id?: string;
	yidongriqi?: string;
	cktype?: string;
	chuwei?: string;
	tuopan?: string;
	huozhu?: string;
	huozhumingcheng?: string;
	shangpinbianma?: string;
	shangpinshuliang?: string;
	shangpinmincheng?: string;
	shengchanriqi?: string;
}

const loading = ref(false);
const rows = ref<OverallRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const selectedRows = ref<OverallRow[]>([]);
const creating = ref(false);

const query = ref({
	chuwei: "",
	tuopan: "",
	huozhu: "",
	shangpinbianma: "",
	shangpinmincheng: "",
});

function loadData() {
	loading.value = true;
	listOverallInventory(
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
			ElMessage.error("综合盘点数据加载失败");
		},
	);
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	query.value = { chuwei: "", tuopan: "", huozhu: "", shangpinbianma: "", shangpinmincheng: "" };
	pageIndex.value = 1;
	loadData();
}

function handleSelectionChange(selection: OverallRow[]) {
	selectedRows.value = selection;
}

async function handleCreateTasks() {
	if (selectedRows.value.length === 0) {
		ElMessage.warning("请先勾选要生成盘点任务的库存记录");
		return;
	}
	const ids = selectedRows.value.map((r) => r.id).filter(Boolean) as string[];
	if (ids.length === 0) {
		ElMessage.warning("所选记录缺少唯一标识，无法生成任务");
		return;
	}
	try {
		await ElMessageBox.confirm(`确定为选中的 ${ids.length} 条记录生成盘点任务吗？`, "批量生成盘点任务", {
			confirmButtonText: "确定",
			cancelButtonText: "取消",
			type: "info",
		});
	} catch {
		return;
	}
	creating.value = true;
	try {
		const result = await createOverallTasks(ids);
		const count = result?.ids?.length ?? ids.length;
		ElMessage.success(`成功生成 ${count} 条盘点任务`);
		loadData();
	} catch {
		ElMessage.error("生成盘点任务失败");
	} finally {
		creating.value = false;
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
	<section class="comprehensive-inventory-root">
		<el-card shadow="never" class="query-card">
			<el-form :model="query" inline label-width="80px">
				<el-form-item label="储位">
					<el-input v-model="query.chuwei" clearable placeholder="请输入储位" style="width: 140px" />
				</el-form-item>
				<el-form-item label="托盘">
					<el-input v-model="query.tuopan" clearable placeholder="请输入托盘" style="width: 140px" />
				</el-form-item>
				<el-form-item label="货主">
					<el-input v-model="query.huozhu" clearable placeholder="请输入货主编码" style="width: 130px" />
				</el-form-item>
				<el-form-item label="商品编码">
					<el-input v-model="query.shangpinbianma" clearable placeholder="请输入商品编码" style="width: 140px" />
				</el-form-item>
				<el-form-item label="商品名称">
					<el-input v-model="query.shangpinmincheng" clearable placeholder="请输入商品名称" style="width: 140px" />
				</el-form-item>
				<el-form-item>
					<el-button type="primary" @click="handleSearch">查询</el-button>
					<el-button @click="handleReset">重置</el-button>
				</el-form-item>
			</el-form>
		</el-card>

		<div class="tool-bar">
			<el-button type="primary" :loading="creating" @click="handleCreateTasks">
				生成盘点任务{{ selectedRows.length ? `（${selectedRows.length}）` : "" }}
			</el-button>
			<el-button @click="loadData">刷新</el-button>
			<span class="tip">勾选库存记录后批量生成盘点任务（任务初始状态：计划中）</span>
		</div>

		<el-table
			v-loading="loading"
			:data="rows"
			border
			stripe
			style="width: 100%"
			@selection-change="handleSelectionChange"
		>
			<el-table-column type="selection" width="45" />
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="yidongriqi" label="移动日期" width="170" />
			<el-table-column prop="cktype" label="库存类型" width="100" />
			<el-table-column prop="chuwei" label="储位" width="120" show-overflow-tooltip />
			<el-table-column prop="tuopan" label="托盘" width="120" show-overflow-tooltip />
			<el-table-column prop="huozhu" label="货主编码" width="120" />
			<el-table-column prop="huozhumingcheng" label="货主名称" min-width="180" show-overflow-tooltip />
			<el-table-column prop="shangpinbianma" label="商品编码" width="120" show-overflow-tooltip />
			<el-table-column prop="shangpinmincheng" label="商品名称" min-width="160" show-overflow-tooltip />
			<el-table-column prop="shangpinshuliang" label="盘点数量" width="110" align="right" />
			<el-table-column prop="shengchanriqi" label="生产日期" width="120" />
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
.comprehensive-inventory-root {
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
