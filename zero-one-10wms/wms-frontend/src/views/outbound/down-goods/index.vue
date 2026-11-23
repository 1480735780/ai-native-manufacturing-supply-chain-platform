<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
	listDownGoods,
	getDownGoods,
	modifyDownGoods,
	batchUpdateDownGoods,
	downGoods,
	deleteDownGoods,
	exportDownGoods,
	saveBlob,
} from "@/apis/outbound/index";

definePage({
	meta: {
		menuType: "page",
		text: "下架管理",
		icon: "IconSetting",
	},
});

interface DownRow {
	id?: string;
	goodsId?: string;
	goodsName?: string;
	goodsQua?: string;
	goodsQuaok?: string;
	orderId?: string;
	orderIdI?: string;
	orderType?: string;
	goodsUnit?: string;
	goodsProData?: string;
	goodsBatch?: string;
	actTypeCode?: string;
	kuWeiBianMa?: string;
	binIdTo?: string;
	binIdFrom?: string;
	cusCode?: string;
	downSta?: string;
	baseUnit?: string;
	baseGoodscount?: string;
	imCusCode?: string;
	omBeiZhu?: string;
}

const loading = ref(false);
const rows = ref<DownRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const selected = ref<DownRow[]>([]);
const query = ref({
	goodsId: "",
	goodsName: "",
	orderId: "",
	goodsBatch: "",
	kuWeiBianMa: "",
	cusCode: "",
	downSta: "",
});
const editVisible = ref(false);
const editForm = ref<any>({});
const batchVisible = ref(false);
const batchForm = ref({ goodsQua: "", baseGoodscount: "" });

function loadData() {
	loading.value = true;
	listDownGoods(
		{ pageIndex: pageIndex.value, pageSize: pageSize.value, ...query.value },
		(data: any) => {
			rows.value = data.rows ?? [];
			total.value = data.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("下架列表加载失败");
		},
	);
}

function resetQuery() {
	query.value = {
		goodsId: "",
		goodsName: "",
		orderId: "",
		goodsBatch: "",
		kuWeiBianMa: "",
		cusCode: "",
		downSta: "",
	};
	pageIndex.value = 1;
	loadData();
}

function openEdit(row: DownRow) {
	getDownGoods(
		row.id as string,
		(data: any) => {
			editForm.value = { ...data };
			editVisible.value = true;
		},
		() => ElMessage.error("下架详情加载失败"),
	);
}

async function submitEdit() {
	if (!editForm.value.orderId || !editForm.value.goodsId) {
		ElMessage.warning("原始单据和商品编码不能为空");
		return;
	}
	const res = await modifyDownGoods(editForm.value);
	if (res.data?.code === 10000) {
		ElMessage.success("修改成功");
		editVisible.value = false;
		loadData();
	} else {
		ElMessage.error(res.data?.message || "修改失败");
	}
}

function openBatch() {
	if (!selected.value.length) {
		ElMessage.warning("请先勾选下架行");
		return;
	}
	batchForm.value = { goodsQua: "", baseGoodscount: "" };
	batchVisible.value = true;
}

async function submitBatch() {
	if (!batchForm.value.goodsQua || !batchForm.value.baseGoodscount) {
		ElMessage.warning("请填写数量和基本单位数量");
		return;
	}
	const list = selected.value.map(row => ({
		id: row.id,
		goodsQua: batchForm.value.goodsQua,
		baseGoodscount: batchForm.value.baseGoodscount,
	}));
	const res = await batchUpdateDownGoods(list);
	if (res.data?.code === 10000) {
		ElMessage.success("批量修改成功");
		batchVisible.value = false;
		loadData();
	} else {
		ElMessage.error(res.data?.message || "批量修改失败");
	}
}

async function handleDown() {
	if (!selected.value.length) {
		ElMessage.warning("请先勾选下架行");
		return;
	}
	await ElMessageBox.confirm(`确定下架选中的 ${selected.value.length} 条货物？`, "提示", { type: "warning" });
	const res = await downGoods(selected.value.map(r => r.id));
	if (res.data?.code === 10000) {
		ElMessage.success("下架成功");
		loadData();
	} else {
		ElMessage.error(res.data?.message || "下架失败");
	}
}

async function handleDelete(row: DownRow) {
	await ElMessageBox.confirm("确定删除该下架任务？", "提示", { type: "warning" });
	const res = await deleteDownGoods(row.id as string);
	if (res.data?.code === 10000) {
		ElMessage.success("删除成功");
		loadData();
	} else {
		ElMessage.error(res.data?.message || "删除失败");
	}
}

async function handleExport() {
	const source = selected.value.length ? selected.value : rows.value;
	const ids = source.map(r => r.id).filter(Boolean) as string[];
	if (!ids.length) {
		ElMessage.warning("没有可导出的数据");
		return;
	}
	try {
		const blob = await exportDownGoods(ids);
		saveBlob(blob, "下架数据.xlsx");
		ElMessage.success("导出成功");
	} catch (e) {
		ElMessage.error("导出失败");
	}
}

