import { agentHttp, normalizeAgentError, unwrapAgentEnvelope } from "@/apis/agent";

// 注意：不要在此文件 re-export agent.ts 的符号（如 AgentError / normalizeAgentError）。
// unplugin-auto-import 以 src/** 为 dirs 扫描全部导出，重复导出会让它把符号注入回
// agent.ts 自身，导致 "Identifier has already been declared" 构建错误。
// 使用方一律从 "@/apis/agent" 直接导入。

/**
 * 异常巡检告警 API（阶段2 最小前端）
 *
 * 复用问数 Agent 的独立 axios 实例（Bearer 注入 + 网关 baseURL），只解析
 * {code, message, data} 外壳。后端约定：
 * - GET 越权 → HTTP 200 + body.code=9997（由 unwrap 抛 AgentError）；
 * - POST 越权/冲突 → HTTP 403/404/409（由 axios reject，经 normalize 翻译）。
 */

export type AlertState = "open" | "acknowledged" | "resolved" | "ignored";
export type AlertSeverity = "P0" | "P1" | "P2";

/** 告警列表行（与后端 _row_to_alert 字段一致） */
export interface InspectionAlert {
	alertId: number;
	fingerprint: string;
	ruleId: string;
	severity: AlertSeverity | string;
	objectType: string;
	objectId: string;
	dimension: Record<string, unknown>;
	title: string;
	state: AlertState | string;
	assignee?: string | null;
	warehouseId: string;
	occurrenceCount: number;
	firstSeenAt?: string | null;
	lastSeenAt?: string | null;
	scanId?: string | null;
	traceId?: string | null;
	ruleDegraded?: boolean;
	firstSeverity?: AlertSeverity | string | null;
	acknowledgedBy?: string | null;
	acknowledgedAt?: string | null;
	assigneeUserId?: string | null;
	claimedAt?: string | null;
	routedTo?: string | null;
	/** 关闭信息（resolve/ignore 时写入；与事件流中的 reason 一致，供抽屉直接展示） */
	resolvedAt?: string | null;
	resolvedReason?: string | null;
	/** ignore 的截止时间，过期后同 fingerprint 的复发会重新建告警 */
	ignoredUntil?: string | null;
}

/** 告警事件流水行 */
export interface AlertEvent {
	eventId: number;
	alertId: number;
	actorType?: string;
	actorId?: string;
	fromState?: string | null;
	toState?: string | null;
	reason?: string | null;
	traceId?: string | null;
	createdAt?: string | null;
	eventType?: string | null;
	fromSeverity?: string | null;
	toSeverity?: string | null;
}

/** 告警详情：告警主体 + 证据 + 规则参数 + 事件流水 + 触发扫描 */
export interface InspectionAlertDetail extends InspectionAlert {
	ruleVersion?: string | null;
	evidence: Record<string, unknown>;
	ruleParams: Record<string, unknown>;
	events: AlertEvent[];
	scan: Record<string, unknown> | null;
}

/** 游标：成对使用 (lastSeenAt, lastAlertId) 才生效 */
export interface AlertPageCursor {
	lastSeenAt?: string | null;
	lastAlertId?: number | null;
}

export interface AlertPageQuery {
	state?: string;
	severity?: string;
	warehouseId?: string;
	ruleId?: string;
	cursor?: AlertPageCursor | null;
	pageSize?: number;
}

export interface AlertPage {
	items: InspectionAlert[];
	nextCursor: AlertPageCursor | null;
	pageSize: number;
}

/** 站内通知（按接收人隔离，已读状态仅本人可改） */
export interface AgentNotification {
	notificationId: number;
	alertId: number;
	channel: string;
	recipient: string;
	recipientUserId?: string | null;
	status: string;
	payloadDigest?: string | null;
	providerMessageId?: string | null;
	createdAt?: string | null;
	sentAt?: string | null;
	readAt?: string | null;
}

async function getJson<T>(url: string, params?: Record<string, unknown>): Promise<T> {
	const response = await agentHttp.get<AgentEnvelopeShim<T>>(url, { params });
	return unwrapAgentEnvelope(response.data);
}

/** 与 agent.ts 的 AgentEnvelope 结构一致（避免循环类型引用） */
interface AgentEnvelopeShim<T> {
	code: number;
	message: string;
	data: T | null;
}

export function stripEmpty(params: Record<string, unknown>): Record<string, unknown> {
	const out: Record<string, unknown> = {};
	for (const [key, value] of Object.entries(params)) {
		if (value === undefined || value === null || value === "") {
			continue;
		}
		out[key] = value;
	}
	return out;
}

