<script lang="ts" setup>
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { UploadFile, UploadFiles } from "element-plus";
import {
	listIcons,
	listIconNames,
	getIconDetail,
	addIcon,
	modifyIcon,
	removeIcon,
} from "@/apis/system-j3/index";

definePage({
	meta: {
		menuType: "page",
		text: "系统图标",
		icon: "IconSetting",
	},
});

interface IconRow {
	name?: string;
	iconclas?: string;
	type?: number;
	url?: string;
	extend?: string;
}

const loading = ref(false);
const rows = ref<IconRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);
const keyword = ref("");

const dialogVisible = ref(false);
const dialogMode = ref<"add" | "edit">("add");
const dialogSaving = ref(false);
const formRef = ref();
const form = reactive({
	id: "",
	name: "",
	type: 1 as number,
	iconclas: "",
});
const iconUrl = ref("");
const uploadFileList = ref<UploadFiles>([]);
const selectedFile = ref<File | null>(null);

const typeOptions = [
	{ label: "系统图标", value: 1 },
	{ label: "菜单图标", value: 2 },
	{ label: "桌面图标", value: 3 },
];

function errText(err: any, fallback: string) {
	return err?.data?.message || err?.message || err?.response?.data?.message || fallback;
}

function typeText(value?: number) {
	const option = typeOptions.find(item => item.value === value);
	return option ? option.label : value ?? "";
}

function loadData() {
	loading.value = true;
	listIcons(
		{
			pageIndex: pageIndex.value,
			pageSize: pageSize.value,
			name: keyword.value,
		},
		(data: any) => {
			rows.value = data.records ?? [];
			total.value = data.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("系统图标数据加载失败");
		},
	);
}

