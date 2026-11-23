<script lang="ts" setup>
import { ref, reactive, computed, onMounted } from "vue";
import { UserFilled } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
	listCatagoryTree,
	listCatagories,
	addCatagory,
	modifyCatagory,
	removeCatagory,
	listIconNames,
} from "@/apis/system-j3/index";

definePage({
	meta: {
		menuType: "page",
		text: "分类管理",
		icon: UserFilled,
	},
});

interface CategoryNode {
	tnId?: string;
	categoryId?: string;
	parentId?: string | null;
	name?: string;
	iconId?: string;
	haveChildren?: boolean;
	children?: CategoryNode[];
}

interface Row {
	catagoryId?: string;
	iconId?: string;
	code?: string;
	name?: string;
	haveChildren?: boolean;
	parentId?: string | null;
}

const treeLoading = ref(false);
const listLoading = ref(false);
const treeData = ref<CategoryNode[]>([]);
const rows = ref<Row[]>([]);
const selectedNode = ref<CategoryNode | null>(null);

const dialogVisible = ref(false);
const dialogMode = ref<"add" | "edit">("add");
const dialogSaving = ref(false);
const formRef = ref();
const form = reactive({
	id: "",
	name: "",
	parentId: "",
	iconId: "",
});

const iconOptions = ref<{ id: string; label: string }[]>([]);

const currentTitle = computed(() => selectedNode.value?.name || "全部根分类");

const parentIdsInTree = computed(() => {
	const ids = new Set<string>();
	const walk = (nodes: CategoryNode[]) => {
		nodes.forEach(node => {
			if (node.children && node.children.length > 0) {
				ids.add(nodeId(node));
				walk(node.children);
			}
		});
	};
	walk(treeData.value);
	return ids;
});

function hasChildren(row: Row) {
	return parentIdsInTree.value.has(row.catagoryId || "");
}

function errText(err: any, fallback: string) {
	return err?.data?.message || err?.message || err?.response?.data?.message || fallback;
}

function nodeId(node: CategoryNode) {
	return node.tnId || node.categoryId || "";
}

function generateId() {
	if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
		return crypto.randomUUID().replace(/-/g, "");
	}
	return `${Date.now().toString(16)}${Math.random().toString(16).slice(2, 18)}`;
}

function loadTree() {
	treeLoading.value = true;
	listCatagoryTree(
		(data: any) => {
			treeData.value = data ?? [];
			treeLoading.value = false;
			if (selectedNode.value) {
				const selectedId = nodeId(selectedNode.value);
				const findNode = (nodes: CategoryNode[]): CategoryNode | null => {
					for (const node of nodes) {
						if (nodeId(node) === selectedId) return node;
						const found = node.children ? findNode(node.children) : null;
						if (found) return found;
					}
					return null;
				};
				const matched = findNode(treeData.value);
				if (matched) {
					selectedNode.value = matched;
				}
			}
		},
		() => {
			treeLoading.value = false;
			ElMessage.error("分类名称树加载失败");
		},
	);
}

function loadList() {
	listLoading.value = true;
	const query = selectedNode.value ? { catagoryId: nodeId(selectedNode.value) } : {};
	listCatagories(
		query,
		(data: any) => {
			rows.value = data ?? [];
			listLoading.value = false;
		},
		() => {
			listLoading.value = false;
			ElMessage.error("分类列表加载失败");
		},
	);
}

function refreshAll() {
	loadTree();
	loadList();
}

function handleTreeClick(node: CategoryNode) {
	selectedNode.value = node;
	loadList();
}

function backToRoot() {
	selectedNode.value = null;
	loadList();
}

async function loadIconOptions() {
	try {
		const res: any = await listIconNames(1);
		const list: any[] = res?.data ?? [];
		iconOptions.value = list.map(item => ({
			id: item.id,
			label: `${item.name ?? ""}（${item.iconclas ?? ""}）`,
		}));
	} catch {
		iconOptions.value = [];
	}
}

function openAdd() {
	dialogMode.value = "add";
	form.id = "";
	form.name = "";
	form.parentId = selectedNode.value ? nodeId(selectedNode.value) : "";
	form.iconId = "";
	dialogVisible.value = true;
	loadIconOptions();
}

function openEdit(row: Row) {
	dialogMode.value = "edit";
	form.id = row.catagoryId ?? "";
	form.name = row.name ?? "";
	form.parentId = row.parentId ?? "";
	form.iconId = row.iconId ?? "";
	dialogVisible.value = true;
	loadIconOptions();
}

