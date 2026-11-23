<script lang="ts" setup>
import { ref } from "vue";
import { ElMessage } from "element-plus";
import { ChatDotRound, Close, Promotion } from "@element-plus/icons-vue";

import { queryAgent, type AgentToolCall } from "apis/agent";

/** 悬浮窗是否展开 */
const visible = ref(false);
/** 请求进行中 */
const loading = ref(false);
/** 用户输入（失败时保留，不清空） */
const question = ref("");
/** 最近一次答案 */
const answer = ref("");
/** 最近一次工具调用审计 */
const toolCalls = ref<AgentToolCall[]>([]);
/** 折叠面板展开项 */
const activePanels = ref<string[]>([]);
/** 会话标识：仅用于后端归并 trace，不承载多轮上下文 */
const sessionId = ref("");
/** 最近一次 traceId */
const traceId = ref("");
/** 最近一次是否已持久化 */
const persisted = ref(false);

function toolTagType(call: AgentToolCall): "success" | "info" | "warning" | "danger" {
	if (call.status === "success") return "success";
	if (call.status === "empty") return "info";
	if (call.status === "error") return "danger";
	return "warning";
}

function toolStatusText(call: AgentToolCall): string {
	switch (call.status) {
		case "success":
			return "成功";
		case "empty":
			return "无数据";
		case "error":
			return "失败";
		default:
			return call.status;
	}
}

/**
 * 发起问数
 * 失败时只提示错误，保留用户输入，便于直接修改重试
 */
async function submit() {
	const query = question.value.trim();
	if (!query) {
		ElMessage.warning("请先输入要问的问题");
		return;
	}
	loading.value = true;
	try {
		const data = await queryAgent(query, sessionId.value || undefined);
		answer.value = data.answer ?? "";
		toolCalls.value = data.toolCalls ?? [];
		sessionId.value = data.sessionId ?? sessionId.value;
		traceId.value = data.traceId ?? "";
		persisted.value = Boolean(data.persisted);
		activePanels.value = toolCalls.value.length > 0 ? ["tools"] : [];
	} catch (error) {
		ElMessage.error(error instanceof Error ? error.message : "问数失败，请稍后重试");
	} finally {
		loading.value = false;
	}
}
</script>

<template>
	<div class="ai-assistant">
		<el-button
			v-if="!visible"
			class="ai-assistant__trigger"
			type="primary"
			circle
			:icon="ChatDotRound"
			title="问数助手"
			@click="visible = true"
		/>
		<el-card v-else class="ai-assistant__panel" shadow="always">
			<template #header>
				<div class="ai-assistant__header">
					<span class="ai-assistant__title">问数助手</span>
					<el-button link :icon="Close" @click="visible = false" />
				</div>
			</template>

			<div class="ai-assistant__body">
				<el-empty v-if="!answer && !loading" description="用一句话描述你要查的问题" :image-size="60" />
				<el-skeleton v-else-if="loading && !answer" :rows="3" animated />
				<div v-if="answer" class="ai-assistant__answer">{{ answer }}</div>

				<el-collapse v-if="toolCalls.length > 0" v-model="activePanels">
					<el-collapse-item name="tools" :title="`工具调用（${toolCalls.length}）`">
						<div v-for="(call, index) in toolCalls" :key="index" class="ai-assistant__tool">
							<div class="ai-assistant__tool-head">
								<el-tag :type="toolTagType(call)" size="small">{{ call.tool }}</el-tag>
								<span class="ai-assistant__tool-status">{{ toolStatusText(call) }}</span>
								<span v-if="call.rowCount !== undefined">{{ call.rowCount }} 行</span>
								<span v-if="call.durationMs !== undefined">{{ call.durationMs }} ms</span>
							</div>
							<div class="ai-assistant__tool-meta">
								<span v-if="call.endpoint">{{ call.endpoint }}</span>
								<span v-if="call.errorCode !== undefined && call.errorCode !== null">错误码 {{ call.errorCode }}</span>
								<span v-if="call.retryable !== undefined">可重试 {{ call.retryable }}</span>
								<span v-if="call.attempt !== undefined">尝试 {{ call.attempt }} 次</span>
								<span v-if="call.resultDigest">{{ call.resultDigest }}</span>
							</div>
						</div>
					</el-collapse-item>
				</el-collapse>

				<div v-if="traceId" class="ai-assistant__trace">
					traceId {{ traceId }} · {{ persisted ? "已持久化" : "仅内存" }}
				</div>
			</div>

			<div class="ai-assistant__input">
				<el-input
					v-model="question"
					type="textarea"
					:rows="3"
					maxlength="500"
					show-word-limit
					placeholder="例如：查询 A01 库位的库存情况"
					@keydown.ctrl.enter="submit"
				/>
				<div class="ai-assistant__actions">
					<el-button type="primary" :icon="Promotion" :loading="loading" @click="submit">提问</el-button>
				</div>
			</div>
		</el-card>
	</div>
</template>

<style scoped>
.ai-assistant__trigger {
	position: fixed;
	right: 24px;
	bottom: 96px;
	z-index: 2000;
	width: 48px;
	height: 48px;
	font-size: 22px;
}

.ai-assistant__panel {
	position: fixed;
	right: 24px;
	bottom: 96px;
	z-index: 2000;
	width: 420px;
	max-width: calc(100vw - 48px);
}

.ai-assistant__header {
	display: flex;
	align-items: center;
	justify-content: space-between;
}

.ai-assistant__title {
	font-weight: 600;
}

.ai-assistant__body {
	max-height: 360px;
	overflow-y: auto;
}

.ai-assistant__answer {
	margin-bottom: 12px;
	line-height: 1.7;
	white-space: pre-wrap;
	word-break: break-word;
}

.ai-assistant__tool {
	padding: 6px 0;
	border-bottom: 1px dashed var(--el-border-color-lighter);
}

.ai-assistant__tool:last-child {
	border-bottom: none;
}

.ai-assistant__tool-head {
	display: flex;
	gap: 8px;
	align-items: center;
	font-size: 13px;
}

.ai-assistant__tool-status {
	color: var(--el-text-color-regular);
}

.ai-assistant__tool-meta {
	display: flex;
	flex-direction: column;
	margin-top: 4px;
	color: var(--el-text-color-secondary);
	font-size: 12px;
	word-break: break-all;
}

.ai-assistant__trace {
	margin-top: 10px;
	color: var(--el-text-color-secondary);
	font-size: 12px;
}

.ai-assistant__input {
	margin-top: 12px;
}

.ai-assistant__actions {
	display: flex;
	justify-content: flex-end;
	margin-top: 8px;
}
</style>