async function postJson<T>(url: string, body?: Record<string, unknown>): Promise<T> {
	const response = await agentHttp.post<AgentEnvelopeShim<T>>(url, body ?? {});
	return unwrapAgentEnvelope(response.data);
}

export async function fetchAlertPage(query: AlertPageQuery): Promise<AlertPage> {
	const params = stripEmpty({
		state: query.state,
		severity: query.severity,
		warehouseId: query.warehouseId,
		ruleId: query.ruleId,
		lastSeenAt: query.cursor?.lastSeenAt,
		lastAlertId: query.cursor?.lastAlertId,
		pageSize: query.pageSize ?? 50,
	});
	return getJson<AlertPage>("/agent/alerts/page", params);
}

export async function fetchAlertDetail(alertId: number): Promise<InspectionAlertDetail> {
	return getJson<InspectionAlertDetail>(`/agent/alerts/${alertId}`);
}

export async function claimAlert(alertId: number): Promise<InspectionAlert> {
	return postJson<InspectionAlert>(`/agent/alerts/${alertId}/claim`);
}

export async function ackAlert(alertId: number): Promise<InspectionAlert> {
	return postJson<InspectionAlert>(`/agent/alerts/${alertId}/ack`);
}

export async function resolveAlert(alertId: number, reason: string): Promise<InspectionAlert> {
	return postJson<InspectionAlert>(`/agent/alerts/${alertId}/resolve`, { reason });
}

export async function ignoreAlert(
	alertId: number,
	reason: string,
	ignoredUntil?: string,
): Promise<InspectionAlert> {
	return postJson<InspectionAlert>(`/agent/alerts/${alertId}/ignore`, { reason, ignoredUntil });
}

/** 触发一次巡检（只入队，执行由后台 worker 异步完成） */
export async function triggerScan(scanTypes: string[]): Promise<{ scanId: string; status: string }> {
	return postJson<{ scanId: string; status: string }>("/agent/scan", {
		scanTypes,
		requestId: generateRequestId(),
	});
}

/** 巡检记录里页面只关心的字段（partial 横幅用） */
export interface ScanStatus {
	scanId: string;
	status: string;
	partial: boolean;
}

/**
 * 查询某次巡检的状态（partial 横幅的数据源）。
 *
 * 横幅不能用"列表里是否存在 SCAN-PARTIAL 元告警"判定：元告警在人工关闭前会一直
 * 存在，导致后续即使巡检完整也持续显示 partial。改为看最新一次巡检自身的 partial。
 */
export async function fetchScanStatus(scanId: string): Promise<ScanStatus> {
	const data = await getJson<Partial<ScanStatus>>(`/agent/scans/${scanId}`);
	return {
		scanId: String(data.scanId ?? scanId),
		status: String(data.status ?? ""),
		partial: Boolean(data.partial),
	};
}

export async function fetchNotifications(unreadOnly = false, limit = 50): Promise<AgentNotification[]> {
	const data = await getJson<{ items: AgentNotification[] }>("/agent/notifications", stripEmpty({
		unreadOnly: unreadOnly ? "true" : "",
		limit,
	}));
	return data.items;
}

export async function markNotificationRead(notificationId: number): Promise<AgentNotification> {
	return postJson<AgentNotification>(`/agent/notifications/${notificationId}/read`);
}

/** 摘要来源：`llm` = 模型写的；`template` = 确定性模板（含模型失败后的降级） */
export type SummarySource = "llm" | "template";

/** LLM 给出的建议动作：只展示，由人确认，前端不执行（ADR-017 / ADR-019） */
export interface SuggestedAction {
	code: string;
	text: string;
}

/** 一次巡检里一组告警（ruleId + 仓库 + 客户）的聚合摘要 */
export interface ScanSummaryItem {
	summaryId?: number | null;
	scanId: string;
	ruleId: string;
	ruleVersion?: string | null;
	warehouse: string;
	customer?: string | null;
	severity: AlertSeverity | string;
	objectCount: number;
	severityCounts?: Record<string, number> | null;
	/** 纯文本（后端已清洗，无 Markdown / HTML） */
	summary: string;
	summarySource: SummarySource | string;
	/** 模板摘要的降级原因；模型摘要与「本就用模板」时为空 */
	fallbackReason?: string | null;
	fallbackDetail?: string | null;
	suggestedActions?: SuggestedAction[] | null;
	model?: string | null;
	/** 该次扫描已归档，摘要来自归档表（ADR-020） */
	archived?: boolean;
}