async function submit() {
	const valid = await formRef.value?.validate().catch(() => false);
	if (!valid) return;
	dialogSaving.value = true;
	try {
		const payload: Record<string, any> = {
			name: form.name,
			parentId: form.parentId || null,
			iconId: form.iconId || null,
		};
		if (dialogMode.value === "add") {
			payload.id = generateId();
			await addCatagory(payload);
		} else {
			payload.id = form.id;
			await modifyCatagory(payload);
		}
		ElMessage.success(dialogMode.value === "add" ? "分类录入成功" : "分类修改成功");
		dialogVisible.value = false;
		refreshAll();
	} catch (err: any) {
		ElMessage.error(errText(err, "操作失败"));
	} finally {
		dialogSaving.value = false;
	}
}

async function deleteRow(row: Row) {
	try {
		await ElMessageBox.confirm(
			`确定删除分类「${row.name ?? ""}」吗？若存在子分类，删除后子分类将失去上级。`,
			"提示",
			{
				type: "warning",
				confirmButtonText: "确定",
				cancelButtonText: "取消",
			},
		);
	} catch {
		return;
	}
	try {
		await removeCatagory(row.catagoryId as string);
		ElMessage.success("删除成功");
		refreshAll();
	} catch (err: any) {
		ElMessage.error(errText(err, "删除失败"));
	}
}

onMounted(() => {
	loadTree();
	loadList();
});
</script>

<template>
	<section class="catagory-root">
		<h2>分类管理</h2>

		<el-row :gutter="16">
			<el-col :span="8">
				<div class="panel">
					<div class="panel-header">
						<span>分类名称树</span>
						<div class="panel-tools">
							<el-button size="small" @click="backToRoot">根分类</el-button>
							<el-button size="small" type="primary" @click="refreshAll">刷新</el-button>
						</div>
					</div>
					<el-tree
						v-loading="treeLoading"
						:data="treeData"
						node-key="tnId"
						:props="{ label: 'name', children: 'children' }"
						default-expand-all
						highlight-current
						empty-text="暂无分类"
						@node-click="handleTreeClick"
					/>
				</div>
			</el-col>

			<el-col :span="16">
				<div class="panel">
					<div class="panel-header">
						<span>分类列表（{{ currentTitle }}）</span>
						<div class="panel-tools">
							<el-button size="small" type="success" @click="openAdd">新增分类</el-button>
						</div>
					</div>

					<el-table v-loading="listLoading" :data="rows" border stripe style="width: 100%">
						<el-table-column type="index" label="序号" width="60" />
						<el-table-column prop="name" label="分类名称" min-width="140" show-overflow-tooltip />
						<el-table-column prop="code" label="分类编码" min-width="160" show-overflow-tooltip />
						<el-table-column prop="catagoryId" label="分类ID" min-width="200" show-overflow-tooltip />
						<el-table-column label="是否有子分类" width="120" align="center">
							<template #default="{ row }">{{ hasChildren(row) ? "是" : "否" }}</template>
						</el-table-column>
						<el-table-column label="操作" width="150" fixed="right">
							<template #default="{ row }">
								<el-button link type="primary" @click="openEdit(row)">编辑</el-button>
								<el-button link type="danger" @click="deleteRow(row)">删除</el-button>
							</template>
						</el-table-column>
					</el-table>
				</div>
			</el-col>
		</el-row>

		<el-dialog
			v-model="dialogVisible"
			:title="dialogMode === 'add' ? '新增分类' : '修改分类'"
			width="480px"
			:close-on-click-modal="false"
			destroy-on-close
		>
			<el-form ref="formRef" :model="form" label-width="90px">
				<el-form-item
					label="分类名称"
					prop="name"
					:rules="[{ required: true, message: '请输入分类名称', trigger: 'blur' }]"
				>
					<el-input v-model="form.name" placeholder="如：家清" />
				</el-form-item>
				<el-form-item label="上级分类" prop="parentId">
					<el-tree-select
						v-model="form.parentId"
						:data="treeData"
						node-key="tnId"
						:props="{ label: 'name', children: 'children' }"
						check-strictly
						clearable
						placeholder="不选则为根分类"
						style="width: 100%"
					/>
				</el-form-item>
				<el-form-item label="图标" prop="iconId">
					<el-select
						v-model="form.iconId"
						filterable
						allow-create
						default-first-option
						clearable
						placeholder="可选，选择或输入图标ID"
						style="width: 100%"
					>
						<el-option v-for="item in iconOptions" :key="item.id" :label="item.label" :value="item.id" />
					</el-select>
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
.catagory-root {
	width: 100%;

	.panel {
		border: 1px solid #ebeef5;
		border-radius: 6px;
		padding: 12px;
		margin-top: 12px;
		min-height: 420px;
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
}
</style>
