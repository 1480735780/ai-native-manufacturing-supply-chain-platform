<script lang="ts" setup>
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
	listTypeGroups,
	addTypeGroup,
	modifyTypeGroup,
	removeTypeGroup,
	listTypes,
	addType,
	modifyType,
	removeType,
} from "@/apis/system-j3/index";

definePage({
	meta: {
		menuType: "page",
		text: "数据字典",
		icon: "IconSetting",
	},
});

interface TypeGroupRow {
	id?: string;
	typegroupName?: string;
	typegroupCode?: string;
}

interface TypeRow {
	id?: string;
	typeCode?: string;
	typeName?: string;
	createDate?: string;
}

const groupLoading = ref(false);
const typeLoading = ref(false);

const groups = ref<TypeGroupRow[]>([]);
const groupTotal = ref(0);
const groupPageIndex = ref(1);
const groupPageSize = ref(10);
const groupKeyword = ref("");

const currentGroup = ref<TypeGroupRow | null>(null);
const types = ref<TypeRow[]>([]);
const typeTotal = ref(0);
const typePageIndex = ref(1);
const typePageSize = ref(10);

const groupDialogVisible = ref(false);
const groupDialogMode = ref<"add" | "edit">("add");
const groupSaving = ref(false);
const groupFormRef = ref();
const groupForm = reactive({
	id: "",
	typegroupName: "",
	typegroupCode: "",
});

const typeDialogVisible = ref(false);
const typeDialogMode = ref<"add" | "edit">("add");
const typeSaving = ref(false);
const typeFormRef = ref();
const typeForm = reactive({
	id: "",
	typeName: "",
	typeCode: "",
	typegroupid: "",
});

function errText(err: any, fallback: string) {
	return err?.data?.message || err?.message || err?.response?.data?.message || fallback;
}

function formatDateTime(value?: string) {
	if (!value) return "";
	return String(value).replace("T", " ").replace(/\.\d+$/, "");
}

function loadGroups(selectFirst = false) {
	groupLoading.value = true;
	listTypeGroups(
		{
			pageIndex: groupPageIndex.value,
			pageSize: groupPageSize.value,
			typegroupname: groupKeyword.value,
		},
		(data: any) => {
			groups.value = data.rows ?? [];
			groupTotal.value = data.total ?? 0;
			groupLoading.value = false;
			if (currentGroup.value?.id) {
				const still = groups.value.find(item => item.id === currentGroup.value?.id);
				if (still) {
					currentGroup.value = still;
				} else if (groups.value.length > 0) {
					selectGroup(groups.value[0]);
				} else {
					currentGroup.value = null;
					types.value = [];
					typeTotal.value = 0;
				}
			} else if (selectFirst && groups.value.length > 0) {
				selectGroup(groups.value[0]);
			}
		},
		() => {
			groupLoading.value = false;
			ElMessage.error("字典分类加载失败");
		},
	);
}

function loadTypes() {
	if (!currentGroup.value?.id) {
		types.value = [];
		typeTotal.value = 0;
		return;
	}
	typeLoading.value = true;
	listTypes(
		{
			pageIndex: typePageIndex.value,
			pageSize: typePageSize.value,
			typegroupid: currentGroup.value.id,
		},
		(data: any) => {
			types.value = data.rows ?? [];
			typeTotal.value = data.total ?? 0;
			typeLoading.value = false;
		},
		() => {
			typeLoading.value = false;
			ElMessage.error("字典类型加载失败");
		},
	);
}

function selectGroup(row: TypeGroupRow) {
	currentGroup.value = row;
	typePageIndex.value = 1;
	loadTypes();
}

function handleGroupSearch() {
	groupPageIndex.value = 1;
	loadGroups();
}

function handleGroupPageChange(page: number) {
	groupPageIndex.value = page;
	loadGroups();
}

function handleGroupSizeChange(size: number) {
	groupPageSize.value = size;
	groupPageIndex.value = 1;
	loadGroups();
}

function handleTypePageChange(page: number) {
	typePageIndex.value = page;
	loadTypes();
}

function handleTypeSizeChange(size: number) {
	typePageSize.value = size;
	typePageIndex.value = 1;
	loadTypes();
}

function openGroupAdd() {
	groupDialogMode.value = "add";
	groupForm.id = "";
	groupForm.typegroupName = "";
	groupForm.typegroupCode = "";
	groupDialogVisible.value = true;
}

function openGroupEdit(row: TypeGroupRow) {
	groupDialogMode.value = "edit";
	groupForm.id = row.id ?? "";
	groupForm.typegroupName = row.typegroupName ?? "";
	groupForm.typegroupCode = row.typegroupCode ?? "";
	groupDialogVisible.value = true;
}