export interface ScanSummaries {
	scanId: string;
	status: string;
	partial: boolean;
	llmCounts?: Record<string, number>;
	items: ScanSummaryItem[];
}

/**
 * 取某次巡检的聚合摘要（告警详情抽屉用）。
 *
 * 可见性 = 扫描记录可见，或能查看该仓库的告警；越权返回 code=9997（经 unwrap 抛 AgentError）。
 */
export async function fetchScanSummaries(scanId: string): Promise<ScanSummaries> {
	const data = await getJson<Partial<ScanSummaries>>(`/agent/scans/${encodeURIComponent(scanId)}/summaries`);
	return {
		scanId: String(data.scanId ?? scanId),
		status: String(data.status ?? ""),
		partial: Boolean(data.partial),
		llmCounts: data.llmCounts ?? {},
		items: Array.isArray(data.items) ? data.items : [],
	};
}

const TERMINAL_SCAN_STATUSES = new Set(["succeeded", "failed", "cancelled"]);

/** 扫描是否已结束（摘要只在扫描收尾时写入，未结束时取不到） */
export function isScanSettled(status: string | null | undefined): boolean {
	return TERMINAL_SCAN_STATUSES.has(String(status ?? ""));
}

function customerOf(dimension: Record<string, unknown> | null | undefined): string {
	return String((dimension ?? {}).customer ?? "").trim();
}

/**
 * 在一次巡检的摘要里找属于这条告警的那一组（规则 + 仓库 + 客户）。
 * 入库延迟规则按供应商分组、没有客户，客户按空串匹配；找不到返回 null。
 */
export function findAlertSummary(
	items: ScanSummaryItem[],
	alert: Pick<InspectionAlert, "ruleId" | "warehouseId" | "dimension">,
): ScanSummaryItem | null {
	const warehouse = String(alert.warehouseId ?? "").trim();
	const customer = customerOf(alert.dimension);
	return (
		items.find(
			(item) =>
				item.ruleId === alert.ruleId &&
				String(item.warehouse ?? "").trim() === warehouse &&
				String(item.customer ?? "").trim() === customer,
		) ?? null
	);
}

const FALLBACK_REASON_TEXT: Record<string, string> = {
	partial_scan: "本次取数不完整，摘要按模板生成",
	provider_unavailable: "模型不可用，摘要按模板生成",
	call_cap: "超出单次巡检的模型调用上限，摘要按模板生成",
	scan_budget_exhausted: "巡检预算已耗尽，摘要按模板生成",
	timeout: "模型响应超时，摘要按模板生成",
	provider_error: "模型调用失败，摘要按模板生成",
	invalid_json: "模型输出不是合法 JSON，摘要按模板生成",
	invalid_schema: "模型输出不符合约定结构，摘要按模板生成",
	empty_summary: "模型输出为空，摘要按模板生成",
};

/** 来源标签：模型写的还是模板生成的 */
export function summarySourceLabel(source: string | null | undefined): string {
	return source === "llm" ? "模型摘要" : "模板摘要";
}

/** 模板摘要的降级说明；模型摘要或本来就该用模板时返回空串 */
export function fallbackNote(item: Pick<ScanSummaryItem, "summarySource" | "fallbackReason">): string {
	if (item.summarySource === "llm" || !item.fallbackReason) return "";
	return FALLBACK_REASON_TEXT[item.fallbackReason] ?? `模型摘要已降级（${item.fallbackReason}），按模板生成`;
}

/** 「P0 x 个、P1 y 个」这种一行文字；没有级别分布时返回空串 */
export function severityCountsText(counts: Record<string, number> | null | undefined): string {
	const parts = (["P0", "P1", "P2"] as const)
		.filter((key) => (counts?.[key] ?? 0) > 0)
		.map((key) => `${key} ${counts?.[key]} 个`);
	return parts.join("、");
}

function generateRequestId(): string {
	if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
		return crypto.randomUUID();
	}
	return `req-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

/**
 * 30 秒轮询的 since 重叠去重：
 * 新一轮以第一页为基础，把上一轮已加载的 alertId 保留为「已见」集合，
 * 新数据按 alertId 去重后追加到列表尾部。
 */
export function mergePolledAlerts(
	previous: InspectionAlert[],
	incoming: InspectionAlert[],
): InspectionAlert[] {
	const seen = new Set<number>();
	const merged: InspectionAlert[] = [];
	for (const alert of [...incoming, ...previous]) {
		if (seen.has(alert.alertId)) {
			continue;
		}
		seen.add(alert.alertId);
		merged.push(alert);
	}
	return merged;
}
