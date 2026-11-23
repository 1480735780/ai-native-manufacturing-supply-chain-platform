<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
	listMoveGoods,
	modifyMoveGoods,
	batchMoveGoods,
	removeMoveGoods,
	downloadMoveGoods,
} from "@/apis/kuneiguanli/index";

definePage({
	meta: {
		menuType: "page",
		text: "库内转移",
		icon: "IconSetting",
	},
});

interface TaskRow {
	id?: string;
	createBy?: string;
	createDate?: string;
	goodsID?: string;
	goodsName?: string;
	goodsQua?: string;
	goodsUnit?: string;
	goodsProData?: string;
	cusCode?: string;
	cusName?: string;
	tinFrom?: string;
	tinId?: string;
	binFrom?: string;
	binTo?: string;
	toCusCode?: string;
	toCusName?: string;
	moveNum?: string;
	produceDate?: string;
	toProduceDate?: string;
	moveStatus?: string;
	runSta?: string;
}

const loading = ref(false);
const rows = ref<TaskRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const selectedRows = ref<TaskRow[]>([]);
const tableRef = ref();

const query = ref({
	id: "",
	goodsID: "",
	goodsName: "",
	cusCode: "",
	tinFrom: "",
	binFrom: "",
	moveSta: "",
	runSta: "",
});

const dialogVisible = ref(false);
const saving = ref(false);
const editForm = ref({
	id: "",
	tinId: "",
	binTo: "",
	moveNum: "",
	produceDate: "",
	toProduceDate: "",
	moveStatus: "",
});

function loadData() {
	loading.value = true;
	listMoveGoods(
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
			ElMessage.error("转移任务列表加载失败");
		},
	);
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	query.value = {
		id: "",
		goodsID: "",
		goodsName: "",
		cusCode: "",
		tinFrom: "",
		binFrom: "",
		moveSta: "",
		runSta: "",
	};
	pageIndex.value = 1;
	loadData();
}

function handleSelectionChange(selection: TaskRow[]) {
	selectedRows.value = selection;
}

function openEdit(row: TaskRow) {
	editForm.value = {
		id: row.id ?? "",
		tinId: row.tinId ?? "",
		binTo: row.binTo ?? "",
		moveNum: row.moveNum ?? row.goodsQua ?? "",
		produceDate: row.produceDate ?? row.goodsProData ?? "",
		toProduceDate: row.toProduceDate ?? "",
		moveStatus: row.moveStatus ?? "",
	};
	dialogVisible.value = true;
}

function saveEdit() {
	if (!editForm.value.id) return;
	saving.value = true;
	modifyMoveGoods(
		{ ...editForm.value },
		() => {
			saving.value = false;
			dialogVisible.value = false;
			ElMessage.success("修改成功");
			loadData();
		},
		() => {
			saving.value = false;
			ElMessage.error("修改失败，已执行或已删除的任务不可修改");
		},
	);
}

function handleBatchMove() {
	if (selectedRows.value.length === 0) {
		ElMessage.warning("请先勾选需要转移的任务");
		return;
	}
	ElMessageBox.confirm(
		`确认将选中的 ${selectedRows.value.length} 条任务标记为已转移？`,
		"批量转移",
		{ type: "warning" },
	)
		.then(() => {
			loading.value = true;
			batchMoveGoods(
				{ items: selectedRows.value.map((row) => ({ id: row.id })) },
				(data: any) => {
					loading.value = false;
					ElMessage.success(`已转移 ${data} 条任务`);
					tableRef.value?.clearSelection();
					selectedRows.value = [];
					loadData();
				},
				() => {
					loading.value = false;
					ElMessage.error("批量转移失败");
				},
			);
		})
		.catch(() => {});
}

function handleRemove() {
	if (selectedRows.value.length === 0) {
		ElMessage.warning("请先勾选需要删除的任务");
		return;
	}
	ElMessageBox.confirm(`确认删除选中的 ${selectedRows.value.length} 条任务？`, "批量删除", {
		type: "warning",
	})
		.then(() => {
			loading.value = true;
			removeMoveGoods(
				selectedRows.value.map((row) => row.id ?? "").filter(Boolean),
				() => {
					loading.value = false;
					ElMessage.success("删除成功");
					tableRef.value?.clearSelection();
					selectedRows.value = [];
					loadData();
				},
				() => {
					loading.value = false;
					ElMessage.error("删除失败");
				},
			);
		})
		.catch(() => {});
}

