<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
	listOutboundTasks,
	modifyOutboundTask,
	batchSetTaskRecipients,
	confirmOutboundTasks,
	generateOutboundWave,
	deleteOutboundTasks,
	requestTaskExport,
} from "@/apis/outbound/index";

definePage({
	meta: {
		menuType: "page",
		text: "任务确认",
		icon: "IconSetting",
	},
});

interface TaskRow {
	id?: string;
	omNoticeId?: string;
	goodsId?: string;
	goodsName?: string;
	imCusCode?: string;
	omBeiZhu?: string;
	qmOkQuat?: string;
	goodsUnit?: string;
	baseGoodscount?: string;
	baseUnit?: string;
	itemText?: string;
	proData?: string;
	tinId?: string;
	binId?: string;
	binSta?: string;
	cusCode?: string;
	assignTo?: string;
	waveId?: string;
	createDate?: string;
}

const loading = ref(false);
const rows = ref<TaskRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const selected = ref<TaskRow[]>([]);
const query = ref({
	omNoticeId: "",
	goodsId: "",
	goodsName: "",
	assignTo: "",
	waveId: "",
	cusCode: "",
});

const dialogVisible = ref(false);
const form = ref<any>({});

function loadData() {
	loading.value = true;
	listOutboundTasks(
		{ pageIndex: pageIndex.value, pageSize: pageSize.value, ...query.value },
		(data: any) => {
			rows.value = data.rows ?? [];
			total.value = data.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("任务列表加载失败");
		},
	);
}

function resetQuery() {
	query.value = { omNoticeId: "", goodsId: "", goodsName: "", assignTo: "", waveId: "", cusCode: "" };
	pageIndex.value = 1;
	loadData();
}

function selectedIds() {
	const ids = selected.value.map(r => r.id).filter(Boolean) as string[];
	if (!ids.length) {
		ElMessage.warning("请先勾选任务");
	}
	return ids;
}

function openEdit(row: TaskRow) {
	form.value = {
		id: row.id,
		assignTo: row.assignTo ?? "",
		proData: row.proData ?? "",
		tinId: row.tinId ?? "",
		binId: row.binId ?? "",
		baseGoodsCount: row.baseGoodscount ?? "",
		qmOkQuat: row.qmOkQuat ?? "",
		itemText: row.itemText ?? "",
	};
	dialogVisible.value = true;
}

async function submitEdit() {
	const res = await modifyOutboundTask(form.value);
	if (res.data?.code === 10000) {
		ElMessage.success("修改成功");
		dialogVisible.value = false;
		loadData();
	} else {
		ElMessage.error(res.data?.message || "修改失败");
	}
}

async function handleSetReceiver() {
	const ids = selectedIds();
	if (!ids.length) return;
	const { value } = await ElMessageBox.prompt("请输入任务接收人", "批量设置接收人", {
		inputPattern: /\S+/,
		inputErrorMessage: "接收人不能为空",
	});
	const res = await batchSetTaskRecipients(ids, value);
	if (res.data?.code === 10000) {
		ElMessage.success("设置成功");
		loadData();
	} else {
		ElMessage.error(res.data?.message || "设置失败");
	}
}

async function handleConfirm() {
	const ids = selectedIds();
	if (!ids.length) return;
	await ElMessageBox.confirm(`确认选中的 ${ids.length} 条任务？`, "提示", { type: "warning" });
	const res = await confirmOutboundTasks(ids);
	if (res.data?.code === 10000) {
		ElMessage.success("确认成功");
		loadData();
	} else {
		ElMessage.error(res.data?.message || "确认失败");
	}
}

async function handleWave() {
	const ids = selectedIds();
	if (!ids.length) return;
	const res = await generateOutboundWave(ids);
	if (res.data?.code === 10000) {
		ElMessage.success("波次生成成功");
		loadData();
	} else {
		ElMessage.error(res.data?.message || "波次生成失败");
	}
}

async function handleDelete() {
	const ids = selectedIds();
	if (!ids.length) return;
	await ElMessageBox.confirm(`确定删除选中的 ${ids.length} 条任务？`, "提示", { type: "warning" });
	const res = await deleteOutboundTasks(ids);
	if (res.data?.code === 10000) {
		ElMessage.success("删除成功");
		loadData();
	} else {
		ElMessage.error(res.data?.message || "删除失败");
	}
}

