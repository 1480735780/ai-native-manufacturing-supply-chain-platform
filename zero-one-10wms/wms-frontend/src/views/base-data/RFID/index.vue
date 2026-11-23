<script lang="ts" setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import type { FormInstance } from "element-plus";
import {
	listRfids,
	getRfidDetail,
	addRfid,
	updateRfid,
	removeRfids,
	exportRfids,
	importRfids,
} from "@/apis/base-data/index.js";
import { errText, useBaseDataPage } from "../composables/use-base-data-page";
import { usePermission } from "@/composables/use-permission";

definePage({
	meta: {
		menuType: "page",
		text: "RFID",
		icon: "IconSetting",
	},
});

const keyword = reactive({ type: "", buseCode: "", buseContent: "", rfid1: "", createName: "" });

const {
	loading,
	rows,
	total,
	pageIndex,
	pageSize,
	selectedRows,
	setQueryBuilder,
	loadData,
	handleSearch,
	handlePageChange,
	handleSizeChange,
	handleSelectionChange,
	removeRow,
	removeSelected,
	exportData,
	importVisible,
	importSaving,
	importFileList,
	openImport,
	handleImportChange,
	handleImportRemove,
	submitImport,
} = useBaseDataPage({
	listApi: listRfids,
	removeApi: removeRfids,
	exportApi: exportRfids,
	importApi: importRfids,
	rowKey: (row) => row.id,
	rowLabel: (row) => row.rfidId1 || row.rfidBuseno,
	fileName: "RFID",
	loadFailText: "RFID 数据加载失败",
});

/** 只读角色（财务/客户等）只能查看详情，不显示写操作入口 */
const { canWrite } = usePermission();

setQueryBuilder(() => ({
	type: keyword.type,
	buseCode: keyword.buseCode,
	buseContent: keyword.buseContent,
	rfid1: keyword.rfid1,
	createName: keyword.createName,
}));

const emptyForm = {
	rfidType: "",
	rfidBuseno: "",
	rfidBusecont: "",
	rfidId1: "",
	rfidId2: "",
	rfidId3: "",
};
const form = reactive({ ...emptyForm });
const formRef = ref<FormInstance>();
const dialogVisible = ref(false);
const dialogMode = ref<"add" | "edit">("add");
const saving = ref(false);

const detailVisible = ref(false);
const detailLoading = ref(false);
const detail = ref<any>({});

function openAdd() {
	dialogMode.value = "add";
	Object.assign(form, emptyForm);
	dialogVisible.value = true;
}

function openEdit(row: any) {
	dialogMode.value = "edit";
	Object.assign(form, emptyForm, {
		rfidType: row.rfidType ?? "",
		rfidBuseno: row.rfidBuseno ?? "",
		rfidBusecont: row.rfidBusecont ?? "",
		rfidId1: row.rfidId1 ?? "",
		rfidId2: row.rfidId2 ?? "",
		rfidId3: row.rfidId3 ?? "",
	});
	dialogVisible.value = true;
}

function openDetail(row: any) {
	detailVisible.value = true;
	detailLoading.value = true;
	detail.value = { ...row };
	getRfidDetail(
		row.rfidBuseno,
		(data: any) => {
			detail.value = data ?? row;
			detailLoading.value = false;
		},
		() => {
			detailLoading.value = false;
		},
	);
}

async function submitForm() {
	if (!formRef.value) return;
	try {
		await formRef.value.validate();
	} catch {
		return;
	}
	saving.value = true;
	try {
		if (dialogMode.value === "add") {
			await addRfid({ ...form });
			ElMessage.success("录入成功");
		} else {
			// 后端以 rfidBuseno 作为更新定位键，业务编号不可修改
			await updateRfid({ ...form });
			ElMessage.success("修改成功");
		}
		dialogVisible.value = false;
		loadData();
	} catch (err: any) {
		ElMessage.error(errText(err, "保存失败"));
	} finally {
		saving.value = false;
	}
}

onMounted(() => {
	loadData();
});
</script>