async function submitGroup() {
	const valid = await groupFormRef.value?.validate().catch(() => false);
	if (!valid) return;
	groupSaving.value = true;
	try {
		if (groupDialogMode.value === "add") {
			await addTypeGroup({
				typegroupName: groupForm.typegroupName,
				typegroupCode: groupForm.typegroupCode,
			});
		} else {
			await modifyTypeGroup({
				id: groupForm.id,
				typegroupName: groupForm.typegroupName,
				typegroupCode: groupForm.typegroupCode,
			});
		}
		ElMessage.success(groupDialogMode.value === "add" ? "字典分类录入成功" : "字典分类修改成功");
		groupDialogVisible.value = false;
		loadGroups();
	} catch (err: any) {
		ElMessage.error(errText(err, "操作失败"));
	} finally {
		groupSaving.value = false;
	}
}

async function deleteGroup(row: TypeGroupRow) {
	try {
		await ElMessageBox.confirm(`确定删除字典分类「${row.typegroupName ?? ""}」吗？`, "提示", {
			type: "warning",
			confirmButtonText: "确定",
			cancelButtonText: "取消",
		});
	} catch {
		return;
	}
	try {
		await removeTypeGroup(row.id as string);
		ElMessage.success("删除成功");
		if (currentGroup.value?.id === row.id) {
			currentGroup.value = null;
			types.value = [];
			typeTotal.value = 0;
		}
		loadGroups();
	} catch (err: any) {
		ElMessage.error(errText(err, "删除失败"));
	}
}

function openTypeAdd() {
	if (!currentGroup.value?.id) {
		ElMessage.warning("请先选择字典分类");
		return;
	}
	typeDialogMode.value = "add";
	typeForm.id = "";
	typeForm.typeName = "";
	typeForm.typeCode = "";
	typeForm.typegroupid = currentGroup.value.id;
	typeDialogVisible.value = true;
}

function openTypeEdit(row: TypeRow) {
	typeDialogMode.value = "edit";
	typeForm.id = row.id ?? "";
	typeForm.typeName = row.typeName ?? "";
	typeForm.typeCode = row.typeCode ?? "";
	typeForm.typegroupid = currentGroup.value?.id ?? "";
	typeDialogVisible.value = true;
}

async function submitType() {
	const valid = await typeFormRef.value?.validate().catch(() => false);
	if (!valid) return;
	typeSaving.value = true;
	try {
		if (typeDialogMode.value === "add") {
			await addType({
				typeName: typeForm.typeName,
				typeCode: typeForm.typeCode,
				typegroupid: typeForm.typegroupid,
			});
		} else {
			await modifyType({
				id: typeForm.id,
				typeName: typeForm.typeName,
				typeCode: typeForm.typeCode,
				typegroupid: typeForm.typegroupid,
			});
		}
		ElMessage.success(typeDialogMode.value === "add" ? "字典类型录入成功" : "字典类型修改成功");
		typeDialogVisible.value = false;
		loadTypes();
	} catch (err: any) {
		ElMessage.error(errText(err, "操作失败"));
	} finally {
		typeSaving.value = false;
	}
}

async function deleteType(row: TypeRow) {
	try {
		await ElMessageBox.confirm(`确定删除字典类型「${row.typeName ?? ""}」吗？`, "提示", {
			type: "warning",
			confirmButtonText: "确定",
			cancelButtonText: "取消",
		});
	} catch {
		return;
	}
	try {
		await removeType(row.id as string);
		ElMessage.success("删除成功");
		loadTypes();
	} catch (err: any) {
		ElMessage.error(errText(err, "删除失败"));
	}
}

onMounted(() => {
	loadGroups(true);
});
</script>

