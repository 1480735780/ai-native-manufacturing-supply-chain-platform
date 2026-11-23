<script lang="ts" setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import type { FormInstance } from "element-plus";
import {
	listProviders,
	getProviderDetail,
	addProvider,
	updateProvider,
	removeProviders,
	exportProviders,
	importProviders,
	listEnterpriseAttrNames,
} from "@/apis/base-data/index.js";
import { errText, useBaseDataPage } from "../composables/use-base-data-page";
import { usePermission } from "@/composables/use-permission";
import { toDictOptions } from "../composables/normalize-options";

definePage({
	meta: {
		menuType: "page",
		text: "供应商",
		icon: "Shop",
	},
});

const keyword = reactive({ zhongWenQch: "", gysBianMa: "", zhuJiMa: "" });
const attrOptions = ref<{ label: string; value: string }[]>([]);


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
	listApi: listProviders,
	removeApi: removeProviders,
	exportApi: exportProviders,
	importApi: importProviders,
	rowKey: (row) => row.id,
	rowLabel: (row) => row.zhongWenQch || row.gysBianMa,
	fileName: "供应商",
	loadFailText: "供应商数据加载失败",
});

/** 只读角色（财务/客户等）只能查看详情，不显示写操作入口 */
const { canWrite } = usePermission();

setQueryBuilder(() => ({
	zhongWenQch: keyword.zhongWenQch,
	gysBianMa: keyword.gysBianMa,
	zhuJiMa: keyword.zhuJiMa,
}));

const emptyForm = {
	id: "",
	gysBianMa: "",
	zhongWenQch: "",
	zhuJiMa: "",
	xingYeFenLei: "",
	diZhi: "",
	zhuLianXiRen: "",
	dianHua: "",
	shouJi: "",
	emaildiZhi: "",
	beiZhu: "",
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
		id: row.id ?? "",
		gysBianMa: row.gysBianMa ?? "",
		zhongWenQch: row.zhongWenQch ?? "",
		zhuJiMa: row.zhuJiMa ?? "",
		xingYeFenLei: row.xingYeFenLei ?? "",
		diZhi: row.diZhi ?? "",
		zhuLianXiRen: row.zhuLianXiRen ?? "",
		dianHua: row.dianHua ?? "",
		shouJi: row.shouJi ?? "",
		emaildiZhi: row.emaildiZhi ?? "",
		beiZhu: row.beiZhu ?? "",
	});
	dialogVisible.value = true;
}

function openDetail(row: any) {
	detailVisible.value = true;
	detailLoading.value = true;
	detail.value = { ...row };
	getProviderDetail(
		row.id,
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
			await addProvider({ ...form });
		} else {
			await updateProvider({ ...form, id: form.id });
		}
		ElMessage.success(dialogMode.value === "add" ? "录入成功" : "修改成功");
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
	listEnterpriseAttrNames(
		(data: any) => {
			attrOptions.value = toDictOptions(data, ["com_type_name", "name"], ["com_type_code", "code", "id"]);
		},
		() => {
			attrOptions.value = [];
		},
	);
});
</script>

