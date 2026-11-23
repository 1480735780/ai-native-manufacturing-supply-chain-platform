import { mount } from "@vue/test-utils";
import ElementPlus from "element-plus";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AiAssistant from "./index.vue";

const queryAgent = vi.fn();

vi.mock("apis/agent", () => ({
	queryAgent: (...args: unknown[]) => queryAgent(...args),
}));

function mountAssistant() {
	return mount(AiAssistant, {
		global: { plugins: [ElementPlus] },
	});
}

describe("问数助手悬浮窗", () => {
	beforeEach(() => {
		queryAgent.mockReset();
	});

	it("默认只显示悬浮按钮，点击后展开面板", async () => {
		const wrapper = mountAssistant();
		expect(wrapper.find(".ai-assistant__panel").exists()).toBe(false);
		await wrapper.find(".ai-assistant__trigger").trigger("click");
		expect(wrapper.find(".ai-assistant__panel").exists()).toBe(true);
	});

	it("空问题不发起请求", async () => {
		const wrapper = mountAssistant();
		await wrapper.find(".ai-assistant__trigger").trigger("click");
		const buttons = wrapper.findAll(".ai-assistant__actions button");
		await buttons[0].trigger("click");
		expect(queryAgent).not.toHaveBeenCalled();
	});

	it("提问成功后展示答案与工具调用", async () => {
		queryAgent.mockResolvedValue({
			answer: "A01 库位库存 12 条",
			sessionId: "s-1",
			traceId: "t-1",
			persisted: false,
			toolCalls: [
				{
					tool: "STOCK-QUERY",
					status: "success",
					rowCount: 12,
					durationMs: 8,
					endpoint: "/stock/inventory-query/query-all",
					resultDigest: "sha256:abc",
				},
			],
			createdAt: "2026-11-23T00:00:00+08:00",
		});
		const wrapper = mountAssistant();
		await wrapper.find(".ai-assistant__trigger").trigger("click");
		const input = wrapper.find(".ai-assistant__input textarea");
		await input.setValue("查询 A01 库位库存");
		const buttons = wrapper.findAll(".ai-assistant__actions button");
		await buttons[0].trigger("click");
		await new Promise((resolve) => setTimeout(resolve, 0));

		expect(queryAgent).toHaveBeenCalledWith("查询 A01 库位库存", undefined);
		expect(wrapper.find(".ai-assistant__answer").text()).toContain("A01 库位库存 12 条");
		expect(wrapper.text()).toContain("STOCK-QUERY");
		expect(wrapper.text()).toContain("t-1");
	});

	it("请求失败时保留用户输入且不展示答案", async () => {
		queryAgent.mockRejectedValue(new Error("问数超时（60 秒），请缩小问题范围后重试"));
		const wrapper = mountAssistant();
		await wrapper.find(".ai-assistant__trigger").trigger("click");
		const input = wrapper.find(".ai-assistant__input textarea");
		await input.setValue("查询 A01 库位库存");
		const buttons = wrapper.findAll(".ai-assistant__actions button");
		await buttons[0].trigger("click");
		await new Promise((resolve) => setTimeout(resolve, 0));

		expect(wrapper.find(".ai-assistant__input textarea").element.value).toBe("查询 A01 库位库存");
		expect(wrapper.find(".ai-assistant__answer").exists()).toBe(false);
	});
});