function handleSelectionChange(val: DownRow[]) {
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
	<section class="down-root">
		<el-form :model="query" inline class="query-bar">
			<el-form-item label="商品编码">
				<el-input v-model="query.goodsId" clearable style="width: 140px" />
			</el-form-item>
			<el-form-item label="商品名称">
				<el-input v-model="query.goodsName" clearable style="width: 160px" />
			</el-form-item>
			<el-form-item label="原始单据">
				<el-input v-model="query.orderId" clearable style="width: 170px" />
			</el-form-item>
			<el-form-item label="批次">
				<el-input v-model="query.goodsBatch" clearable style="width: 130px" />
			</el-form-item>
			<el-form-item label="库位">
				<el-input v-model="query.kuWeiBianMa" clearable style="width: 130px" />
			</el-form-item>
			<el-form-item label="状态">
				<el-input v-model="query.downSta" clearable style="width: 110px" />
			</el-form-item>
			<el-form-item>
				<el-button type="primary" @click="loadData">查询</el-button>
				<el-button @click="resetQuery">重置</el-button>
			</el-form-item>
		</el-form>

		<div class="tool-bar">
			<el-button type="primary" @click="openBatch">批量修改数量</el-button>
			<el-button type="success" @click="handleDown">下架</el-button>
			<el-button @click="handleExport">导出</el-button>
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
			<el-table-column prop="orderId" label="原始单据" width="170" show-overflow-tooltip />
			<el-table-column prop="goodsId" label="商品编码" width="130" show-overflow-tooltip />
			<el-table-column prop="goodsName" label="商品名称" min-width="160" show-overflow-tooltip />
			<el-table-column prop="goodsQua" label="数量" width="90" align="right" />
			<el-table-column prop="goodsQuaok" label="完成数量" width="100" align="right" />
			<el-table-column prop="goodsUnit" label="单位" width="70" />
			<el-table-column prop="goodsBatch" label="批次" width="110" />
			<el-table-column prop="goodsProData" label="生产日期" width="120" />
			<el-table-column prop="kuWeiBianMa" label="库位" width="120" />
			<el-table-column prop="binIdFrom" label="源托盘" width="110" />
			<el-table-column prop="binIdTo" label="目标托盘" width="110" />
			<el-table-column prop="cusCode" label="货主" width="100" />
			<el-table-column prop="downSta" label="状态" width="90" />
			<el-table-column prop="omBeiZhu" label="备注" min-width="140" show-overflow-tooltip />
			<el-table-column label="操作" width="130" fixed="right">
				<template #default="{ row }">
					<el-button link type="primary" @click="openEdit(row)">修改</el-button>
					<el-button link type="danger" @click="handleDelete(row)">删除</el-button>
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

		<el-dialog v-model="editVisible" title="修改下架信息" width="620px">
			<el-form :model="editForm" label-width="110px">
				<el-row :gutter="12">
					<el-col :span="12">
						<el-form-item label="原始单据">
							<el-input v-model="editForm.orderId" disabled />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="商品编码">
							<el-input v-model="editForm.goodsId" disabled />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="数量">
							<el-input v-model="editForm.goodsQua" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="完成数量">
							<el-input v-model="editForm.goodsQuaok" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="库位">
							<el-input v-model="editForm.kuWeiBianMa" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="源托盘">
							<el-input v-model="editForm.binIdFrom" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="目标托盘">
							<el-input v-model="editForm.binIdTo" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="批次">
							<el-input v-model="editForm.goodsBatch" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="生产日期">
							<el-input v-model="editForm.goodsProData" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="状态">
							<el-input v-model="editForm.downSta" />
						</el-form-item>
					</el-col>
					<el-col :span="24">
						<el-form-item label="备注">
							<el-input v-model="editForm.omBeiZhu" type="textarea" :rows="2" />
						</el-form-item>
					</el-col>
				</el-row>
			</el-form>
			<template #footer>
				<el-button @click="editVisible = false">取消</el-button>
				<el-button type="primary" @click="submitEdit">保存</el-button>
			</template>
		</el-dialog>

		<el-dialog v-model="batchVisible" title="批量修改数量" width="420px">
			<el-form :model="batchForm" label-width="110px">
				<el-form-item label="数量" required>
					<el-input v-model="batchForm.goodsQua" />
				</el-form-item>
				<el-form-item label="基本单位数量" required>
					<el-input v-model="batchForm.baseGoodscount" />
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="batchVisible = false">取消</el-button>
				<el-button type="primary" @click="submitBatch">保存</el-button>
			</template>
		</el-dialog>
	</section>
</template>

<style lang="scss" scoped>
.down-root {
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
