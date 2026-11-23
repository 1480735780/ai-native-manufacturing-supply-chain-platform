<script lang="ts" setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import type { FormInstance } from "element-plus";
import {
	listCusOthers,
	getCusOtherDetail,
	addCusOther,
	updateCusOther,
	removeCusOthers,
	exportCusOthers,
	importCusOthers,
	listCustomerNames,
	listIndustryClassNames,
	listEnterpriseAttrNames,
	listEnterpriseStatusNames,
	listEnterpriseLevelNames,
} from "@/apis/base-data/index.js";
import { errText, useBaseDataPage } from "../composables/use-base-data-page";
import { usePermission } from "@/composables/use-permission";
import { toDictOptions, toOptions } from "../composables/normalize-options";

definePage({
	meta: {
		menuType: "page",
		text: "第三方客户",
		icon: "Avatar",
	},
});

const keyword = reactive({ keHuBianMa: "", suoShuKeHu: "", zhongWenQch: "" });
const customerOptions = ref<{ label: string; value: string }[]>([]);
const industryOptions = ref<{ label: string; value: string }[]>([]);
const attrOptions = ref<{ label: string; value: string }[]>([]);
const statusOptions = ref<{ label: string; value: string }[]>([]);
const levelOptions = ref<{ label: string; value: string }[]>([]);

/**
 * 五个下拉的响应结构各不相同，统一交给 normalize-options 处理：
 *  - 所属客户：Java `/md/customer/customer-name-list` → `[{ id, keHuBianMa, zhongWenQch }]`
 *  - 行业分类：C++ → `{ enterpriseNameList: string[] }`
 *  - 企业属性：C++ → `{ rows: [{ com_type_code, com_type_name, id }] }`
 *  - 企业状态：C++ → `{ items: [{ statusonlyid, enterpriseid, enterprisename }] }`
 *  - 企业等级：C++ → `{ name: [], code: [], id: [] }` 平行数组
 */
function normalizeCustomers(data: any) {
	return toOptions(data, ["zhongWenQch", "keHuBianMa"], ["keHuBianMa", "id"]);
}

function normalizeIndustry(data: any) {
	return toDictOptions(data, ["classfl_name", "name"], ["classfl_code", "code", "id"]);
}

function normalizeAttr(data: any) {
	return toDictOptions(data, ["com_type_name", "name"], ["com_type_code", "code", "id"]);
}

function normalizeStatus(data: any) {
	return toDictOptions(data, ["enterprisename", "status", "name"], ["statusonlyid", "status", "id"]);
}

function normalizeLevel(data: any) {
	return toDictOptions(data, ["levelName", "name"], ["levelCode", "code", "id"]);
}

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
	listApi: listCusOthers,
	removeApi: removeCusOthers,
	exportApi: exportCusOthers,
	importApi: importCusOthers,
	rowKey: (row) => row.id,
	rowLabel: (row) => row.zhongWenQch || row.keHuBianMa,
	fileName: "第三方客户",
	loadFailText: "第三方客户数据加载失败",
});

/** 只读角色（财务/客户等）只能查看详情，不显示写操作入口 */
const { canWrite } = usePermission();

setQueryBuilder(() => ({
	keHuBianMa: keyword.keHuBianMa,
	suoShuKeHu: keyword.suoShuKeHu,
	zhongWenQch: keyword.zhongWenQch,
}));

const emptyForm = {
	id: "",
	keHuBianMa: "",
	suoShuKeHu: "",
	zhongWenQch: "",
	keHuJianCheng: "",
	zhuJiMa: "",
	keHuYingWen: "",
	xingYeFenLei: "",
	keHuDengJi: "",
	suoShuXingYe: "",
	keHuZhuangTai: "",
	diZhi: "",
	youZhengBianMa: "",
	zhuLianXiRen: "",
	dianHua: "",
	shouJi: "",
	chuanZhen: "",
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
		keHuBianMa: row.keHuBianMa ?? "",
		suoShuKeHu: row.suoShuKeHu ?? "",
		zhongWenQch: row.zhongWenQch ?? "",
		keHuJianCheng: row.keHuJianCheng ?? "",
		zhuJiMa: row.zhuJiMa ?? "",
		keHuYingWen: row.keHuYingWen ?? "",
		xingYeFenLei: row.xingYeFenLei ?? "",
		keHuDengJi: row.keHuDengJi ?? "",
		suoShuXingYe: row.suoShuXingYe ?? "",
		keHuZhuangTai: row.keHuZhuangTai ?? "",
		diZhi: row.diZhi ?? "",
		youZhengBianMa: row.youZhengBianMa ?? "",
		zhuLianXiRen: row.zhuLianXiRen ?? "",
		dianHua: row.dianHua ?? "",
		shouJi: row.shouJi ?? "",
		chuanZhen: row.chuanZhen ?? "",
		emaildiZhi: row.emaildiZhi ?? "",
		beiZhu: row.beiZhu ?? "",
	});
	dialogVisible.value = true;
}

