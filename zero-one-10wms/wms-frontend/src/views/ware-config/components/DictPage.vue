<template>
	<section class="dict-page">
		<div class="tool-bar">
			<div class="query-bar">
				<template v-for="f in queryFields" :key="f.prop">
					<el-input
						v-model="query[f.prop]"
						:placeholder="f.label"
						clearable
						class="query-input"
						@keyup.enter="handleSearch"
					/>
				</template>
				<el-button type="primary" @click="handleSearch">查询</el-button>
				<el-button @click="handleReset">重置</el-button>
			</div>
			<div class="action-bar">
				<el-button v-if="addApi" type="primary" @click="openAdd">录入</el-button>
				<el-button v-if="deleteBatchApi" type="danger" plain @click="handleDeleteBatch">批量删除</el-button>
				<el-button v-if="importApi" type="success" plain @click="openImport">导入</el-button>
				<el-button v-if="exportApi" type="success" plain @click="handleExport">导出</el-button>
			</div>
		</div>

		<el-table
			v-loading="loading"
			:data="rows"
			border
			stripe
			style="width: 100%"
			@selection-change="handleSelectionChange"
		>
			<el-table-column v-if="deleteBatchApi" type="selection" width="45" align="center" fixed />
			<el-table-column type="index" label="序号" width="60" align="center" :index="indexFrom" />
			<el-table-column
				v-for="col in columns"
				:key="col.prop"
				:prop="col.prop"
				:label="col.label"
				:width="col.width"
				align="center"
				show-overflow-tooltip
			/>
			<el-table-column label="操作" width="160" align="center" fixed="right">
				<template #default="{ row }">
					<el-button v-if="updateApi" link type="primary" @click="openEdit(row)">修改</el-button>
					<el-button v-if="deleteApi" link type="danger" @click="handleDelete(row)">删除</el-button>
				</template>
			</el-table-column>
		</el-table>

		<el-pagination
			style="margin-top: 16px; justify-content: flex-end"
			v-model:current-page="pageIndex"
			v-model:page-size="pageSize"
			:page-sizes="[10, 20, 50]"
			layout="total, sizes, prev, pager, next, jumper"
			:total="total"
			@size-change="handleSizeChange"
			@current-change="handlePageChange"
		/>

		<el-dialog
			v-model="dialogVisible"
			:title="dialogMode === 'add' ? `录入${title}` : `修改${title}`"
			width="480px"
			:close-on-click-modal="false"
			draggable
		>
			<el-form ref="formRef" :model="form" label-width="110px">
				<el-form-item
					v-for="f in dialogMode === 'add' ? addFields : editFields"
					:key="f.prop"
					:label="f.label"
					:required="f.prop !== 'id' && dialogMode === 'add'"
				>
					<el-input v-model="form[f.prop]" :disabled="f.prop === 'id' && dialogMode === 'edit'" />
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="dialogVisible = false">取消</el-button>
				<el-button type="primary" :loading="dialogSaving" @click="handleSave">保存</el-button>
			</template>
		</el-dialog>

		<el-dialog v-model="importVisible" title="导入 Excel" width="440px" :close-on-click-modal="false">
			<el-upload
				drag
				action="#"
				:auto-upload="false"
				:limit="1"
				:file-list="importFileList"
				accept=".xlsx,.xls"
				:on-change="handleImportChange"
			>
				<div class="el-upload__text">将 Excel 文件拖到此处，或<em>点击选择</em></div>
			</el-upload>
			<template #footer>
				<el-button @click="importVisible = false">取消</el-button>
				<el-button type="primary" :loading="importSaving" @click="handleImportSubmit">开始导入</el-button>
			</template>
		</el-dialog>
	</section>
</template>

<script lang="ts" setup>
/**
 * 仓库配置通用字典页面：与 use-dict-page 组合使用
 */
import { computed } from "vue";
import { useDictPage, type DictPageOptions } from "../composables/use-dict-page";

const props = defineProps<{
	options: DictPageOptions;
}>();

const {
	rowKey, loading, rows, total, pageIndex, pageSize, selectedRows, selectedIds, query,
	dialogVisible, dialogMode, dialogSaving, formRef, form,
	importVisible, importSaving, importFileList,
	loadData, handleSelectionChange, handlePageChange, handleSizeChange, handleSearch, handleReset,
	openAdd, openEdit, handleSave, handleDelete, handleDeleteBatch,
	openImport, handleImportChange, handleImportSubmit, handleExport,
} = useDictPage(props.options);

const title = computed(() => props.options.title);
const columns = computed(() => props.options.columns);
const queryFields = computed(() => props.options.queryFields);
const addFields = computed(() => props.options.addFields);
const editFields = computed(() => props.options.editFields);
const addApi = computed(() => props.options.addApi);
const updateApi = computed(() => props.options.updateApi);
const deleteApi = computed(() => props.options.deleteApi);
const deleteBatchApi = computed(() => props.options.deleteBatchApi);
const importApi = computed(() => props.options.importApi);
const exportApi = computed(() => props.options.exportApi);

const indexFrom = (index: number) => (pageIndex.value - 1) * pageSize.value + index + 1;

defineExpose({ loadData, selectedIds, rowKey });
</script>

<style lang="scss" scoped>
.dict-page {
	width: 100%;

	.tool-bar {
		display: flex;
		justify-content: space-between;
		align-items: center;
		flex-wrap: wrap;
		gap: 12px;
		margin: 12px 0;

		.query-bar,
		.action-bar {
			display: flex;
			align-items: center;
			gap: 8px;
			flex-wrap: wrap;
		}

		.query-input {
			width: 180px;
		}
	}
}
</style>
