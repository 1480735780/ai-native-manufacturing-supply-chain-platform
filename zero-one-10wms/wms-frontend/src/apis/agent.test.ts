import { describe, expect, it } from "vitest";

import { AgentError, normalizeAgentError, unwrapAgentEnvelope } from "./agent";

describe("问数接口外壳解析", () => {
	it("code=10000 时返回 data", () => {
		const data = unwrapAgentEnvelope<{ answer: string }>({
			code: 10000,
			message: "ok",
			data: { answer: "库存 12 条" },
		});
		expect(data.answer).toBe("库存 12 条");
	});

	it("非 10000 抛 AgentError 并带上 code", () => {
		expect(() =>
			unwrapAgentEnvelope({
				code: 9995,
				message: "[pageIndex]页码最小值为1",
				data: null,
			}),
		).toThrowError(AgentError);
		try {
			unwrapAgentEnvelope({ code: 9995, message: "参数错误", data: null });
		} catch (error) {
			expect((error as AgentError).code).toBe(9995);
			expect((error as AgentError).message).toBe("参数错误");
		}
	});

	it("外壳为空时报错", () => {
		expect(() => unwrapAgentEnvelope(null)).toThrowError("问数服务未返回内容");
		expect(() => unwrapAgentEnvelope({ code: 10000, message: "ok", data: null })).toThrowError(
			"问数服务未返回数据",
		);
	});
});

describe("问数错误归一化", () => {
	it("已是 AgentError 时原样返回", () => {
		const origin = new AgentError("缺少 Bearer token", 401);
		expect(normalizeAgentError(origin)).toBe(origin);
	});

	it("超时提示可读文案", () => {
		const error = normalizeAgentError({ isAxiosError: true, code: "ECONNABORTED" });
		expect(error.message).toContain("超时");
	});

	it("401 提示重新登录", () => {
		const error = normalizeAgentError({ isAxiosError: true, response: { status: 401, data: null } });
		expect(error.code).toBe(401);
		expect(error.message).toContain("重新登录");
	});

	it("优先展示后端 message", () => {
		const error = normalizeAgentError({
			isAxiosError: true,
			response: { status: 200, data: { code: 9999, message: "查询数据不存在", data: null } },
		});
		expect(error.message).toBe("查询数据不存在");
	});

	it("无响应体时给出状态码", () => {
		const error = normalizeAgentError({ isAxiosError: true, response: { status: 500, data: null } });
		expect(error.message).toContain("500");
	});

	it("非 axios 异常也归一化", () => {
		expect(normalizeAgentError(new Error("boom")).message).toBe("boom");
	});
});