function handleSearch() {
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

/** 列表 DTO 未返回 id，通过图标名称列表反查 id */
async function resolveIconId(row: IconRow) {
	const types = Array.from(new Set([row.type, 1, 2, 3].filter(item => item !== undefined && item !== null)));
	for (const type of types) {
		try {
			const res: any = await listIconNames(type);
			const list: any[] = res?.data ?? [];
			const exact = list.find(item => item.name === row.name && item.iconclas === row.iconclas);
			if (exact) return exact.id as string;
			const byName = list.filter(item => item.name === row.name);
			if (byName.length === 1) return byName[0].id as string;
		} catch {
			// 忽略单个类型的查询失败，继续尝试
		}
	}
	return "";
}

function resetUpload() {
	selectedFile.value = null;
	uploadFileList.value = [];
}

function handleFileChange(file: UploadFile) {
	selectedFile.value = file.raw ?? null;
}

function handleFileRemove() {
	selectedFile.value = null;
	uploadFileList.value = [];
}

function openAdd() {
	dialogMode.value = "add";
	form.id = "";
	form.name = "";
	form.type = 1;
	form.iconclas = "";
	iconUrl.value = "";
	resetUpload();
	dialogVisible.value = true;
}

async function openEdit(row: IconRow) {
	const id = await resolveIconId(row);
	if (!id) {
		ElMessage.error("未能获取该图标的ID，无法编辑");
		return;
	}
	dialogMode.value = "edit";
	form.id = id;
	form.name = row.name ?? "";
	form.type = row.type ?? 1;
	form.iconclas = row.iconclas ?? "";
	iconUrl.value = row.url ?? "";
	resetUpload();
	dialogVisible.value = true;
	try {
		const res: any = await getIconDetail(id);
		const detail = res?.data ?? {};
		form.name = detail.name ?? form.name;
		form.type = detail.type ?? form.type;
		form.iconclas = detail.iconclas ?? form.iconclas;
	} catch {
		// 详情接口异常时保留列表数据回显
	}
}

async function submit() {
	const valid = await formRef.value?.validate().catch(() => false);
	if (!valid) return;
	if (!selectedFile.value) {
		ElMessage.warning(dialogMode.value === "add" ? "请选择图标文件" : "修改图标需重新选择图标文件");
		return;
	}
	dialogSaving.value = true;
	try {
		const payload: Record<string, any> = {
			name: form.name,
			type: form.type,
			iconclas: form.iconclas,
			file: selectedFile.value,
		};
		if (dialogMode.value === "edit") {
			payload.id = form.id;
			await modifyIcon(payload);
		} else {
			await addIcon(payload);
		}
		ElMessage.success(dialogMode.value === "add" ? "图标录入成功" : "图标修改成功");
		dialogVisible.value = false;
		loadData();
	} catch (err: any) {
		ElMessage.error(errText(err, "操作失败"));
	} finally {
		dialogSaving.value = false;
	}
}

async function deleteRow(row: IconRow) {
	const id = await resolveIconId(row);
	if (!id) {
		ElMessage.error("未能获取该图标的ID，无法删除");
		return;
	}
	try {
		await ElMessageBox.confirm(`确定删除图标「${row.name ?? ""}」吗？`, "提示", {
			type: "warning",
			confirmButtonText: "确定",
			cancelButtonText: "取消",
		});
	} catch {
		return;
	}
	try {
		await removeIcon(id);
		ElMessage.success("删除成功");
		loadData();
	} catch (err: any) {
		ElMessage.error(errText(err, "删除失败"));
	}
}

onMounted(() => {
	loadData();
});
</script>

<template>
	<section class="system-icon-root">
		<h2>系统图标</h2>

		<div class="tool-bar">
			<el-input
				v-model="keyword"
				placeholder="图标名称"
				clearable
				style="width: 200px"
				@clear="handleSearch"
				@keyup.enter="handleSearch"
			/>
			<el-button type="primary" @click="handleSearch">查询</el-button>
			<el-button type="success" @click="openAdd">录入</el-button>
			<span class="tip">图标文件由 FastDFS 存储，缩略图加载失败时显示占位符</span>
		</div>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%">
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column label="预览" width="90" align="center">
				<template #default="{ row }">
					<el-image :src="row.url" fit="contain" style="width: 28px; height: 28px">
						<template #error>
							<span class="no-image">—</span>
						</template>
					</el-image>
				</template>
			</el-table-column>
			<el-table-column prop="name" label="图标名称" min-width="150" show-overflow-tooltip />
			<el-table-column prop="iconclas" label="图标样式" min-width="180" show-overflow-tooltip />
			<el-table-column label="图标类型" width="120">
				<template #default="{ row }">{{ typeText(row.type) }}</template>
			</el-table-column>
			<el-table-column prop="extend" label="后缀" width="100" />
			<el-table-column label="操作" width="140" fixed="right">
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
			:title="dialogMode === 'add' ? '录入系统图标' : '修改系统图标'"
			width="460px"
			:close-on-click-modal="false"
			destroy-on-close
		>
			<el-form ref="formRef" :model="form" label-width="90px">
				<el-form-item
					label="图标名称"
					prop="name"
					:rules="[{ required: true, message: '请输入图标名称', trigger: 'blur' }]"
				>
					<el-input v-model="form.name" placeholder="如：默认" />
				</el-form-item>
				<el-form-item label="图标类型" prop="type">
					<el-select v-model="form.type" style="width: 100%">
						<el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
					</el-select>
				</el-form-item>
				<el-form-item label="图标样式" prop="iconclas">
					<el-input v-model="form.iconclas" placeholder="如：default" />
				</el-form-item>
				<el-form-item label="图标文件" required>
					<el-upload
						v-model:file-list="uploadFileList"
						:auto-upload="false"
						:limit="1"
						accept="image/*"
						:on-change="handleFileChange"
						:on-remove="handleFileRemove"
						:on-exceed="() => ElMessage.warning('只能选择一个图标文件')"
					>
						<el-button type="primary">选择文件</el-button>
						<template #tip>
							<div class="el-upload__tip">
								{{ dialogMode === "edit" ? "修改图标必须重新选择图标文件" : "请选择 png / jpg 等图片文件" }}
							</div>
						</template>
					</el-upload>
				</el-form-item>
				<el-form-item v-if="iconUrl" label="当前图标">
					<el-image :src="iconUrl" fit="contain" style="width: 40px; height: 40px">
						<template #error>
							<span class="no-image">—</span>
						</template>
					</el-image>
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
.system-icon-root {
	width: 100%;

	.tool-bar {
		display: flex;
		align-items: center;
		gap: 12px;
		margin: 12px 0;
	}

	.tip {
		color: #909399;
		font-size: 13px;
	}

	.no-image {
		color: #c0c4cc;
		font-size: 16px;
	}

	.pagination-bar {
		display: flex;
		justify-content: flex-end;
		margin-top: 16px;
	}
}
</style>
