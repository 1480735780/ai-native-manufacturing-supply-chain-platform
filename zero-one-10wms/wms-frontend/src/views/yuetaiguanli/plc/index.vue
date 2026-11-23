<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import {
	listPlc,
	getPlcDetail,
	addPlc,
	updatePlc,
	deletePlc,
	batchDeletePlc,
	exportPlc,
	importPlc,
	executePlc,
} from "@/apis/yuetaiguanli/index";

definePage({
	meta: {
		menuType: "page",
		text: "PLC指令",
		icon: "IconSetting",
	},
});

interface PlcRow {
	id: string;
	plc_ip: string;
	plc_port: string;
	plc_type: string;
	com_remark?: string;
	com_no?: string;
	remark1?: string;
	com_time?: string;
	com_seq?: string;
	com_cons?: string;
	query01?: string;
	query02?: string;
	setp_time?: string;
	setp_num?: string;
}

const loading = ref(false);
const rows = ref<PlcRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const selectedRows = ref<PlcRow[]>([]);
const tableRef = ref();

const query = ref({
	plc_type1: "",
	plc_type2: "",
	com_remark1: "",
	com_remark2: "",
	com_no: "",
});

const dialogVisible = ref(false);
const isEdit = ref(false);
const form = ref({
	id: "",
	plc_ip: "",
	plc_port: "",
	plc_type: "",
	com_remark: "",
	com_time: "",
	com_seq: "",
	com_cons: "",
	com_no: "",
	query01: "",
	query02: "",
	setp_time: "",
	setp_num: "",
});

const detailVisible = ref(false);
const detail = ref<PlcRow | null>(null);

const importInputRef = ref<HTMLInputElement>();

function loadData() {
	loading.value = true;
	listPlc(
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
			ElMessage.error("PLC指令列表加载失败");
		},
	);
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	query.value = { plc_type1: "", plc_type2: "", com_remark1: "", com_remark2: "", com_no: "" };
	pageIndex.value = 1;
	loadData();
}

function handleSelectionChange(selection: PlcRow[]) {
	selectedRows.value = selection;
}

function openAdd() {
	isEdit.value = false;
	form.value = {
		id: "",
		plc_ip: "",
		plc_port: "",
		plc_type: "",
		com_remark: "",
		com_time: "",
		com_seq: "",
		com_cons: "",
		com_no: "",
		query01: "",
		query02: "",
		setp_time: "",
		setp_num: "",
	};
	dialogVisible.value = true;
}

function openEdit(row: PlcRow) {
	// 打开详情补全字段后再编辑
	loading.value = true;
	getPlcDetail(
		row.id,
		(data: any) => {
			loading.value = false;
			isEdit.value = true;
			const d = data ?? {};
			form.value = {
				id: d.id ?? row.id,
				plc_ip: d.plc_ip ?? "",
				plc_port: d.plc_port ?? "",
				plc_type: d.plc_type ?? "",
				com_remark: d.com_remark ?? "",
				com_time: d.com_time ?? "",
				com_seq: d.com_seq ?? "",
				com_cons: d.com_cons ?? "",
				com_no: d.com_no ?? "",
				query01: d.query01 ?? "",
				query02: d.query02 ?? "",
				setp_time: d.setp_time ?? "",
				setp_num: d.setp_num ?? "",
			};
			dialogVisible.value = true;
		},
		() => {
			loading.value = false;
			ElMessage.error("获取指令详情失败");
		},
	);
}

function handleSave() {
	if (!form.value.plc_ip.trim() || !form.value.plc_port.trim() || !form.value.plc_type.trim()) {
		ElMessage.warning("PLC IP、端口、型号不能为空");
		return;
	}
	loading.value = true;
	const done = (ok: boolean) => {
		loading.value = false;
		if (ok) {
			ElMessage.success(isEdit.value ? "修改成功" : "录入成功");
			dialogVisible.value = false;
			loadData();
		} else {
			ElMessage.error(isEdit.value ? "修改失败" : "录入失败");
		}
	};
	if (isEdit.value) {
		updatePlc(
			{ ...form.value },
			() => done(true),
			() => done(false),
		);
	} else {
		addPlc(
			{ ...form.value },
			() => done(true),
			() => done(false),
		);
	}
}

