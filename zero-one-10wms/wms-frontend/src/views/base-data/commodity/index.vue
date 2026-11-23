<script lang="ts" setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import type { FormInstance } from "element-plus";
import {
	listGoods,
	getGoodsDetail,
	addGoods,
	updateGoods,
	removeGoods,
	exportGoods,
	importGoods,
	printGoodsLabel,
	listGoodsBrandNames,
	getGoodsCategoryTree,
	listMeasurementUnitNames,
	listCustomerNames,
	saveBlob,
} from "@/apis/base-data/index.js";
import { errText, useBaseDataPage } from "../composables/use-base-data-page";
import { usePermission } from "@/composables/use-permission";
import { toOptions, toTree } from "../composables/normalize-options";

definePage({
	meta: {
		menuType: "page",
		text: "商品",
		icon: "IconSetting",
	},
});

const keyword = reactive({
	shpMingCheng: "",
	shpBianMa: "",
	shpTiaoMa: "",
	ywMingCheng: "",
});

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
	listApi: listGoods,
	removeApi: removeGoods,
	exportApi: exportGoods,
	importApi: importGoods,
	rowKey: (row) => row.shpBianMa,
	rowLabel: (row) => row.shpMingCheng || row.shpBianMa,
	fileName: "商品",
	loadFailText: "商品数据加载失败",
});

/** 只读角色（财务/客户等）只能查看详情，不显示写操作入口 */
const { canWrite } = usePermission();

setQueryBuilder(() => ({
	shpMingCheng: keyword.shpMingCheng,
	shpBianMa: keyword.shpBianMa,
	shpTiaoMa: keyword.shpTiaoMa,
	ywMingCheng: keyword.ywMingCheng,
}));

/* ===================== 下拉数据：品牌 / 类目树 / 单位 / 货主 ===================== */

const brandOptions = ref<{ label: string; value: string }[]>([]);
const unitOptions = ref<{ label: string; value: string }[]>([]);
const ownerOptions = ref<{ label: string; value: string }[]>([]);
const categoryTree = ref<any[]>([]);

/** 品牌：后端返回 [{ id, goodsBrandName, goodsBrandCode }] */
function loadBrands() {
	listGoodsBrandNames(
		(data: any) => {
			brandOptions.value = toOptions(data, ["goodsBrandName", "name"], ["goodsBrandName", "goodsBrandCode"]);
		},
		() => {
			brandOptions.value = [];
		},
	);
}

/** 计量单位：后端返回 string[] */
function loadUnits() {
	listMeasurementUnitNames(
		(data: any) => {
			unitOptions.value = toOptions(data, ["name", "unitName"], []);
		},
		() => {
			unitOptions.value = [];
		},
	);
}

/** 货主客户：返回 [{ id, keHuBianMa, zhongWenQch }] */
function loadOwners() {
	listCustomerNames(
		(data: any) => {
			ownerOptions.value = toOptions(data, ["zhongWenQch", "keHuBianMa"], ["keHuBianMa", "id"]);
		},
		() => {
			ownerOptions.value = [];
		},
	);
}

/**
 * 商品类目：c1-bconf 的 `/gc/query-category-tree` 实际返回的是**扁平列表**，
 * 形如 `{ DTOList: [{ id, category_code, category_name, category_level, pid, top_node }] }`，
 * 没有 children 字段，必须前端按 pid 建树。
 * 取值用 `category_code`：md_goods 的「商品类目」列存的就是编码（GoodsListDTO.categoryCode）。
 */
function loadCategoryTree() {
	getGoodsCategoryTree(
		(data: any) => {
			categoryTree.value = toTree(data, {
				nodeIdKeys: ["id"],
				nameKeys: ["category_name", "categoryName", "name", "label"],
				pidKeys: ["pid", "parentId", "parent_id"],
				valueKeys: ["category_code", "categoryCode", "code"],
			});
		},
		() => {
			categoryTree.value = [];
		},
	);
}

/* ============================ 录入 / 修改表单 ============================ */

const emptyForm = {
	shpBianMa: "",
	shpMingCheng: "",
	ywMingCheng: "",
	rwMingCheng: "",
	shpPinPai: "",
	categoryCode: "",
	price: "",
	shpTiaoMa: "",
	bzhiQi: "",
	shlDanWei: "",
	shpGuiGe: "",
	tiJiCm: "",
	zhlKg: "",
	jshDanWei: "",
	chlShl: "",
	jfShpLei: "",
	sku: "",
	chDanPin: "",
	kuDanPin: "",
	gaoDanPin: "",
	minStock: "",
	acceptanceDays: "",
	mpDanCeng: "",
	mpCengGao: "",
	sysCompanyCode: "",
};
const form = reactive({ ...emptyForm });
const formRef = ref<FormInstance>();
const dialogVisible = ref(false);
const dialogMode = ref<"add" | "edit">("add");
const saving = ref(false);