<template>
	<section class="base-data-page">
		<h2>供应商</h2>
		<div class="toolbar">
			<el-input v-model="keyword.zhongWenQch" placeholder="供应商中文全称" clearable style="width: 200px" @keyup.enter="handleSearch" />
			<el-input v-model="keyword.gysBianMa" placeholder="供应商编码" clearable style="width: 160px" @keyup.enter="handleSearch" />
			<el-input v-model="keyword.zhuJiMa" placeholder="助记码" clearable style="width: 150px" @keyup.enter="handleSearch" />
			<el-button type="primary" @click="handleSearch">查询</el-button>
			<el-button v-if="canWrite" type="success" @click="openAdd">录入</el-button>
			<el-button @click="exportData">导出</el-button>
			<el-button v-if="canWrite" @click="openImport">导入</el-button>
			<el-button v-if="canWrite" type="danger" plain :disabled="selectedRows.length === 0" @click="removeSelected">批量删除</el-button>
		</div>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%" @selection-change="handleSelectionChange">
			<el-table-column v-if="canWrite" type="selection" width="45" />
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="gysBianMa" label="供应商编码" min-width="140" show-overflow-tooltip />
			<el-table-column prop="zhongWenQch" label="中文全称" min-width="200" show-overflow-tooltip />
			<el-table-column prop="xingYeFenLei" label="企业属性" min-width="120" show-overflow-tooltip />
			<el-table-column prop="diZhi" label="地址" min-width="200" show-overflow-tooltip />
			<el-table-column prop="zhuLianXiRen" label="主联系人" min-width="110" show-overflow-tooltip />
			<el-table-column prop="dianHua" label="电话" min-width="130" show-overflow-tooltip />
			<el-table-column prop="shouJi" label="手机" min-width="130" show-overflow-tooltip />
			<el-table-column prop="emaildiZhi" label="Email" min-width="180" show-overflow-tooltip />
			<el-table-column prop="beiZhu" label="备注" min-width="160" show-overflow-tooltip />
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

		<el-dialog v-model="dialogVisible" :title="dialogMode === 'add' ? '录入供应商' : '修改供应商'" width="620px" :close-on-click-modal="false" destroy-on-close>
			<el-form ref="formRef" :model="form" label-width="110px">
				<el-row :gutter="12">
					<el-col :span="12">
						<el-form-item label="供应商编码" prop="gysBianMa" :rules="[{ required: true, message: '请输入供应商编码', trigger: 'blur' }]">
							<el-input v-model="form.gysBianMa" :disabled="dialogMode === 'edit'" placeholder="如 G001" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="中文全称" prop="zhongWenQch" :rules="[{ required: true, message: '请输入中文全称', trigger: 'blur' }]">
							<el-input v-model="form.zhongWenQch" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="助记码"><el-input v-model="form.zhuJiMa" /></el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="企业属性">
							<el-select v-model="form.xingYeFenLei" clearable filterable style="width: 100%" placeholder="请选择">
								<el-option v-for="item in attrOptions" :key="item.value" :label="item.label" :value="item.value" />
							</el-select>
						</el-form-item>
					</el-col>
					<el-col :span="24">
						<el-form-item label="地址"><el-input v-model="form.diZhi" /></el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="主联系人"><el-input v-model="form.zhuLianXiRen" /></el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="电话"><el-input v-model="form.dianHua" /></el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="手机"><el-input v-model="form.shouJi" /></el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="Email"><el-input v-model="form.emaildiZhi" /></el-form-item>
					</el-col>
					<el-col :span="24">
						<el-form-item label="备注"><el-input v-model="form.beiZhu" type="textarea" :rows="2" /></el-form-item>
					</el-col>
				</el-row>
			</el-form>
			<template #footer>
				<el-button @click="dialogVisible = false">取消</el-button>
				<el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
			</template>
		</el-dialog>

		<el-drawer v-model="detailVisible" title="供应商详情" size="520px">
			<div v-loading="detailLoading" class="detail-list">
				<p><span>供应商编码</span>{{ detail.gysBianMa || "-" }}</p>
				<p><span>中文全称</span>{{ detail.zhongWenQch || "-" }}</p>
				<p><span>助记码</span>{{ detail.zhuJiMa || "-" }}</p>
				<p><span>企业属性</span>{{ detail.xingYeFenLei || "-" }}</p>
				<p><span>地址</span>{{ detail.diZhi || "-" }}</p>
				<p><span>主联系人</span>{{ detail.zhuLianXiRen || "-" }}</p>
				<p><span>电话</span>{{ detail.dianHua || "-" }}</p>
				<p><span>手机</span>{{ detail.shouJi || "-" }}</p>
				<p><span>Email</span>{{ detail.emaildiZhi || "-" }}</p>
				<p><span>备注</span>{{ detail.beiZhu || "-" }}</p>
			</div>
		</el-drawer>

		<el-dialog v-model="importVisible" title="导入供应商" width="460px" :close-on-click-modal="false">
			<el-upload
				v-model:file-list="importFileList"
				:auto-upload="false"
				:limit="1"
				accept=".xlsx,.xls"
				:on-change="handleImportChange"
				:on-remove="handleImportRemove"
			>
				<el-button type="primary">选择文件</el-button>
				<template #tip><div class="el-upload__tip">请使用导出的供应商文件作为导入模板</div></template>
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
			width: 100px;
			color: var(--el-text-color-secondary);
			flex-shrink: 0;
		}
	}
}
</style>
