<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { getMessageCenterAPI } from "@/apis/message-middle";

definePage({
	meta: {
		menuType: "page",
		text: "消息中心",
		icon: "IconMessage",
	},
});

interface MessageRow {
	id?: string;
	esType?: string;
	esTitle?: string;
	esSender?: string;
	esReceiver?: string;
	esContent?: string;
	createDate?: string;
	esSendtime?: string;
	esStatus?: string;
	remark?: string;
}

const loading = ref(false);
const rows = ref<MessageRow[]>([]);
const total = ref(0);
const pageIndex = ref(1);
const pageSize = ref(10);

// MessageQuery 要求 esType、esStatus 必填，默认查系统提醒 + 发送成功
const query = ref({
	esType: "3",
	esStatus: "1",
	esTitle: "",
});

function typeText(value?: string) {
	if (value === "1") return "短信提醒";
	if (value === "2") return "邮件提醒";
	if (value === "3") return "系统提醒";
	return value ?? "";
}

function statusText(value?: string) {
	if (value === "1") return "发送成功";
	if (value === "2") return "发送失败";
	if (value === "3") return "未发送";
	return value ?? "";
}

function formatDateTime(value?: string) {
	if (!value) return "";
	return String(value).replace("T", " ");
}

function loadData() {
	loading.value = true;
	getMessageCenterAPI(
		{
			pageIndex: pageIndex.value,
			pageSize: pageSize.value,
			...query.value,
		},
		(data: any) => {
			rows.value = data?.rows ?? [];
			total.value = data?.total ?? 0;
			loading.value = false;
		},
		() => {
			loading.value = false;
			ElMessage.error("消息中心数据加载失败");
		},
	);
}

function handleSearch() {
	pageIndex.value = 1;
	loadData();
}

function handleReset() {
	query.value = { esType: "3", esStatus: "1", esTitle: "" };
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

onMounted(() => {
	loadData();
});
</script>

<template>
	<section class="message-center-root">
		<h2>消息中心</h2>

		<el-form :inline="true" class="filter-bar">
			<el-form-item label="消息类型">
				<el-select v-model="query.esType" style="width: 130px">
					<el-option label="短信提醒" value="1" />
					<el-option label="邮件提醒" value="2" />
					<el-option label="系统提醒" value="3" />
				</el-select>
			</el-form-item>
			<el-form-item label="发送状态">
				<el-select v-model="query.esStatus" style="width: 130px">
					<el-option label="发送成功" value="1" />
					<el-option label="发送失败" value="2" />
					<el-option label="未发送" value="3" />
				</el-select>
			</el-form-item>
			<el-form-item label="消息标题">
				<el-input v-model="query.esTitle" placeholder="消息标题" clearable style="width: 180px" />
			</el-form-item>
			<el-form-item>
				<el-button type="primary" @click="handleSearch">查询</el-button>
				<el-button @click="handleReset">重置</el-button>
			</el-form-item>
		</el-form>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%">
			<el-table-column type="index" label="序号" width="60" />
			<el-table-column label="消息类型" width="100">
				<template #default="{ row }">{{ typeText(row.esType) }}</template>
			</el-table-column>
			<el-table-column prop="esTitle" label="消息标题" min-width="140" show-overflow-tooltip />
			<el-table-column prop="esSender" label="发送人" width="100" />
			<el-table-column prop="esReceiver" label="接收人" width="100" />
			<el-table-column prop="esContent" label="内容" min-width="320" show-overflow-tooltip />
			<el-table-column label="创建日期" width="170">
				<template #default="{ row }">{{ formatDateTime(row.createDate) }}</template>
			</el-table-column>
			<el-table-column label="发送时间" width="170">
				<template #default="{ row }">{{ formatDateTime(row.esSendtime) }}</template>
			</el-table-column>
			<el-table-column label="发送状态" width="100">
				<template #default="{ row }">
					<el-tag v-if="row.esStatus === '1'" type="success">{{ statusText(row.esStatus) }}</el-tag>
					<el-tag v-else-if="row.esStatus === '2'" type="danger">{{ statusText(row.esStatus) }}</el-tag>
					<el-tag v-else type="info">{{ statusText(row.esStatus) }}</el-tag>
				</template>
			</el-table-column>
			<el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip />
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
	</section>
</template>

<style lang="scss" scoped>
.message-center-root {
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
