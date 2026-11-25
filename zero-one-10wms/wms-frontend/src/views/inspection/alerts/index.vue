<script lang="ts" setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
	ackAlert,
	claimAlert,
	fallbackNote,
	fetchAlertDetail,
	fetchAlertPage,
	fetchScanStatus,
	fetchScanSummaries,
	findAlertSummary,
	ignoreAlert,
	isScanSettled,
	mergePolledAlerts,
	resolveAlert,
	severityCountsText,
	summarySourceLabel,
	type AlertPageCursor,
	type InspectionAlert,
	type InspectionAlertDetail,
	type ScanSummaryItem,
} from "@/apis/inspection/alerts";
import { normalizeAgentError } from "@/apis/agent";
import { usePermission } from "@/composables/use-permission";

definePage({
	meta: {
		menuType: "page",
		text: "异常巡检",
		icon: "IconSetting",
	},
});

/** 轮询间隔与 since 重叠窗口（秒） */
const POLL_INTERVAL_MS = 30_000;
const PAGE_SIZE = 50;

const STATE_OPTIONS = [
	{ label: "待处理", value: "open" },
	{ label: "已确认", value: "acknowledged" },
	{ label: "已解决", value: "resolved" },
	{ label: "已忽略", value: "ignored" },
];
const SEVERITY_OPTIONS = ["P0", "P1", "P2"];

const filters = ref<{ state: string; severity: string; warehouseId: string }>({
	state: "",
	severity: "",
	warehouseId: "",
});

const rows = ref<InspectionAlert[]>([]);
const loading = ref(false);
const loadingMore = ref(false);
const nextCursor = ref<AlertPageCursor | null>(null);
/** 最近一轮轮询里是否存在 partial 元告警（扫描不完整横幅） */
const partialScan = ref(false);
const drawerVisible = ref(false);
const detailLoading = ref(false);
let detailRequestSeq = 0;
const detail = ref<InspectionAlertDetail | null>(null);

/**
 * 巡检摘要（阶段6 后端能力，阶段7 接入抽屉）：按告警最近一次命中的 scanId 取该次巡检的聚合摘要。
 * 摘要在扫描收尾时才写入，所以扫描未结束时要等；越权（无告警查看权限）与没有摘要分开提示。
 */
const SUMMARY_POLL_MS = 10_000;
const SUMMARY_POLL_MAX = 30;
type SummaryState = "idle" | "loading" | "ready" | "pending" | "none" | "forbidden" | "error";
const summaryState = ref<SummaryState>("idle");
const summary = ref<ScanSummaryItem | null>(null);
const summaryLoading = ref(false);
let summaryTimer: ReturnType<typeof setTimeout> | null = null;
let summaryPolls = 0;
/** 切换告警后，迟到的旧响应不再覆盖当前抽屉 */
let summaryRequestSeq = 0;

const summaryFallbackNote = computed(() => (summary.value ? fallbackNote(summary.value) : ""));
const summarySeverityText = computed(() => severityCountsText(summary.value?.severityCounts));

const { readOnly, roles } = usePermission();
/** 操作按钮权限：只读角色（KH/cw/cs）隐藏 ack/claim/resolve/ignore */
const canOperate = computed(() => !readOnly.value);

let pollTimer: ReturnType<typeof setInterval> | null = null;
/** 记录上次查询 partial 的 scanId，避免同一巡检在轮询中反复请求 */
let lastPartialScanId: string | null = null;
/**
 * 刷新 partial 横幅：看最新一次巡检自身的 partial，而不是"列表里是否有 SCAN-PARTIAL 元告警"
 * （元告警在人工关闭前会一直在，否则后续完整巡检也会误显示 partial）。
 *
 * 横幅是全局信号，必须独立于当前筛选：单独用一条不带筛选的 pageSize=1 查询取最新告警，
 * 其 scanId 即最新一次巡检（列表按 lastSeenAt 倒序）。任一步失败都沿用上一次状态，不打断列表。
 */
