<script lang="ts" setup>
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { listMultiLang, addLang, updateLang, removeLang, refreshLangCache } from "@/apis/system-j3/index";

definePage({
	meta: {
		menuType: "page",
		text: "国际化语言",
		icon: "IconSetting",
	},
});

interface MultiLangRow {
	id?: string;
	keyCode?: string;
	langKey?: string;
	langContext?: string;
	createDate?: string | number;
	updateDate?: string | number;
}

const loading = ref(false);
const rows = ref<MultiLangRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const langKey = ref("");
const langContext = ref("");

const dialogVisible = ref(false);
const dialogMode = ref<"add" | "edit">("add");
const dialogSaving = ref(false);
const refreshing = ref(false);
const formRef = ref();
const form = reactive({
	id: "",
	keyCode: "zh-cn",
	langKey: "",
	langContext: "",
});

const keyCodeOptions = ["zh-cn", "zh-tw", "en", "ja", "ko"];

function errText(err: any, fallback: string) {
	return err?.data?.message || err?.message || err?.response?.data?.message || fallback;
}

function formatDate(value?: string | number) {
	if (value === null || value === undefined || value === "") return "";
	if (typeof value === "number") return new Date(value).toLocaleString();
	return String(value).replace("T", " ").replace(/\.\d+$/, "");
}

function loadData() {
	loading.value = true;
	listMultiLang(
		{
			pageIndex: pageIndex.value,
			pageSize: pageSize.value,
			langKey: langKey.value,
			langContext: langContext.value,
		},
		(data: any) => {
			rows.value = data.rows ?? [];
			total.value = data.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("国际化语言数据加载失败");
		},
	);
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	langKey.value = "";
	langContext.value = "";
	pageIndex.value = 1;
	loadData();
}

function handlePageChange(page: number) {
	pageIndex.value = page;
	loadData();
}

function handleSizeChange(size: number) {
	pageSize.value = size;
	pageIndex.value = 1;
	loadData();
}

function openAdd() {
	dialogMode.value = "add";
	form.id = "";
	form.keyCode = "zh-cn";
	form.langKey = "";
	form.langContext = "";
	dialogVisible.value = true;
}

function openEdit(row: MultiLangRow) {
	dialogMode.value = "edit";
	form.id = row.id ?? "";
	form.keyCode = row.keyCode ?? "zh-cn";
	form.langKey = row.langKey ?? "";
	form.langContext = row.langContext ?? "";
	dialogVisible.value = true;
}

async function submit() {
	const valid = await formRef.value?.validate().catch(() => false);
	if (!valid) return;
	dialogSaving.value = true;
	try {
		const payload = {
			keyCode: form.keyCode,
			langKey: form.langKey,
			langContext: form.langContext,
		};
		if (dialogMode.value === "edit") {
			await updateLang({ ...payload, id: form.id });
		} else {
			await addLang(payload);
		}
		ElMessage.success(dialogMode.value === "add" ? "语言对照录入成功" : "语言对照修改成功");
		dialogVisible.value = false;
		loadData();
	} catch (err: any) {
		ElMessage.error(errText(err, "操作失败"));
	} finally {
		dialogSaving.value = false;
	}
}

async function deleteRow(row: MultiLangRow) {
	try {
		await ElMessageBox.confirm(`确定删除语言对照「${row.langKey ?? ""}」吗？`, "提示", {
			type: "warning",
			confirmButtonText: "确定",
			cancelButtonText: "取消",
		});
	} catch {
		return;
	}
	try {
		await removeLang(row.id as string);
		ElMessage.success("删除成功");
		loadData();
	} catch (err: any) {
		ElMessage.error(errText(err, "删除失败"));
	}
}

async function handleRefreshCache() {
	refreshing.value = true;
	try {
		const res: any = await refreshLangCache();
		ElMessage.success(res?.data || "缓存刷新成功");
	} catch (err: any) {
		ElMessage.error(errText(err, "缓存刷新失败"));
	} finally {
		refreshing.value = false;
	}
}

onMounted(() => {
	loadData();
});
</script>

<template>
	<section class="multi-lang-root">
		<h2>国际化语言</h2>

		<el-form :inline="true" class="filter-bar">
			<el-form-item label="语言键值">
				<el-input v-model="langKey" placeholder="如 common.login" clearable style="width: 200px" />
			</el-form-item>
			<el-form-item label="内容">
				<el-input v-model="langContext" placeholder="如 登录" clearable style="width: 180px" />
			</el-form-item>
			<el-form-item>
				<el-button type="primary" @click="handleSearch">查询</el-button>
				<el-button @click="handleReset">重置</el-button>
				<el-button type="success" @click="openAdd">录入</el-button>
				<el-button :loading="refreshing" @click="handleRefreshCache">刷新缓存</el-button>
			</el-form-item>
		</el-form>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%">
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column prop="keyCode" label="语言码" width="110" />
			<el-table-column prop="langKey" label="语言键值" min-width="200" show-overflow-tooltip />
			<el-table-column prop="langContext" label="内容" min-width="180" show-overflow-tooltip />
			<el-table-column label="创建时间" width="180">
				<template #default="{ row }">{{ formatDate(row.createDate) }}</template>
			</el-table-column>
			<el-table-column label="更新时间" width="180">
				<template #default="{ row }">{{ formatDate(row.updateDate) }}</template>
			</el-table-column>
			<el-table-column label="操作" width="120" fixed="right">
				<template #default="{ row }">
					<el-button link type="primary" @click="openEdit(row)">编辑</el-button>
					<el-button link type="danger" @click="deleteRow(row)">删除</el-button>
				</template>
			</el-table-column>
		</el-table>

		<div class="pagination-bar">
			<el-pagination
				:current-page="pageIndex"
				:page-size="pageSize"
				:page-sizes="[10, 20, 50]"
				:total="total"
				layout="total, sizes, prev, pager, next, jumper"
				@current-change="handlePageChange"
				@size-change="handleSizeChange"
			/>
		</div>

		<el-dialog
			v-model="dialogVisible"
			:title="dialogMode === 'add' ? '录入语言对照' : '修改语言对照'"
			width="480px"
			:close-on-click-modal="false"
			destroy-on-close
		>
			<el-form ref="formRef" :model="form" label-width="90px">
				<el-form-item
					label="语言码"
					prop="keyCode"
					:rules="[{ required: true, message: '请选择或输入语言码', trigger: 'change' }]"
				>
					<el-select v-model="form.keyCode" filterable allow-create default-first-option style="width: 100%">
						<el-option v-for="code in keyCodeOptions" :key="code" :label="code" :value="code" />
					</el-select>
				</el-form-item>
				<el-form-item
					label="语言键值"
					prop="langKey"
					:rules="[{ required: true, message: '请输入语言键值', trigger: 'blur' }]"
				>
					<el-input v-model="form.langKey" placeholder="如：common.login" />
				</el-form-item>
				<el-form-item
					label="内容"
					prop="langContext"
					:rules="[{ required: true, message: '请输入语言内容', trigger: 'blur' }]"
				>
					<el-input v-model="form.langContext" type="textarea" :rows="3" placeholder="如：登录" />
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="dialogVisible = false">取消</el-button>
				<el-button type="primary" :loading="dialogSaving" @click="submit">确定</el-button>
			</template>
		</el-dialog>
	</section>
</template>

<style lang="scss" scoped>
.multi-lang-root {
	width: 100%;

	.filter-bar {
		margin-top: 12px;
	}

	.pagination-bar {
		display: flex;
		justify-content: flex-end;
		margin-top: 16px;
	}
}
</style>