const numberFields = [
	"price",
	"bzhiQi",
	"tiJiCm",
	"zhlKg",
	"chlShl",
	"minStock",
	"acceptanceDays",
	"mpDanCeng",
	"mpCengGao",
];

/** 数字字段统一校验：允许为空，非空时必须是数字 */
function numberRule(_rule: any, value: string, callback: (error?: Error) => void) {
	if (value === "" || value === null || value === undefined) {
		return callback();
	}
	if (/^-?\d+(\.\d+)?$/.test(String(value))) {
		return callback();
	}
	return callback(new Error("请输入数字"));
}

function openAdd() {
	dialogMode.value = "add";
	Object.assign(form, emptyForm);
	dialogVisible.value = true;
}

function openEdit(row: any) {
	dialogMode.value = "edit";
	Object.assign(form, emptyForm);
	Object.keys(emptyForm).forEach((key) => {
		const value = row[key];
		if (value !== null && value !== undefined) (form as any)[key] = String(value);
	});
	dialogVisible.value = true;
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
			await addGoods({ ...form });
			ElMessage.success("录入成功");
		} else {
			// 后端以商品编码作为更新定位键，编码不可修改
			await updateGoods({ ...form });
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

/* ==================== 详情抽屉（决策三：并入商品页） ==================== */

const detailVisible = ref(false);
const detailLoading = ref(false);
const detail = ref<any>({});

function openDetail(row: any) {
	detailVisible.value = true;
	detailLoading.value = true;
	detail.value = { ...row };
	getGoodsDetail(
		row.shpBianMa,
		(data: any) => {
			detail.value = data ?? row;
			detailLoading.value = false;
		},
		() => {
			detailLoading.value = false;
		},
	);
}

function detailText(value: any) {
	return value === null || value === undefined || value === "" ? "-" : value;
}

/* ============================== 打印标签 ============================== */

const printing = ref("");

async function handlePrint(row: any) {
	printing.value = row.shpBianMa;
	try {
		const blob = await printGoodsLabel(row.shpBianMa);
		saveBlob(blob, `商品标签_${row.shpBianMa}.pdf`);
		ElMessage.success("标签已生成");
	} catch (err: any) {
		ElMessage.error(errText(err, "打印标签失败"));
	} finally {
		printing.value = "";
	}
}

onMounted(() => {
	loadData();
	loadBrands();
	loadUnits();
	loadOwners();
	loadCategoryTree();
});
</script>

<template>
	<section class="base-data-page">
		<h2>商品</h2>
		<div class="toolbar">
			<el-input v-model="keyword.shpMingCheng" placeholder="商品名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
			<el-input v-model="keyword.shpBianMa" placeholder="商品编码" clearable style="width: 160px" @keyup.enter="handleSearch" />
			<el-input v-model="keyword.shpTiaoMa" placeholder="条码" clearable style="width: 150px" @keyup.enter="handleSearch" />
			<el-input v-model="keyword.ywMingCheng" placeholder="英文名" clearable style="width: 150px" @keyup.enter="handleSearch" />
			<el-button type="primary" @click="handleSearch">查询</el-button>
			<el-button v-if="canWrite" type="success" @click="openAdd">录入</el-button>
			<el-button @click="exportData">导出</el-button>
			<el-button v-if="canWrite" @click="openImport">导入</el-button>
			<el-button v-if="canWrite" type="danger" plain :disabled="selectedRows.length === 0" @click="removeSelected">批量删除</el-button>
		</div>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%" @selection-change="handleSelectionChange">
			<el-table-column v-if="canWrite" type="selection" width="45" />
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="shpBianMa" label="商品编码" min-width="140" show-overflow-tooltip />
			<el-table-column prop="shpMingCheng" label="商品名称" min-width="180" show-overflow-tooltip />
			<el-table-column prop="ywMingCheng" label="英文名" min-width="150" show-overflow-tooltip />
			<el-table-column prop="shlDanWei" label="计量单位" width="100" />
			<el-table-column prop="shpGuiGe" label="规格" min-width="120" show-overflow-tooltip />
			<el-table-column prop="categoryCode" label="商品类目" min-width="130" show-overflow-tooltip />
			<el-table-column prop="chpShuXing" label="产品属性" min-width="110" show-overflow-tooltip />
			<el-table-column prop="price" label="价格" width="100" />
			<el-table-column prop="shpTiaoMa" label="条码" min-width="140" show-overflow-tooltip />
			<el-table-column prop="bzhiQi" label="保质期" width="90" />
			<el-table-column label="操作" :width="canWrite ? 220 : 130" fixed="right">
				<template #default="{ row }">
					<el-button link type="primary" @click="openDetail(row)">查看</el-button>
					<el-button v-if="canWrite" link type="primary" @click="openEdit(row)">修改</el-button>
					<el-button link type="primary" :loading="printing === row.shpBianMa" @click="handlePrint(row)">打印</el-button>
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

		<el-dialog
			v-model="dialogVisible"
			:title="dialogMode === 'add' ? '录入商品' : '修改商品'"
			width="900px"
			top="6vh"
			:close-on-click-modal="false"
			destroy-on-close
		>
			<el-form ref="formRef" :model="form" label-width="96px">
				<el-divider content-position="left">基础信息</el-divider>
				<el-row :gutter="12">
					<el-col :span="8">
						<el-form-item label="商品编码" prop="shpBianMa" :rules="[{ required: true, message: '请输入商品编码', trigger: 'blur' }]">
							<el-input v-model="form.shpBianMa" :disabled="dialogMode === 'edit'" placeholder="修改时不可变更" />
						</el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="商品名称" prop="shpMingCheng" :rules="[{ required: true, message: '请输入商品名称', trigger: 'blur' }]">
							<el-input v-model="form.shpMingCheng" />
						</el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="条码"><el-input v-model="form.shpTiaoMa" /></el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="英文名"><el-input v-model="form.ywMingCheng" /></el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="日文名"><el-input v-model="form.rwMingCheng" /></el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="商品品牌">
							<el-select v-model="form.shpPinPai" clearable filterable style="width: 100%" placeholder="请选择品牌">
								<el-option v-for="item in brandOptions" :key="item.value" :label="item.label" :value="item.value" />
							</el-select>
						</el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="商品类目">
							<el-tree-select
								v-model="form.categoryCode"
								:data="categoryTree"
								check-strictly
								clearable
								filterable
								style="width: 100%"
								placeholder="请选择商品类目"
							/>
						</el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="价格" prop="price" :rules="[{ validator: numberRule, trigger: 'blur' }]">
							<el-input v-model="form.price" />
						</el-form-item>
					</el-col>
				</el-row>

				<el-divider content-position="left">规格与单位</el-divider>
				<el-row :gutter="12">
					<el-col :span="8">
						<el-form-item label="计量单位">
							<el-select v-model="form.shlDanWei" clearable filterable style="width: 100%" placeholder="请选择单位">
								<el-option v-for="item in unitOptions" :key="item.value" :label="item.label" :value="item.value" />
							</el-select>
						</el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="规格"><el-input v-model="form.shpGuiGe" /></el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="保质期" prop="bzhiQi" :rules="[{ validator: numberRule, trigger: 'blur' }]">
							<el-input v-model="form.bzhiQi" />
						</el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="体积(cm³)" prop="tiJiCm" :rules="[{ validator: numberRule, trigger: 'blur' }]">
							<el-input v-model="form.tiJiCm" />
						</el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="重量(kg)" prop="zhlKg" :rules="[{ validator: numberRule, trigger: 'blur' }]">
							<el-input v-model="form.zhlKg" />
						</el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="拆零单位">
							<el-select v-model="form.jshDanWei" clearable filterable style="width: 100%" placeholder="请选择单位">
								<el-option v-for="item in unitOptions" :key="item.value" :label="item.label" :value="item.value" />
							</el-select>
						</el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="拆零数量" prop="chlShl" :rules="[{ validator: numberRule, trigger: 'blur' }]">
							<el-input v-model="form.chlShl" />
						</el-form-item>
					</el-col>
				</el-row>

				<el-divider content-position="left">库存与其他</el-divider>
				<el-row :gutter="12">
					<el-col :span="8">
						<el-form-item label="货主客户">
							<el-select v-model="form.sysCompanyCode" clearable filterable style="width: 100%" placeholder="请选择货主">
								<el-option v-for="item in ownerOptions" :key="item.value" :label="item.label" :value="item.value" />
							</el-select>
						</el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="SKU"><el-input v-model="form.sku" /></el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="计费商品类"><el-input v-model="form.jfShpLei" /></el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="箱单品"><el-input v-model="form.chDanPin" /></el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="库内单品"><el-input v-model="form.kuDanPin" /></el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="高位单品"><el-input v-model="form.gaoDanPin" /></el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="最小库存" prop="minStock" :rules="[{ validator: numberRule, trigger: 'blur' }]">
							<el-input v-model="form.minStock" />
						</el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="验收天数" prop="acceptanceDays" :rules="[{ validator: numberRule, trigger: 'blur' }]">
							<el-input v-model="form.acceptanceDays" />
						</el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="码盘单层" prop="mpDanCeng" :rules="[{ validator: numberRule, trigger: 'blur' }]">
							<el-input v-model="form.mpDanCeng" />
						</el-form-item>
					</el-col>
					<el-col :span="8">
						<el-form-item label="码盘层高" prop="mpCengGao" :rules="[{ validator: numberRule, trigger: 'blur' }]">
							<el-input v-model="form.mpCengGao" />
						</el-form-item>
					</el-col>
				</el-row>
				<el-alert
					type="info"
					:closable="false"
					show-icon
					title="「产品属性」「拆零控制」「产品大类」的取值域待产品确认，暂不开放录入；已有数据可在详情抽屉查看。"
				/>
			</el-form>
			<template #footer>
				<el-button @click="dialogVisible = false">取消</el-button>
				<el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
			</template>
		</el-dialog>

		<el-drawer v-model="detailVisible" title="商品详情" size="560px">
			<div v-loading="detailLoading" class="detail-list">
				<p class="detail-group">基础信息</p>
				<p><span>商品编码</span>{{ detailText(detail.shpBianMa) }}</p>
				<p><span>商品名称</span>{{ detailText(detail.shpMingCheng) }}</p>
				<p><span>英文名</span>{{ detailText(detail.ywMingCheng) }}</p>
				<p><span>日文名</span>{{ detailText(detail.rwMingCheng) }}</p>
				<p><span>商品品牌</span>{{ detailText(detail.shpPinPai) }}</p>
				<p><span>商品类目</span>{{ detailText(detail.categoryCode) }}</p>
				<p><span>产品大类</span>{{ detailText(detail.categoryId) }}</p>
				<p><span>产品属性</span>{{ detailText(detail.chpShuXing) }}</p>
				<p><span>价格</span>{{ detailText(detail.price) }}</p>
				<p><span>条码</span>{{ detailText(detail.shpTiaoMa) }}</p>
				<p class="detail-group">规格与单位</p>
				<p><span>计量单位</span>{{ detailText(detail.shlDanWei) }}</p>
				<p><span>规格</span>{{ detailText(detail.shpGuiGe) }}</p>
				<p><span>保质期</span>{{ detailText(detail.bzhiQi) }}</p>
				<p><span>体积(cm³)</span>{{ detailText(detail.tiJiCm) }}</p>
				<p><span>重量(kg)</span>{{ detailText(detail.zhlKg) }}</p>
				<p><span>拆零控制</span>{{ detailText(detail.chlKongZhi) }}</p>
				<p><span>拆零单位</span>{{ detailText(detail.jshDanWei) }}</p>
				<p><span>拆零数量</span>{{ detailText(detail.chlShl) }}</p>
				<p class="detail-group">库存与其他</p>
				<p><span>货主客户</span>{{ detailText(detail.sysCompanyCode) }}</p>
				<p><span>SKU</span>{{ detailText(detail.sku) }}</p>
				<p><span>计费商品类</span>{{ detailText(detail.jfShpLei) }}</p>
				<p><span>箱单品</span>{{ detailText(detail.chDanPin) }}</p>
				<p><span>库内单品</span>{{ detailText(detail.kuDanPin) }}</p>
				<p><span>高位单品</span>{{ detailText(detail.gaoDanPin) }}</p>
				<p><span>最小库存</span>{{ detailText(detail.minStock) }}</p>
				<p><span>验收天数</span>{{ detailText(detail.acceptanceDays) }}</p>
				<p><span>码盘单层</span>{{ detailText(detail.mpDanCeng) }}</p>
				<p><span>码盘层高</span>{{ detailText(detail.mpCengGao) }}</p>
			</div>
			<template #footer>
				<el-button @click="detailVisible = false">关闭</el-button>
				<el-button type="primary" :loading="printing === detail.shpBianMa" @click="handlePrint(detail)">打印标签</el-button>
			</template>
		</el-drawer>

		<el-dialog v-model="importVisible" title="导入商品" width="460px" :close-on-click-modal="false">
			<el-upload
				v-model:file-list="importFileList"
				:auto-upload="false"
				:limit="1"
				accept=".xlsx,.xls"
				:on-change="handleImportChange"
				:on-remove="handleImportRemove"
			>
				<el-button type="primary">选择文件</el-button>
				<template #tip><div class="el-upload__tip">请使用导出的商品文件作为导入模板</div></template>
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
	.detail-list {
		p {
			display: flex;
			gap: 12px;
			margin: 0;
			padding: 10px 0;
			border-bottom: 1px solid var(--el-border-color-lighter);
			span:first-child {
				width: 96px;
				color: var(--el-text-color-secondary);
				flex-shrink: 0;
			}
		}
		.detail-group {
			margin-top: 8px;
			font-weight: 600;
			color: var(--el-text-color-primary);
			background: var(--el-fill-color-light);
			padding-left: 8px;
		}
	}
}
</style>