function handleDelete(row: PlcRow) {
	loading.value = true;
	deletePlc(
		row.id,
		() => {
			loading.value = false;
			ElMessage.success("删除成功");
			loadData();
		},
		() => {
			loading.value = false;
			ElMessage.error("删除失败");
		},
	);
}

function handleBatchDelete() {
	if (selectedRows.value.length === 0) {
		ElMessage.warning("请先勾选要删除的指令");
		return;
	}
	const ids = selectedRows.value.map((r) => r.id);
	loading.value = true;
	batchDeletePlc(
		ids,
		() => {
			loading.value = false;
			ElMessage.success("批量删除成功");
			tableRef.value?.clearSelection();
			loadData();
		},
		() => {
			loading.value = false;
			ElMessage.error("批量删除失败");
		},
	);
}

function handleExecute() {
	if (selectedRows.value.length === 0) {
		ElMessage.warning("请先勾选要执行的指令");
		return;
	}
	const ids = selectedRows.value.map((r) => r.id);
	loading.value = true;
	executePlc(
		ids,
		(data: any) => {
			loading.value = false;
			ElMessage.success(`执行完成：成功 ${data ?? 0} 条 / 共 ${ids.length} 条`);
			tableRef.value?.clearSelection();
			loadData();
		},
		() => {
			loading.value = false;
			ElMessage.error("执行指令失败");
		},
	);
}

function handleExport() {
	loading.value = true;
	exportPlc(
		{ ...query.value },
		(data: any) => {
			loading.value = false;
			if (typeof data === "string" && data) {
				window.open(data, "_blank");
				ElMessage.success("导出成功，已打开下载地址");
			} else {
				ElMessage.warning("导出结果为空");
			}
		},
		() => {
			loading.value = false;
			ElMessage.error("导出失败");
		},
	);
}

function triggerImport() {
	importInputRef.value?.click();
}

function handleImportFile(event: Event) {
	const target = event.target as HTMLInputElement;
	const file = target.files?.[0];
	if (!file) return;
	loading.value = true;
	importPlc(
		file,
		() => {
			loading.value = false;
			ElMessage.success("导入成功");
			loadData();
		},
		() => {
			loading.value = false;
			ElMessage.error("导入失败，请检查文件格式（xlsx，13列指令数据）");
		},
	);
	target.value = "";
}