async function refreshPartialBanner(): Promise<void> {
	try {
		const latest = await fetchAlertPage({ pageSize: 1 });
		const scanId = latest.items[0]?.scanId;
		if (!scanId) {
			partialScan.value = false;
			lastPartialScanId = null;
			return;
		}
		if (scanId === lastPartialScanId) return;
		const scan = await fetchScanStatus(scanId);
		partialScan.value = scan.partial;
		lastPartialScanId = scanId;
	} catch {
		// 横幅查询失败不影响列表渲染
	}
}
/** 按当前筛选条件取第一页（用于首屏与轮询） */
async function loadFirstPage(isPoll = false) {
	if (!isPoll) loading.value = true;
	try {
		const page = await fetchAlertPage({
			state: filters.value.state || undefined,
			severity: filters.value.severity || undefined,
			warehouseId: filters.value.warehouseId || undefined,
			pageSize: PAGE_SIZE,
		});
		// partial 横幅独立于筛选条件，单独取最新巡检状态（见 refreshPartialBanner）
		await refreshPartialBanner();
		if (isPoll) {
			// since 重叠：新轮询结果在前，已加载的旧告警按 alertId 去重后保留
			rows.value = mergePolledAlerts(rows.value, page.items);
		} else {
			rows.value = page.items;
		}
		nextCursor.value = page.nextCursor;
	} catch (error) {
		const err = normalizeAgentError(error);
		ElMessage.error(err.message || "告警加载失败");
	} finally {
		loading.value = false;
	}
}

async function loadMore() {
	if (!nextCursor.value || loadingMore.value) return;
	loadingMore.value = true;
	try {
		const page = await fetchAlertPage({
			state: filters.value.state || undefined,
			severity: filters.value.severity || undefined,
			warehouseId: filters.value.warehouseId || undefined,
			cursor: nextCursor.value,
			pageSize: PAGE_SIZE,
		});
		rows.value = mergePolledAlerts(rows.value, page.items);
		nextCursor.value = page.nextCursor;
	} catch (error) {
		ElMessage.error(normalizeAgentError(error).message || "加载更多失败");
	} finally {
		loadingMore.value = false;
	}
}

function handleSearch() {
	nextCursor.value = null;
	loadFirstPage();
}

function handleReset() {
	filters.value = { state: "", severity: "", warehouseId: "" };
	handleSearch();
}

function startPolling() {
	stopPolling();
	pollTimer = setInterval(() => {
		// 抽屉打开或正在翻页时跳过本轮，避免与用户操作竞争
		if (drawerVisible.value || loadingMore.value) return;
		loadFirstPage(true);
	}, POLL_INTERVAL_MS);
}

function stopPolling() {
	if (pollTimer) {
		clearInterval(pollTimer);
		pollTimer = null;
	}
}

function clearSummaryPoll() {
	if (summaryTimer) {
		clearTimeout(summaryTimer);
		summaryTimer = null;
	}
}

function scheduleSummaryPoll() {
	clearSummaryPoll();
	if (summaryState.value !== "pending" || !drawerVisible.value || summaryPolls >= SUMMARY_POLL_MAX) return;
	summaryTimer = setTimeout(() => {
		summaryTimer = null;
		loadSummary();
	}, SUMMARY_POLL_MS);
}

/** 取当前告警所属那组告警的摘要；`manual` 为用户点刷新，失败时弹提示 */
async function loadSummary(manual = false) {
	const scanId = detail.value?.scanId;
	if (!scanId) {
		summaryState.value = "none";
		summary.value = null;
		return;
	}
	const seq = ++summaryRequestSeq;
	summaryLoading.value = true;
	summaryPolls += 1;
	try {
		const result = await fetchScanSummaries(scanId);
		if (seq !== summaryRequestSeq) return;
		const item = findAlertSummary(result.items, detail.value ?? { ruleId: "", warehouseId: "", dimension: {} });
		summary.value = item;
		if (!isScanSettled(result.status)) {
			summaryState.value = "pending";
		} else {
			summaryState.value = item ? "ready" : "none";
		}
	} catch (error) {
		if (seq !== summaryRequestSeq) return;
		const err = normalizeAgentError(error);
		summary.value = null;
		summaryState.value = err.code === 9997 ? "forbidden" : "error";
		if (manual) ElMessage.error(err.message || "摘要加载失败");
	} finally {
		if (seq === summaryRequestSeq) {
			summaryLoading.value = false;
			scheduleSummaryPoll();
		}
	}
}

async function openDetail(row: InspectionAlert) {
	drawerVisible.value = true;
	detailLoading.value = true;
	detail.value = null;
	clearSummaryPoll();
	summary.value = null;
	summaryPolls = 0;
	summaryState.value = "idle";
	// 关闭后立刻打开另一条时，上一次尚未返回的请求不能覆盖当前告警
	const seq = ++detailRequestSeq;
	try {
		const data = await fetchAlertDetail(row.alertId);
		if (seq !== detailRequestSeq) return;
		detail.value = data;
		await loadSummary();
	} catch (error) {
		if (seq === detailRequestSeq) {
			ElMessage.error(normalizeAgentError(error).message || "详情加载失败");
			drawerVisible.value = false;
		}
	} finally {
		if (seq === detailRequestSeq) detailLoading.value = false;
	}
}

