<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { listPlatIo, addPlatIo, updatePlatIo } from "@/apis/yuetaiguanli/index";
import { listPlatformNames } from "@/apis/yuetaiguanli/index";

definePage({
	meta: {
		menuType: "page",
		text: "月台计划",
		icon: "IconSetting",
	},
});

interface PlatIoRow {
	id: string;
	carno?: string;
	docId?: string;
	platId?: string;
	inData?: string;
	outData?: string;
	platSta?: string;
	platBeizhu?: string;
	planIndata?: string;
	planOutdata?: string;
	platOper?: string;
	createName?: string;
	createDate?: string;
}

interface PlatformOption {
	id: string;
	platform_code: string;
	platform_name: string;
}

const loading = ref(false);
const rows = ref<PlatIoRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const platformOptions = ref<PlatformOption[]>([]);

const query = ref({ carno: "", docId: "", platId: "", platSta: "" });

const dialogVisible = ref(false);
const isEdit = ref(false);
const form = ref({
	id: "",
	carno: "",
	docId: "",
	platId: "",
	planIndata: "",
	planOutdata: "",
	platSta: "待进场",
	platOper: "",
	platBeizhu: "",
});

function loadData() {
	loading.value = true;
	listPlatIo(
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
			ElMessage.error("月台计划列表加载失败");
		},
	);
}

function loadPlatformOptions() {
	listPlatformNames(
		(data: any) => {
			platformOptions.value = Array.isArray(data) ? data : [];
		},
		() => {
			platformOptions.value = [];
		},
	);
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	query.value = { carno: "", docId: "", platId: "", platSta: "" };
	pageIndex.value = 1;
	loadData();
}

function openAdd() {
	isEdit.value = false;
	form.value = {
		id: "",
		carno: "",
		docId: "",
		platId: "",
		planIndata: "",
		planOutdata: "",
		platSta: "待进场",
		platOper: "",
		platBeizhu: "",
	};
	dialogVisible.value = true;
}

function openEdit(row: PlatIoRow) {
	isEdit.value = true;
	form.value = {
		id: row.id,
		carno: row.carno ?? "",
		docId: row.docId ?? "",
		platId: row.platId ?? "",
		planIndata: row.planIndata ?? "",
		planOutdata: row.planOutdata ?? "",
		platSta: row.platSta ?? "",
		platOper: row.platOper ?? "",
		platBeizhu: row.platBeizhu ?? "",
	};
	dialogVisible.value = true;
}

function handleSave() {
	if (!form.value.carno.trim() || !form.value.docId.trim() || !form.value.platId) {
		ElMessage.warning("车号、单据编号、月台为必填项");
		return;
	}
	loading.value = true;
	const payload = {
		id: form.value.id || undefined,
		carno: form.value.carno,
		docId: form.value.docId,
		platId: form.value.platId,
		planIndata: form.value.planIndata || undefined,
		planOutdata: form.value.planOutdata || undefined,
		platSta: form.value.platSta,
		platOper: form.value.platOper,
		platBeizhu: form.value.platBeizhu,
	};
	const done = (ok: boolean) => {
		loading.value = false;
		if (ok) {
			ElMessage.success(isEdit.value ? "修改成功" : "录入成功");
			dialogVisible.value = false;
			loadData();
		} else {
			ElMessage.error(isEdit.value ? "修改失败（可能重复或字段非法）" : "录入失败（可能重复或字段非法）");
		}
	};
	if (isEdit.value) {
		updatePlatIo(
			payload,
			() => done(true),
			() => done(false),
		);
	} else {
		addPlatIo(
			payload,
			() => done(true),
			() => done(false),
		);
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
	loadPlatformOptions();
});
</script>