async function handleExport() {
	try {
		const res = await requestTaskExport();
		ElMessage.success(res.data?.data || "导出任务已提交");
	} catch (e) {
		ElMessage.error("导出请求失败");
	}
}

function handleSelectionChange(val: TaskRow[]) {
	selected.value = val;
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
	<section class="task-root">
		<el-form :model="query" inline class="query-bar">
			<el-form-item label="出库单号">
				<el-input v-model="query.omNoticeId" clearable style="width: 170px" />
			</el-form-item>
			<el-form-item label="商品编码">
				<el-input v-model="query.goodsId" clearable style="width: 140px" />
			</el-form-item>
			<el-form-item label="商品名称">
				<el-input v-model="query.goodsName" clearable style="width: 160px" />
			</el-form-item>
			<el-form-item label="接收人">
				<el-input v-model="query.assignTo" clearable style="width: 130px" />
			</el-form-item>
			<el-form-item label="波次">
				<el-input v-model="query.waveId" clearable style="width: 150px" />
			</el-form-item>
			<el-form-item>
				<el-button type="primary" @click="loadData">查询</el-button>
				<el-button @click="resetQuery">重置</el-button>
			</el-form-item>
		</el-form>

		<div class="tool-bar">
			<el-button type="primary" @click="handleSetReceiver">批量设置接收人</el-button>
			<el-button type="success" @click="handleConfirm">确认任务</el-button>
			<el-button type="warning" @click="handleWave">生成波次</el-button>
			<el-button type="danger" @click="handleDelete">删除任务</el-button>
			<el-button @click="handleExport">导出任务</el-button>
			<span class="tip">已选 {{ selected.length }} 条</span>
		</div>

		<el-table
			v-loading="loading"
			:data="rows"
			border
			stripe
			style="width: 100%"
			@selection-change="handleSelectionChange"
		>
			<el-table-column type="selection" width="50" />
			<el-table-column prop="omNoticeId" label="出库单号" width="170" show-overflow-tooltip />
			<el-table-column prop="goodsId" label="商品编码" width="130" show-overflow-tooltip />
			<el-table-column prop="goodsName" label="商品名称" min-width="160" show-overflow-tooltip />
			<el-table-column prop="qmOkQuat" label="数量" width="90" align="right" />
			<el-table-column prop="goodsUnit" label="单位" width="70" />
			<el-table-column prop="tinId" label="托盘" width="110" />
			<el-table-column prop="binId" label="仓位" width="110" />
			<el-table-column prop="assignTo" label="接收人" width="110" />
			<el-table-column prop="waveId" label="波次" width="160" show-overflow-tooltip />
			<el-table-column prop="binSta" label="状态" width="80" />
			<el-table-column prop="imCusCode" label="客户订单号" width="130" show-overflow-tooltip />
			<el-table-column prop="omBeiZhu" label="备注" min-width="140" show-overflow-tooltip />
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

		<el-dialog v-model="dialogVisible" title="修改任务" width="520px">
			<el-form :model="form" label-width="110px">
				<el-form-item label="任务接收人">
					<el-input v-model="form.assignTo" />
				</el-form-item>
				<el-form-item label="生产日期">
					<el-input v-model="form.proData" placeholder="yyyy-MM-dd" />
				</el-form-item>
				<el-form-item label="托盘">
					<el-input v-model="form.tinId" />
				</el-form-item>
				<el-form-item label="仓位">
					<el-input v-model="form.binId" />
				</el-form-item>
				<el-form-item label="数量">
					<el-input v-model="form.qmOkQuat" />
				</el-form-item>
				<el-form-item label="基本单位数量">
					<el-input v-model="form.baseGoodsCount" />
				</el-form-item>
				<el-form-item label="备注">
					<el-input v-model="form.itemText" type="textarea" :rows="2" />
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="dialogVisible = false">取消</el-button>
				<el-button type="primary" @click="submitEdit">保存</el-button>
			</template>
		</el-dialog>
	</section>
</template>

<style lang="scss" scoped>
.task-root {
	width: 100%;

	.query-bar {
		margin-top: 8px;
	}

	.tool-bar {
		display: flex;
		align-items: center;
		gap: 8px;
		margin: 4px 0 12px;
	}

	.tip {
		margin-left: 8px;
		color: #909399;
		font-size: 13px;
	}
}
</style>