function openDetail(row: PlcRow) {
	loading.value = true;
	getPlcDetail(
		row.id,
		(data: any) => {
			loading.value = false;
			detail.value = data ?? null;
			detailVisible.value = true;
		},
		() => {
			loading.value = false;
			ElMessage.error("获取指令详情失败");
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
	<section>
		<el-card shadow="never">
			<el-form :model="query" inline>
				<el-form-item label="PLC型号">
					<el-input v-model="query.plc_type1" clearable placeholder="起始型号" style="width: 110px" />
					<span style="margin: 0 4px">至</span>
					<el-input v-model="query.plc_type2" clearable placeholder="结束型号" style="width: 110px" />
				</el-form-item>
				<el-form-item label="指令备注">
					<el-input v-model="query.com_remark1" clearable placeholder="起始备注" style="width: 110px" />
					<span style="margin: 0 4px">至</span>
					<el-input v-model="query.com_remark2" clearable placeholder="结束备注" style="width: 110px" />
				</el-form-item>
				<el-form-item label="指令编号">
					<el-input v-model="query.com_no" clearable placeholder="指令编号" style="width: 130px" />
				</el-form-item>
				<el-form-item>
					<el-button type="primary" @click="handleSearch">查询</el-button>
					<el-button @click="handleReset">重置</el-button>
				</el-form-item>
			</el-form>
		</el-card>

		<el-card shadow="never" style="margin-top: 12px">
			<div style="margin-bottom: 12px; display: flex; gap: 8px">
				<el-button type="primary" @click="openAdd">录入指令</el-button>
				<el-button type="success" :disabled="selectedRows.length === 0" @click="handleExecute">
					执行指令（{{ selectedRows.length }}）
				</el-button>
				<el-button type="danger" :disabled="selectedRows.length === 0" @click="handleBatchDelete">
					批量删除（{{ selectedRows.length }}）
				</el-button>
				<el-button @click="handleExport">导出</el-button>
				<el-button @click="triggerImport">导入</el-button>
				<input ref="importInputRef" type="file" accept=".xlsx" style="display: none" @change="handleImportFile" />
			</div>

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
				<el-table-column prop="plc_ip" label="PLC IP" width="130" />
				<el-table-column prop="plc_port" label="端口" width="80" />
				<el-table-column prop="plc_type" label="型号" width="110" />
				<el-table-column prop="remark1" label="备注1" min-width="110" show-overflow-tooltip />
				<el-table-column prop="com_no" label="指令编号" width="120" />
				<el-table-column label="操作" width="200" fixed="right">
					<template #default="{ row }">
						<el-button link type="primary" @click="openDetail(row)">详情</el-button>
						<el-button link type="primary" @click="openEdit(row)">修改</el-button>
						<el-button link type="danger" @click="handleDelete(row)">删除</el-button>
					</template>
				</el-table-column>
			</el-table>

			<el-pagination
				style="margin-top: 16px; justify-content: flex-end"
				v-model:current-page="pageIndex"
				v-model:page-size="pageSize"
				:total="total"
				:page-sizes="[10, 20, 50]"
				layout="total, sizes, prev, pager, next, jumper"
				@current-change="handlePageChange"
				@size-change="handleSizeChange"
			/>
		</el-card>

		<el-dialog v-model="dialogVisible" :title="isEdit ? '修改PLC指令' : '录入PLC指令'" width="640px">
			<el-form :model="form" label-width="100px">
				<el-row :gutter="12">
					<el-col :span="12">
						<el-form-item label="PLC IP" required>
							<el-input v-model="form.plc_ip" placeholder="如 192.168.1.10" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="PLC端口" required>
							<el-input v-model="form.plc_port" placeholder="如 502" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="PLC型号" required>
							<el-input v-model="form.plc_type" placeholder="如 S7-1200" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="指令编号">
							<el-input v-model="form.com_no" placeholder="指令编号" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="执行顺序">
							<el-input v-model="form.com_seq" placeholder="执行顺序" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="执行时间">
							<el-input v-model="form.com_time" placeholder="执行时间" :disabled="isEdit" />
						</el-form-item>
					</el-col>
					<el-col :span="24">
						<el-form-item label="指令集">
							<el-input v-model="form.com_cons" type="textarea" :rows="3" placeholder="指令集内容" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="单步参数1">
							<el-input v-model="form.query01" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="单步参数2">
							<el-input v-model="form.query02" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="单步时间">
							<el-input v-model="form.setp_time" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="步数">
							<el-input v-model="form.setp_num" />
						</el-form-item>
					</el-col>
					<el-col :span="24">
						<el-form-item label="指令备注">
							<el-input v-model="form.com_remark" type="textarea" :rows="2" />
						</el-form-item>
					</el-col>
				</el-row>
			</el-form>
			<template #footer>
				<el-button @click="dialogVisible = false">取消</el-button>
				<el-button type="primary" :loading="loading" @click="handleSave">保存</el-button>
			</template>
		</el-dialog>

		<el-dialog v-model="detailVisible" title="PLC指令详情" width="640px">
			<el-descriptions v-if="detail" :column="2" border>
				<el-descriptions-item label="PLC IP">{{ detail.plc_ip }}</el-descriptions-item>
				<el-descriptions-item label="端口">{{ detail.plc_port }}</el-descriptions-item>
				<el-descriptions-item label="型号">{{ detail.plc_type }}</el-descriptions-item>
				<el-descriptions-item label="指令编号">{{ detail.com_no }}</el-descriptions-item>
				<el-descriptions-item label="执行顺序">{{ detail.com_seq }}</el-descriptions-item>
				<el-descriptions-item label="执行时间">{{ detail.com_time }}</el-descriptions-item>
				<el-descriptions-item label="单步参数1">{{ detail.query01 }}</el-descriptions-item>
				<el-descriptions-item label="单步参数2">{{ detail.query02 }}</el-descriptions-item>
				<el-descriptions-item label="单步时间">{{ detail.setp_time }}</el-descriptions-item>
				<el-descriptions-item label="步数">{{ detail.setp_num }}</el-descriptions-item>
				<el-descriptions-item label="指令集" :span="2">{{ detail.com_cons }}</el-descriptions-item>
				<el-descriptions-item label="备注" :span="2">{{ detail.com_remark }}</el-descriptions-item>
			</el-descriptions>
		</el-dialog>
	</section>
</template>