<template>
	<section class="dictionary-root">
		<h2>数据字典</h2>

		<el-row :gutter="16">
			<el-col :span="10">
				<div class="panel">
					<div class="panel-header">
						<span>字典分类</span>
						<div class="panel-tools">
							<el-input
								v-model="groupKeyword"
								placeholder="字典名称"
								clearable
								style="width: 140px"
								@clear="handleGroupSearch"
								@keyup.enter="handleGroupSearch"
							/>
							<el-button type="primary" @click="handleGroupSearch">查询</el-button>
							<el-button type="success" @click="openGroupAdd">录入</el-button>
						</div>
					</div>

					<el-table
						v-loading="groupLoading"
						:data="groups"
						border
						stripe
						highlight-current-row
						style="width: 100%"
						@row-click="selectGroup"
					>
						<el-table-column type="index" label="序号" width="60" />
						<el-table-column prop="typegroupName" label="字典名称" min-width="120" show-overflow-tooltip />
						<el-table-column prop="typegroupCode" label="字典Code" min-width="120" show-overflow-tooltip />
						<el-table-column label="操作" width="120" fixed="right">
							<template #default="{ row }">
								<el-button link type="primary" @click.stop="openGroupEdit(row)">编辑</el-button>
								<el-button link type="danger" @click.stop="deleteGroup(row)">删除</el-button>
							</template>
						</el-table-column>
					</el-table>

					<div class="pagination-bar">
						<el-pagination
							:current-page="groupPageIndex"
							:page-size="groupPageSize"
							:page-sizes="[10, 20, 50]"
							:total="groupTotal"
							layout="total, sizes, prev, pager, next"
							@current-change="handleGroupPageChange"
							@size-change="handleGroupSizeChange"
						/>
					</div>
				</div>
			</el-col>

			<el-col :span="14">
				<div class="panel">
					<div class="panel-header">
						<span>
							字典类型
							<template v-if="currentGroup">
								（{{ currentGroup.typegroupName }} / {{ currentGroup.typegroupCode }}）
							</template>
						</span>
						<div class="panel-tools">
							<el-button type="success" @click="openTypeAdd">录入</el-button>
						</div>
					</div>

					<el-table v-loading="typeLoading" :data="types" border stripe style="width: 100%">
						<el-table-column type="index" label="序号" width="60" />
						<el-table-column prop="typeCode" label="类型编码" min-width="120" show-overflow-tooltip />
						<el-table-column prop="typeName" label="类型名称" min-width="140" show-overflow-tooltip />
						<el-table-column label="创建时间" width="170">
							<template #default="{ row }">{{ formatDateTime(row.createDate) }}</template>
						</el-table-column>
						<el-table-column label="操作" width="120" fixed="right">
							<template #default="{ row }">
								<el-button link type="primary" @click="openTypeEdit(row)">编辑</el-button>
								<el-button link type="danger" @click="deleteType(row)">删除</el-button>
							</template>
						</el-table-column>
					</el-table>

					<div class="pagination-bar">
						<el-pagination
							:current-page="typePageIndex"
							:page-size="typePageSize"
							:page-sizes="[10, 20, 50]"
							:total="typeTotal"
							layout="total, sizes, prev, pager, next"
							@current-change="handleTypePageChange"
							@size-change="handleTypeSizeChange"
						/>
					</div>
				</div>
			</el-col>
		</el-row>

		<el-dialog
			v-model="groupDialogVisible"
			:title="groupDialogMode === 'add' ? '录入字典分类' : '修改字典分类'"
			width="420px"
			:close-on-click-modal="false"
			destroy-on-close
		>
			<el-form ref="groupFormRef" :model="groupForm" label-width="90px">
				<el-form-item
					label="字典名称"
					prop="typegroupName"
					:rules="[{ required: true, message: '请输入字典名称', trigger: 'blur' }]"
				>
					<el-input v-model="groupForm.typegroupName" placeholder="如：送货方式" />
				</el-form-item>
				<el-form-item
					label="字典Code"
					prop="typegroupCode"
					:rules="[{ required: true, message: '请输入字典Code', trigger: 'blur' }]"
				>
					<el-input v-model="groupForm.typegroupCode" placeholder="如：tms_thfs" />
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="groupDialogVisible = false">取消</el-button>
				<el-button type="primary" :loading="groupSaving" @click="submitGroup">确定</el-button>
			</template>
		</el-dialog>

		<el-dialog
			v-model="typeDialogVisible"
			:title="typeDialogMode === 'add' ? '录入字典类型' : '修改字典类型'"
			width="420px"
			:close-on-click-modal="false"
			destroy-on-close
		>
			<el-form ref="typeFormRef" :model="typeForm" label-width="90px">
				<el-form-item label="所属分类">
					<el-input :model-value="currentGroup?.typegroupName" disabled />
				</el-form-item>
				<el-form-item
					label="类型名称"
					prop="typeName"
					:rules="[{ required: true, message: '请输入类型名称', trigger: 'blur' }]"
				>
					<el-input v-model="typeForm.typeName" placeholder="如：良品" />
				</el-form-item>
				<el-form-item
					label="类型编码"
					prop="typeCode"
					:rules="[{ required: true, message: '请输入类型编码', trigger: 'blur' }]"
				>
					<el-input v-model="typeForm.typeCode" placeholder="如：01" />
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="typeDialogVisible = false">取消</el-button>
				<el-button type="primary" :loading="typeSaving" @click="submitType">确定</el-button>
			</template>
		</el-dialog>
	</section>
</template>

<style lang="scss" scoped>
.dictionary-root {
	width: 100%;

	.panel {
		border: 1px solid #ebeef5;
		border-radius: 6px;
		padding: 12px;
		margin-top: 12px;
	}

	.panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		min-height: 32px;
		margin-bottom: 8px;
		font-weight: 600;
	}

	.panel-tools {
		display: flex;
		gap: 8px;
		font-weight: normal;
	}

	.pagination-bar {
		display: flex;
		justify-content: flex-end;
		margin-top: 12px;
	}
}
</style>