function openDetail(row: any) {
	detailVisible.value = true;
	detailLoading.value = true;
	detail.value = { ...row };
	getCusOtherDetail(
		row.keHuBianMa,
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
			await addCusOther({ ...form });
		} else {
			await updateCusOther({ ...form, id: form.id });
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
	listCustomerNames(
		(data: any) => {
			customerOptions.value = normalizeCustomers(data).map((item: any) => ({
				label: item.label === item.value ? item.label : `${item.label}（${item.value}）`,
				value: item.value,
			}));
		},
		() => {
			customerOptions.value = [];
		},
	);
	listIndustryClassNames(
		(data: any) => {
			industryOptions.value = normalizeIndustry(data);
		},
		() => {
			industryOptions.value = [];
		},
	);
	listEnterpriseAttrNames(
		(data: any) => {
			attrOptions.value = normalizeAttr(data);
		},
		() => {
			attrOptions.value = [];
		},
	);
	listEnterpriseStatusNames(
		(data: any) => {
			statusOptions.value = normalizeStatus(data);
		},
		() => {
			statusOptions.value = [];
		},
	);
	listEnterpriseLevelNames(
		(data: any) => {
			levelOptions.value = normalizeLevel(data);
		},
		() => {
			levelOptions.value = [];
		},
	);
});
</script>