/** 抽屉关闭后停止摘要轮询 */
watch(drawerVisible, (open) => {
	if (!open) clearSummaryPoll();
});

function replaceRow(updated: InspectionAlert) {
	const index = rows.value.findIndex((a) => a.alertId === updated.alertId);
	if (index >= 0) {
		rows.value.splice(index, 1, updated);
	} else {
		rows.value.unshift(updated);
	}
	if (detail.value && detail.value.alertId === updated.alertId) {
		detail.value = { ...detail.value, ...updated };
	}
}

async function runAction(action: () => Promise<InspectionAlert>, successText: string) {
	try {
		const updated = await action();
		replaceRow(updated);
		ElMessage.success(successText);
	} catch (error) {
		ElMessage.error(normalizeAgentError(error).message || "操作失败");
		throw error;
	}
}

async function handleClaim(row: InspectionAlert) {
	await runAction(() => claimAlert(row.alertId), "认领成功");
}

async function handleAck(row: InspectionAlert) {
	await runAction(() => ackAlert(row.alertId), "已确认");
}

async function handleResolve(row: InspectionAlert) {
	let reason: string;
	try {
		const { value } = await ElMessageBox.prompt("请输入解决原因（必填）", "解决告警", {
			confirmButtonText: "确认解决",
			cancelButtonText: "取消",
			inputValidator: (val) => (val && val.trim() ? true : "原因不能为空"),
		});
		reason = value.trim();
	} catch {
		return;
	}
	await runAction(() => resolveAlert(row.alertId, reason), "已解决");
}

async function handleIgnore(row: InspectionAlert) {
	let reason: string;
	try {
		const { value } = await ElMessageBox.prompt(
			"请输入忽略原因（必填，默认忽略 7 天）",
			"忽略告警",
			{
				confirmButtonText: "确认忽略",
				cancelButtonText: "取消",
				inputValidator: (val) => (val && val.trim() ? true : "原因不能为空"),
			},
		);
		reason = value.trim();
	} catch {
		return;
	}
	await runAction(() => ignoreAlert(row.alertId, reason), "已忽略");
}

function severityTagType(severity: string): "danger" | "warning" | "info" {
	if (severity === "P0") return "danger";
	if (severity === "P1") return "warning";
	return "info";
}

function stateLabel(state: string): string {
	return STATE_OPTIONS.find((o) => o.value === state)?.label ?? state;
}