<template>
	<section class="base-data-page">
		<h2>RFID</h2>
		<div class="toolbar">
			<el-input v-model="keyword.rfid1" placeholder="RFID1" clearable style="width: 160px" @keyup.enter="handleSearch" />
			<el-input v-model="keyword.type" placeholder="类型" clearable style="width: 140px" @keyup.enter="handleSearch" />
			<el-input v-model="keyword.buseCode" placeholder="业务编号" clearable style="width: 160px" @keyup.enter="handleSearch" />
			<el-input v-model="keyword.buseContent" placeholder="业务内容" clearable style="width: 160px" @keyup.enter="handleSearch" />
			<el-input v-model="keyword.createName" placeholder="创建人" clearable style="width: 140px" @keyup.enter="handleSearch" />
			<el-button type="primary" @click="handleSearch">查询</el-button>
			<el-button v-if="canWrite" type="success" @click="openAdd">录入</el-button>
			<el-button @click="exportData">导出</el-button>
			<el-button v-if="canWrite" @click="openImport">导入</el-button>
			<el-button v-if="canWrite" type="danger" plain :disabled="selectedRows.length === 0" @click="removeSelected">批量删除</el-button>
		</div>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%" @selection-change="handleSelectionChange">
			<el-table-column v-if="canWrite" type="selection" width="45" />
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="rfidId1" label="RFID1" min-width="160" show-overflow-tooltip />
			<el-table-column prop="rfidType" label="类型" min-width="110" show-overflow-tooltip />
			<el-table-column prop="rfidBuseno" label="业务编号" min-width="150" show-overflow-tooltip />
			<el-table-column prop="rfidBusecont" label="业务内容" min-width="180" show-overflow-tooltip />
			<el-table-column prop="createName" label="创建人" min-width="120" show-overflow-tooltip />
			<el-table-column label="操作" :width="canWrite ? 180 : 90" fixed="right">
				<template #default="{ row }">
					<el-button link type="primary" @click="openDetail(row)">查看</el-button>
					<el-button v-if="canWrite" link type="primary" @click="openEdit(row)">修改</el-button>
					<el-button v-if="canWrite" link type="danger" @click="removeRow(row)">删除</el-button>
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

		<el-dialog v-model="dialogVisible" :title="dialogMode === 'add' ? '录入 RFID' : '修改 RFID'" width="560px" :close-on-click-modal="false" destroy-on-close>
			<el-form ref="formRef" :model="form" label-width="100px">
				<el-row :gutter="12">
					<el-col :span="12">
						<el-form-item label="类型" prop="rfidType" :rules="[{ required: true, message: '请输入类型', trigger: 'blur' }]">
							<el-input v-model="form.rfidType" placeholder="如 weight" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="业务编号" prop="rfidBuseno" :rules="[{ required: true, message: '请输入业务编号', trigger: 'blur' }]">
							<el-input v-model="form.rfidBuseno" :disabled="dialogMode === 'edit'" placeholder="修改时不可变更" />
						</el-form-item>
					</el-col>
					<el-col :span="24">
						<el-form-item label="业务内容"><el-input v-model="form.rfidBusecont" /></el-form-item>
					</el-col>
					<el-col :span="24">
						<el-form-item label="RFID1" prop="rfidId1" :rules="[{ required: true, message: '请输入 RFID1', trigger: 'blur' }]">
							<el-input v-model="form.rfidId1" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="RFID2"><el-input v-model="form.rfidId2" /></el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="RFID3"><el-input v-model="form.rfidId3" /></el-form-item>
					</el-col>
				</el-row>
			</el-form>
			<template #footer>
				<el-button @click="dialogVisible = false">取消</el-button>
				<el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
			</template>
		</el-dialog>

		<el-drawer v-model="detailVisible" title="RFID 详情" size="480px">
			<div v-loading="detailLoading" class="detail-list">
				<p><span>RFID1</span>{{ detail.rfidId1 || "-" }}</p>
				<p><span>RFID2</span>{{ detail.rfidId2 || "-" }}</p>
				<p><span>RFID3</span>{{ detail.rfidId3 || "-" }}</p>
				<p><span>类型</span>{{ detail.rfidType || "-" }}</p>
				<p><span>业务编号</span>{{ detail.rfidBuseno || "-" }}</p>
				<p><span>业务内容</span>{{ detail.rfidBusecont || "-" }}</p>
				<p><span>创建人</span>{{ detail.createName || "-" }}</p>
			</div>
		</el-drawer>

		<el-dialog v-model="importVisible" title="导入 RFID" width="460px" :close-on-click-modal="false">
			<el-upload
				v-model:file-list="importFileList"
				:auto-upload="false"
				:limit="1"
				accept=".xlsx,.xls"
				:on-change="handleImportChange"
				:on-remove="handleImportRemove"
			>
				<el-button type="primary">选择文件</el-button>
				<template #tip><div class="el-upload__tip">请使用导出的 RFID 文件作为导入模板</div></template>
			</el-upload>
			<template #footer>
				<el-button @click="importVisible = false">取消</el-button>
				<el-button type="primary" :loading="importSaving" @click="submitImport">开始导入</el-button>
			</template>
		</el-dialog>
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
	.detail-list p {
		display: flex;
		gap: 12px;
		margin: 0;
		padding: 10px 0;
		border-bottom: 1px solid var(--el-border-color-lighter);
		span:first-child {
			width: 90px;
			color: var(--el-text-color-secondary);
			flex-shrink: 0;
		}
	}
}
</style>