<template>
	<section class="base-data-page">
		<h2>第三方客户</h2>
		<div class="toolbar">
			<el-input v-model="keyword.keHuBianMa" placeholder="客户编码" clearable style="width: 160px" @keyup.enter="handleSearch" />
			<el-input v-model="keyword.suoShuKeHu" placeholder="所属客户" clearable style="width: 160px" @keyup.enter="handleSearch" />
			<el-input v-model="keyword.zhongWenQch" placeholder="中文全称" clearable style="width: 180px" @keyup.enter="handleSearch" />
			<el-button type="primary" @click="handleSearch">查询</el-button>
			<el-button v-if="canWrite" type="success" @click="openAdd">录入</el-button>
			<el-button @click="exportData">导出</el-button>
			<el-button v-if="canWrite" @click="openImport">导入</el-button>
			<el-button v-if="canWrite" type="danger" plain :disabled="selectedRows.length === 0" @click="removeSelected">批量删除</el-button>
		</div>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%" @selection-change="handleSelectionChange">
			<el-table-column v-if="canWrite" type="selection" width="45" />
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="keHuBianMa" label="客户编码" min-width="140" show-overflow-tooltip />
			<el-table-column prop="suoShuKeHu" label="所属客户" min-width="140" show-overflow-tooltip />
			<el-table-column prop="zhongWenQch" label="中文全称" min-width="200" show-overflow-tooltip />
			<el-table-column prop="keHuJianCheng" label="客户简称" min-width="130" show-overflow-tooltip />
			<el-table-column prop="keHuDengJi" label="客户等级" min-width="110" show-overflow-tooltip />
			<el-table-column prop="diZhi" label="地址" min-width="200" show-overflow-tooltip />
			<el-table-column prop="zhuLianXiRen" label="主联系人" min-width="110" show-overflow-tooltip />
			<el-table-column prop="dianHua" label="电话" min-width="130" show-overflow-tooltip />
			<el-table-column prop="shouJi" label="手机" min-width="130" show-overflow-tooltip />
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

		<el-dialog v-model="dialogVisible" :title="dialogMode === 'add' ? '录入第三方客户' : '修改第三方客户'" width="720px" :close-on-click-modal="false" destroy-on-close>
			<el-form ref="formRef" :model="form" label-width="100px">
				<el-row :gutter="12">
					<el-col :span="12">
						<el-form-item label="客户编码" prop="keHuBianMa" :rules="[{ required: true, message: '请输入客户编码', trigger: 'blur' }]">
							<el-input v-model="form.keHuBianMa" :disabled="dialogMode === 'edit'" placeholder="如 01STAR" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="中文全称" prop="zhongWenQch" :rules="[{ required: true, message: '请输入中文全称', trigger: 'blur' }]">
							<el-input v-model="form.zhongWenQch" />
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="所属客户">
							<el-select v-model="form.suoShuKeHu" clearable filterable style="width: 100%" placeholder="请选择">
								<el-option v-for="item in customerOptions" :key="item.value" :label="item.label" :value="item.value" />
							</el-select>
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="客户简称"><el-input v-model="form.keHuJianCheng" /></el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="助记码"><el-input v-model="form.zhuJiMa" /></el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="英文名称"><el-input v-model="form.keHuYingWen" /></el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="行业分类">
							<el-select v-model="form.suoShuXingYe" clearable filterable style="width: 100%" placeholder="请选择">
								<el-option v-for="item in industryOptions" :key="item.value" :label="item.label" :value="item.value" />
							</el-select>
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="企业属性">
							<el-select v-model="form.xingYeFenLei" clearable filterable style="width: 100%" placeholder="请选择">
								<el-option v-for="item in attrOptions" :key="item.value" :label="item.label" :value="item.value" />
							</el-select>
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="企业状态">
							<el-select v-model="form.keHuZhuangTai" clearable filterable style="width: 100%" placeholder="请选择">
								<el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
							</el-select>
						</el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="企业等级">
							<el-select v-model="form.keHuDengJi" clearable filterable style="width: 100%" placeholder="请选择">
								<el-option v-for="item in levelOptions" :key="item.value" :label="item.label" :value="item.value" />
							</el-select>
						</el-form-item>
					</el-col>
					<el-col :span="24">
						<el-form-item label="地址"><el-input v-model="form.diZhi" /></el-form-item>
					</el-col>
					<el-col :span="12">
						<el-form-item label="邮政编码"><el-input v-model="form.youZhengBianMa" /></el-form-item>
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
						<el-form-item label="传真"><el-input v-model="form.chuanZhen" /></el-form-item>
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

		<el-drawer v-model="detailVisible" title="第三方客户详情" size="560px">
			<div v-loading="detailLoading" class="detail-list">
				<p><span>客户编码</span>{{ detail.keHuBianMa || "-" }}</p>
				<p><span>所属客户</span>{{ detail.suoShuKeHu || "-" }}</p>
				<p><span>中文全称</span>{{ detail.zhongWenQch || "-" }}</p>
				<p><span>客户简称</span>{{ detail.keHuJianCheng || "-" }}</p>
				<p><span>助记码</span>{{ detail.zhuJiMa || "-" }}</p>
				<p><span>英文名称</span>{{ detail.keHuYingWen || "-" }}</p>
				<p><span>行业分类</span>{{ detail.suoShuXingYe || "-" }}</p>
				<p><span>企业属性</span>{{ detail.xingYeFenLei || "-" }}</p>
				<p><span>企业状态</span>{{ detail.keHuZhuangTai || "-" }}</p>
				<p><span>企业等级</span>{{ detail.keHuDengJi || "-" }}</p>
				<p><span>地址</span>{{ detail.diZhi || "-" }}</p>
				<p><span>邮政编码</span>{{ detail.youZhengBianMa || "-" }}</p>
				<p><span>主联系人</span>{{ detail.zhuLianXiRen || "-" }}</p>
				<p><span>电话</span>{{ detail.dianHua || "-" }}</p>
				<p><span>手机</span>{{ detail.shouJi || "-" }}</p>
				<p><span>传真</span>{{ detail.chuanZhen || "-" }}</p>
				<p><span>Email</span>{{ detail.emaildiZhi || "-" }}</p>
				<p><span>备注</span>{{ detail.beiZhu || "-" }}</p>
			</div>
		</el-drawer>

		<el-dialog v-model="importVisible" title="导入第三方客户" width="460px" :close-on-click-modal="false">
			<el-upload
				v-model:file-list="importFileList"
				:auto-upload="false"
				:limit="1"
				accept=".xlsx,.xls"
				:on-change="handleImportChange"
				:on-remove="handleImportRemove"
			>
				<el-button type="primary">选择文件</el-button>
				<template #tip><div class="el-upload__tip">请使用导出的第三方客户文件作为导入模板</div></template>
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