/** ISO 时间 → 本地可读时间；空值显示 "-"（用于详情抽屉中的关闭/确认/忽略时间） */
function fmtTime(iso: string | null | undefined): string {
	if (!iso) return "-";
	const d = new Date(iso);
	return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

function isActionable(row: InspectionAlert): boolean {
	return row.state === "open" || row.state === "acknowledged";
}

onMounted(() => {
	loadFirstPage();
	startPolling();
});

onBeforeUnmount(() => {
	stopPolling();
	clearSummaryPoll();
});
</script>

<template>
	<section class="inspection-alerts-root">
		<el-alert
			v-if="partialScan"
			title="最近一次巡检数据不完整（partial）：部分数据源超时或分页异常，告警可能缺失，请稍后重试"
			type="warning"
			:closable="false"
			show-icon
			class="partial-banner"
		/>

		<el-form :inline="true" class="filter-bar">
			<el-form-item label="状态">
				<el-select v-model="filters.state" clearable placeholder="全部" style="width: 140px">
					<el-option v-for="o in STATE_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
				</el-select>
			</el-form-item>
			<el-form-item label="级别">
				<el-select v-model="filters.severity" clearable placeholder="全部" style="width: 120px">
					<el-option v-for="s in SEVERITY_OPTIONS" :key="s" :label="s" :value="s" />
				</el-select>
			</el-form-item>
			<el-form-item label="仓库">
				<el-input v-model="filters.warehouseId" placeholder="仓库编码" clearable style="width: 140px" />
			</el-form-item>
			<el-form-item>
				<el-button type="primary" @click="handleSearch">查询</el-button>
				<el-button @click="handleReset">重置</el-button>
			</el-form-item>
			<el-form-item>
				<span class="role-tip">当前角色：{{ roles.length ? roles.join(" / ") : "未知" }}</span>
			</el-form-item>
		</el-form>

		<el-table v-loading="loading" :data="rows" border stripe style="width: 100%">
			<el-table-column prop="alertId" label="ID" width="80" />
			<el-table-column label="级别" width="80">
				<template #default="{ row }">
					<el-tag :type="severityTagType(row.severity)" size="small">{{ row.severity }}</el-tag>
				</template>
			</el-table-column>
			<el-table-column prop="ruleId" label="规则" width="160" show-overflow-tooltip />
			<el-table-column prop="title" label="告警" min-width="220" show-overflow-tooltip />
			<el-table-column prop="objectId" label="对象" width="160" show-overflow-tooltip />
			<el-table-column prop="warehouseId" label="仓库" width="90" />
			<el-table-column label="状态" width="100">
				<template #default="{ row }">
					<el-tag :type="row.state === 'open' ? 'danger' : 'info'" size="small">
						{{ stateLabel(row.state) }}
					</el-tag>
				</template>
			</el-table-column>
			<el-table-column prop="occurrenceCount" label="次数" width="70" align="right" />
			<el-table-column label="认领人" width="110">
				<template #default="{ row }">{{ row.assignee || "-" }}</template>
			</el-table-column>
			<el-table-column prop="lastSeenAt" label="最近发现" width="180" />
			<el-table-column label="操作" width="300" fixed="right">
				<template #default="{ row }">
					<el-button link type="primary" @click="openDetail(row)">详情</el-button>
					<template v-if="canOperate && isActionable(row)">
						<el-button v-if="!row.assignee" link type="primary" @click="handleClaim(row)">认领</el-button>
						<el-button v-if="row.state === 'open'" link type="primary" @click="handleAck(row)">确认</el-button>
						<el-button link type="success" @click="handleResolve(row)">解决</el-button>
						<el-button link type="warning" @click="handleIgnore(row)">忽略</el-button>
					</template>
				</template>
			</el-table-column>
		</el-table>

		<div class="load-more-bar">
			<el-button v-if="nextCursor" :loading="loadingMore" @click="loadMore">加载更多</el-button>
			<span v-else class="tip">已加载全部</span>
		</div>

		<!-- el-drawer 要等关闭动画结束才把 v-model 置回 false；动画期间再点「详情」会因值未变而不重新打开。
		     所以在 @close（动画开始）就同步置为 false，关闭过程中再次打开会被视为真正的重新打开。
		     不用 destroy-on-close：openDetail 会同步清空 detail，重新打开时不会闪现上一条。 -->
		<el-drawer v-model="drawerVisible" title="告警详情" size="45%" @close="drawerVisible = false">
			<div v-loading="detailLoading" class="detail-body">
				<template v-if="detail">
					<el-descriptions :column="1" border size="small">
						<el-descriptions-item label="告警">{{ detail.title }}</el-descriptions-item>
						<el-descriptions-item label="规则">{{ detail.ruleId }}（{{ detail.ruleVersion ?? "-" }}）</el-descriptions-item>
						<el-descriptions-item label="级别">{{ detail.severity }}</el-descriptions-item>
						<el-descriptions-item label="对象">{{ detail.objectType }} / {{ detail.objectId }}</el-descriptions-item>
						<el-descriptions-item label="状态">{{ stateLabel(detail.state) }}</el-descriptions-item>
						<el-descriptions-item label="认领人">{{ detail.assignee || "-" }}</el-descriptions-item>
						<el-descriptions-item v-if="detail.acknowledgedBy" label="确认人">{{ detail.acknowledgedBy }}（{{ fmtTime(detail.acknowledgedAt) }}）</el-descriptions-item>
						<el-descriptions-item v-if="detail.resolvedReason" label="解决原因">{{ detail.resolvedReason }}</el-descriptions-item>
						<el-descriptions-item v-if="detail.state === 'resolved' && detail.resolvedAt" label="解决时间">{{ fmtTime(detail.resolvedAt) }}</el-descriptions-item>
						<el-descriptions-item v-if="detail.state === 'ignored'" label="忽略截止">{{ fmtTime(detail.ignoredUntil) }}</el-descriptions-item>
						<el-descriptions-item label="trace">{{ detail.traceId || "-" }}</el-descriptions-item>
					</el-descriptions>

					<!-- 巡检摘要：纯文本渲染（不走 v-html）；建议动作只展示，由人确认 -->
					<h4 class="summary-heading">
						巡检摘要
						<el-button
							link
							type="primary"
							size="small"
							:loading="summaryLoading"
							:disabled="summaryState === 'forbidden'"
							@click="loadSummary(true)"
						>
							刷新
						</el-button>
					</h4>
					<div v-if="summary && summaryState === 'ready'" class="summary-card" data-testid="scan-summary">
						<div class="summary-meta">
							<el-tag :type="summary.summarySource === 'llm' ? 'success' : 'info'" size="small">
								{{ summarySourceLabel(summary.summarySource) }}
							</el-tag>
							<span v-if="summary.summarySource === 'llm' && summary.model" class="tip">模型：{{ summary.model }}</span>
							<span v-if="summary.archived" class="tip">已归档</span>
							<span class="tip">
								同组 {{ summary.objectCount }} 个对象<template v-if="summarySeverityText">（{{ summarySeverityText }}）</template>
							</span>
						</div>
						<p v-if="summaryFallbackNote" class="summary-note">{{ summaryFallbackNote }}</p>
						<p class="summary-text">{{ summary.summary }}</p>
						<div v-if="summary.suggestedActions?.length" class="summary-actions">
							<span class="actions-label">建议动作（需人工确认，不会自动执行）</span>
							<ul>
								<li v-for="(action, index) in summary.suggestedActions" :key="`${action.code}-${index}`">
									{{ action.text }}<span class="tip">（{{ action.code }}）</span>
								</li>
							</ul>
						</div>
					</div>
					<p v-else-if="summaryState === 'pending'" class="tip" data-testid="scan-summary-pending">
						巡检尚未结束，摘要会在扫描完成后生成，可稍后点「刷新」
					</p>
					<p v-else-if="summaryState === 'none'" class="tip">该次巡检没有生成这组告警的摘要</p>
					<p v-else-if="summaryState === 'forbidden'" class="tip">无权查看该次巡检的摘要</p>
					<p v-else-if="summaryState === 'error'" class="tip">摘要加载失败，可点「刷新」重试</p>

					<h4>证据</h4>
					<pre class="json-block">{{ JSON.stringify(detail.evidence ?? {}, null, 2) }}</pre>

					<h4>规则参数</h4>
					<pre class="json-block">{{ JSON.stringify(detail.ruleParams ?? {}, null, 2) }}</pre>

					<h4>事件流水</h4>
					<el-timeline v-if="detail.events?.length">
						<el-timeline-item
							v-for="ev in detail.events"
							:key="ev.eventId"
							:timestamp="ev.createdAt"
							placement="top"
						>
							{{ ev.eventType || ev.toState }} · {{ ev.actorId || "system" }}
							<span v-if="ev.reason" class="tip">（{{ ev.reason }}）</span>
						</el-timeline-item>
					</el-timeline>
					<p v-else class="tip">暂无事件</p>
				</template>
			</div>
		</el-drawer>
	</section>
</template>

<style lang="scss" scoped>
.inspection-alerts-root {
	width: 100%;

	.partial-banner {
		margin-bottom: 12px;
	}

	.filter-bar {
		margin-top: 12px;
	}

	.role-tip {
		color: #909399;
		font-size: 13px;
	}

	.load-more-bar {
		display: flex;
		justify-content: center;
		margin-top: 16px;
	}

	.tip {
		color: #909399;
		font-size: 13px;
	}

	.detail-body {
		min-height: 200px;

		h4 {
			margin: 16px 0 8px;
		}

		.summary-heading {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.summary-card {
		padding: 12px;
		border: 1px solid #ebeef5;
		border-radius: 4px;
		background: #fff;

		.summary-meta {
			display: flex;
			flex-wrap: wrap;
			align-items: center;
			gap: 8px;
			margin-bottom: 8px;
		}

		.summary-note {
			margin: 0 0 8px;
			color: #e6a23c;
			font-size: 13px;
		}

		.summary-text {
			margin: 0;
			font-size: 14px;
			line-height: 1.7;
			white-space: pre-line;
			word-break: break-word;
		}

		.summary-actions {
			margin-top: 10px;
			font-size: 13px;

			.actions-label {
				color: #606266;
			}

			ul {
				margin: 6px 0 0;
				padding-left: 18px;
			}
		}
	}

	.json-block {
			padding: 8px 12px;
			background: #f5f7fa;
			border-radius: 4px;
			font-size: 12px;
			line-height: 1.6;
			overflow: auto;
			max-height: 240px;
		}
	}
}
</style>
