import axios, { type AxiosError } from "axios";

import { useUserStore } from "stores/user";

/**
 * 问数 Agent 独立 axios 实例
 *
 * 与全局 http.js 的区别：
 * - 不复用全局实例，避免受 http.defaults.timeout = 10000 的影响（多步 ReAct 问数容易超过 10s）；
 * - 不挂全局响应拦截器，只解析 Agent 的 {code, message, data} 外壳；
 * - 请求依旧经网关转发（baseURL = VITE_API_URL = /api，开发态由 vite 代理到 127.0.0.1:10001）。
 */
export const agentHttp = axios.create({
	baseURL: import.meta.env.VITE_API_URL,
	timeout: 60000,
});

agentHttp.interceptors.request.use((config) => {
	const store = useUserStore();
	const token = store.getToken;
	if (token) {
		config.headers["Authorization"] = `Bearer ${token}`;
	}
	return config;
});

/** 单次工具调用审计信息（与后端 toolCalls 字段一一对应） */
export interface AgentToolCall {
	tool: string;
	params?: Record<string, unknown>;
	status: string;
	rowCount?: number;
	durationMs?: number;
	endpoint?: string;
	errorCode?: number | string | null;
	retryable?: boolean;
	attempt?: number;
	resultDigest?: string;
}

/** /agent/query 成功响应体 */
export interface AgentQueryData {
	answer: string;
	sessionId: string;
	traceId: string;
	persisted: boolean;
	toolCalls: AgentToolCall[];
	createdAt: string;
}

/** 后端统一响应外壳 {code, message, data} */
export interface AgentEnvelope<T> {
	code: number;
	message: string;
	data: T | null;
}

/** 成功码，与 JsonVO / http.js 的 SUCCESS 常量保持一致 */
export const AGENT_SUCCESS_CODE = 10000;

export class AgentError extends Error {
	code?: number;

	constructor(message: string, code?: number) {
		super(message);
		this.name = "AgentError";
		this.code = code;
	}
}

/**
 * 解析后端外壳：code=10000 才算成功，其余一律抛 AgentError
 */
export function unwrapAgentEnvelope<T>(payload: AgentEnvelope<T> | null | undefined): T {
	if (!payload) {
		throw new AgentError("问数服务未返回内容");
	}
	if (payload.code !== AGENT_SUCCESS_CODE) {
		throw new AgentError(payload.message || "问数失败", payload.code);
	}
	if (!payload.data) {
		throw new AgentError("问数服务未返回数据", payload.code);
	}
	return payload.data;
}

/**
 * 把 axios / 网络异常翻译成可展示的中文错误
 */
export function normalizeAgentError(error: unknown): AgentError {
	if (error instanceof AgentError) {
		return error;
	}
	const axiosError = error as AxiosError<AgentEnvelope<unknown>>;
	if (axiosError?.isAxiosError) {
		if (axiosError.code === "ECONNABORTED" || axiosError.code === "ETIMEDOUT") {
			return new AgentError("问数超时（60 秒），请缩小问题范围后重试");
		}
		if (!axiosError.response) {
			return new AgentError("无法连接问数服务，请检查网络或网关状态");
		}
		const status = axiosError.response.status;
		const body = axiosError.response.data;
		if (status === 401) {
			return new AgentError("登录已失效，请重新登录", 401);
		}
		if (status === 403) {
			return new AgentError("权限不足，无法使用问数助手", 403);
		}
		if (body && typeof body === "object" && body.message) {
			return new AgentError(body.message, body.code);
		}
		return new AgentError(`问数服务返回异常状态 ${status}`, status);
	}
	return new AgentError(error instanceof Error ? error.message : "问数失败");
}

/**
 * 发起一次问数请求
 * @param query 自然语言问题，必填
 * @param sessionId 可选，会话标识（后端仅用于归并 trace，不做多轮记忆）
 */
export async function queryAgent(query: string, sessionId?: string): Promise<AgentQueryData> {
	const body: Record<string, unknown> = { query };
	if (sessionId) {
		body.sessionId = sessionId;
	}
	try {
		const response = await agentHttp.post<AgentEnvelope<AgentQueryData>>("/agent/query", body);
		return unwrapAgentEnvelope(response.data);
	} catch (error) {
		throw normalizeAgentError(error);
	}
}