<template>
	<section>
		<el-card shadow="never">
			<el-form :model="query" inline>
				<el-form-item label="车号">
					<el-input v-model="query.carno" clearable placeholder="车号（模糊）" style="width: 140px" />
				</el-form-item>
				<el-form-item label="单据编号">
					<el-input v-model="query.docId" clearable placeholder="单据编号" style="width: 150px" />
				</el-form-item>
				<el-form-item label="月台">
					<el-select v-model="query.platId" clearable placeholder="全部月台" style="width: 170px">
						<el-option
							v-for="opt in platformOptions"
							:key="opt.id"
							:label="`${opt.platform_name}（${opt.platform_code}）`"
							:value="opt.id"
						/>
					</el-select>
				</el-form-item>
				<el-form-item label="状态">
					<el-input v-model="query.platSta" clearable placeholder="月台状态" style="width: 120px" />
				</el-form-item>
				<el-form-item>
					<el-button type="primary" @click="handleSearch">查询</el-button>
					<el-button @click="handleReset">重置</el-button>
				</el-form-item>
			</el-form>
		</el-card>

		<el-card shadow="never" style="margin-top: 12px">
			<div style="margin-bottom: 12px">
				<el-button type="primary" @click="openAdd">录入月台计划</el-button>
			</div>

			<el-table v-loading="loading" :data="rows" border stripe style="width: 100%">
				<el-table-column type="index" label="序号" width="60" />
				<el-table-column prop="carno" label="车号" width="120" />
				<el-table-column prop="docId" label="单据编号" min-width="150" show-overflow-tooltip />
				<el-table-column prop="platId" label="月台编号" width="140" show-overflow-tooltip />
				<el-table-column prop="planIndata" label="计划进入时间" width="170" />
				<el-table-column prop="planOutdata" label="计划驶出时间" width="170" />
				<el-table-column prop="inData" label="实际进入" width="170" />
				<el-table-column prop="outData" label="实际驶出" width="170" />
				<el-table-column prop="platSta" label="月台状态" width="100" />
				<el-table-column prop="platOper" label="月台操作" width="100" />
				<el-table-column prop="platBeizhu" label="备注" min-width="140" show-overflow-tooltip />
				<el-table-column label="操作" width="100" fixed="right">
					<template #default="{ row }">
						<el-button link type="primary" @click="openEdit(row)">修改</el-button>
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

		<el-dialog v-model="dialogVisible" :title="isEdit ? '修改月台计划' : '录入月台计划'" width="560px">
			<el-form :model="form" label-width="100px">
				<el-form-item label="车号" required>
					<el-input v-model="form.carno" placeholder="如 京A88888" :disabled="isEdit" />
				</el-form-item>
				<el-form-item label="单据编号" required>
					<el-input v-model="form.docId" placeholder="如 DOC123456" :disabled="isEdit" />
				</el-form-item>
				<el-form-item label="月台" required>
					<el-select v-model="form.platId" placeholder="选择月台" style="width: 100%">
						<el-option
							v-for="opt in platformOptions"
							:key="opt.id"
							:label="`${opt.platform_name}（${opt.platform_code}）`"
							:value="opt.id"
						/>
					</el-select>
				</el-form-item>
				<el-form-item label="计划进入时间">
					<el-date-picker
						v-model="form.planIndata"
						type="datetime"
						value-format="YYYY-MM-DDTHH:mm:ss"
						style="width: 100%"
					/>
				</el-form-item>
				<el-form-item label="计划驶出时间">
					<el-date-picker
						v-model="form.planOutdata"
						type="datetime"
						value-format="YYYY-MM-DDTHH:mm:ss"
						style="width: 100%"
					/>
				</el-form-item>
				<el-form-item label="月台状态">
					<el-input v-model="form.platSta" placeholder="如 待进场/占用中/已完成" />
				</el-form-item>
				<el-form-item label="月台操作">
					<el-input v-model="form.platOper" placeholder="如 装卸货" />
				</el-form-item>
				<el-form-item label="备注">
					<el-input v-model="form.platBeizhu" type="textarea" :rows="2" />
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="dialogVisible = false">取消</el-button>
				<el-button type="primary" :loading="loading" @click="handleSave">保存</el-button>
			</template>
		</el-dialog>
	</section>
</template>