async function handleExport() {
	if (selectedRows.value.length === 0) {
		ElMessage.warning("请先勾选需要导出的任务");
		return;
	}
	try {
		loading.value = true;
		const res: any = await downloadMoveGoods(
			selectedRows.value.map((row) => row.id ?? "").filter(Boolean),
		);
		const blob = new Blob([res.data], {
			type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
		});
		const url = URL.createObjectURL(blob);
		const link = document.createElement("a");
		link.href = url;
		link.download = "move-goods.xlsx";
		link.click();
		URL.revokeObjectURL(url);
		loading.value = false;
	} catch (e) {
		loading.value = false;
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

onMounted(() => {
	loadData();
});
</script>

<template>
	<section class="move-task-root">
		<el-card shadow="never" class="query-card">
			<el-form :model="query" inline label-width="90px">
				<el-form-item label="任务ID">
					<el-input v-model="query.id" clearable placeholder="任务ID" style="width: 180px" />
				</el-form-item>
				<el-form-item label="商品编码">
					<el-input v-model="query.goodsID" clearable placeholder="商品编码" style="width: 140px" />
				</el-form-item>
				<el-form-item label="商品名称">
					<el-input v-model="query.goodsName" clearable placeholder="商品名称" style="width: 150px" />
				</el-form-item>
				<el-form-item label="货主编码">
					<el-input v-model="query.cusCode" clearable placeholder="货主编码" style="width: 130px" />
				</el-form-item>
				<el-form-item label="源托盘">
					<el-input v-model="query.tinFrom" clearable placeholder="源托盘" style="width: 130px" />
				</el-form-item>
				<el-form-item label="源储位">
					<el-input v-model="query.binFrom" clearable placeholder="源储位" style="width: 130px" />
				</el-form-item>
				<el-form-item label="状态">
					<el-select v-model="query.moveSta" clearable placeholder="全部" style="width: 120px">
						<el-option label="待转移" value="待转移" />
						<el-option label="已转移" value="已转移" />
					</el-select>
				</el-form-item>
				<el-form-item label="执行状态">
					<el-select v-model="query.runSta" clearable placeholder="全部" style="width: 120px">
						<el-option label="未执行" value="未执行" />
						<el-option label="已执行" value="已执行" />
					</el-select>
				</el-form-item>
				<el-form-item>
					<el-button type="primary" @click="handleSearch">查询</el-button>
					<el-button @click="handleReset">重置</el-button>
				</el-form-item>
			</el-form>
		</el-card>

		<el-card shadow="never" class="tool-card">
			<div class="tool-bar">
				<el-button
					type="primary"
					:disabled="selectedRows.length === 0"
					@click="handleBatchMove"
				>
					批量转移（{{ selectedRows.length }}）
				</el-button>
				<el-button :disabled="selectedRows.length === 0" @click="handleExport">导出数据</el-button>
				<el-button type="danger" :disabled="selectedRows.length === 0" @click="handleRemove">
					批量删除
				</el-button>
				<el-button @click="loadData">刷新</el-button>
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
			<el-table-column prop="createDate" label="创建日期" width="170" />
			<el-table-column prop="goodsID" label="商品编码" width="120" show-overflow-tooltip />
			<el-table-column prop="goodsName" label="商品名称" min-width="150" show-overflow-tooltip />
			<el-table-column prop="goodsQua" label="数量" width="90" align="right" />
			<el-table-column prop="goodsUnit" label="单位" width="80" />
			<el-table-column prop="goodsProData" label="生产日期" width="120" />
			<el-table-column prop="cusCode" label="货主编码" width="110" />
			<el-table-column prop="cusName" label="货主名称" min-width="150" show-overflow-tooltip />
			<el-table-column prop="binFrom" label="源储位" width="110" show-overflow-tooltip />
			<el-table-column prop="tinFrom" label="源托盘" width="110" show-overflow-tooltip />
			<el-table-column prop="binTo" label="到储位" width="110" show-overflow-tooltip />
			<el-table-column prop="tinId" label="到托盘" width="110" show-overflow-tooltip />
			<el-table-column prop="moveStatus" label="状态" width="100" />
			<el-table-column prop="runSta" label="执行状态" width="100" />
			<el-table-column label="操作" width="90" fixed="right">
				<template #default="{ row }">
					<el-button link type="primary" @click="openEdit(row)">修改</el-button>
				</template>
			</el-table-column>
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

		<el-dialog v-model="dialogVisible" title="修改转移任务" width="520px">
			<el-form :model="editForm" label-width="100px">
				<el-form-item label="到储位">
					<el-input v-model="editForm.binTo" clearable placeholder="目标储位" />
				</el-form-item>
				<el-form-item label="到托盘">
					<el-input v-model="editForm.tinId" clearable placeholder="目标托盘" />
				</el-form-item>
				<el-form-item label="移动数量">
					<el-input v-model="editForm.moveNum" clearable placeholder="移动数量" />
				</el-form-item>
				<el-form-item label="生产日期">
					<el-date-picker
						v-model="editForm.produceDate"
						type="date"
						value-format="YYYY-MM-DD"
						placeholder="生产日期"
						style="width: 100%"
					/>
				</el-form-item>
				<el-form-item label="到生产日期">
					<el-date-picker
						v-model="editForm.toProduceDate"
						type="date"
						value-format="YYYY-MM-DD"
						placeholder="到生产日期"
						style="width: 100%"
					/>
				</el-form-item>
				<el-form-item label="状态">
					<el-select v-model="editForm.moveStatus" placeholder="状态" style="width: 100%">
						<el-option label="待转移" value="待转移" />
						<el-option label="已转移" value="已转移" />
					</el-select>
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="dialogVisible = false">取消</el-button>
				<el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button>
			</template>
		</el-dialog>
	</section>
</template>

<style lang="scss" scoped>
.move-task-root {
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
	gap: 8px;
}
</style>
