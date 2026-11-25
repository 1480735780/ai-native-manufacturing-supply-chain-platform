import { describe, expect, it } from "vitest";

import {
	fallbackNote,
	findAlertSummary,
	isScanSettled,
	mergePolledAlerts,
	severityCountsText,
	stripEmpty,
	summarySourceLabel,
	type InspectionAlert,
	type ScanSummaryItem,
} from "./alerts";

describe("巡检告警 API 纯函数契约", () => {
	it("stripEmpty 去掉 undefined/null/空串，保留 0 与 false", () => {
		expect(
			stripEmpty({
				state: "open",
				severity: "",
				warehouseId: null,
				ruleId: undefined,
				lastAlertId: 0,
				unreadOnly: false,
			}),
		).toEqual({ state: "open", lastAlertId: 0, unreadOnly: false });
	});

	it("mergePolledAlerts 按 alertId 去重：新数据优先，旧数据保留在尾部", () => {
		const base = (alertId: number, state: string): InspectionAlert => ({
			alertId,
			fingerprint: `fp-${alertId}`,
			ruleId: "NOUP-OVERDUE",
			severity: "P1",
			objectType: "no_up_goods",
			objectId: `obj-${alertId}`,
			dimension: {},
			title: `t-${alertId}`,
			state,
			warehouseId: "W01",
			occurrenceCount: 1,
		});
		const previous = [base(1, "open"), base(2, "open"), base(3, "open")];
		const incoming = [base(3, "acknowledged"), base(4, "open")];

		const merged = mergePolledAlerts(previous, incoming);

		// 新轮询数据在前，按 alertId 去重，且同一 alertId 采用新状态
		expect(merged.map((a) => a.alertId)).toEqual([3, 4, 1, 2]);
		expect(merged[0].state).toBe("acknowledged");
		// 长度不重复
		expect(new Set(merged.map((a) => a.alertId)).size).toBe(merged.length);
	});

	it("mergePolledAlerts 在空输入下不抛错", () => {
		expect(mergePolledAlerts([], [])).toEqual([]);
	});
});

describe("巡检摘要（详情抽屉）纯函数契约", () => {
	const item = (overrides: Partial<ScanSummaryItem>): ScanSummaryItem => ({
		scanId: "scan-1",
		ruleId: "NOUP-OVERDUE",
		warehouse: "W01",
		customer: "C1",
		severity: "P0",
		objectCount: 3,
		summary: "上架超时：仓库 W01 客户 C1 共 3 个对象。",
		summarySource: "template",
		...overrides,
	});
	const alert = { ruleId: "NOUP-OVERDUE", warehouseId: "W01", dimension: { warehouse: "W01", customer: "C1" } };

	it("findAlertSummary 按规则 + 仓库 + 客户匹配当前告警所属的那一组", () => {
		const items = [
			item({ customer: "C2", severity: "P1" }),
			item({ customer: "C1" }),
			item({ ruleId: "EXP-NEAR", customer: "C1" }),
		];
		expect(findAlertSummary(items, alert)?.customer).toBe("C1");
		// 客户不同、规则不同都匹配不到；入库延迟规则没有客户，按空串匹配
		expect(findAlertSummary(items, { ...alert, dimension: { customer: "C9" } })).toBeNull();
		expect(findAlertSummary(items, { ...alert, warehouseId: "W02" })).toBeNull();
		const delay = item({ ruleId: "DELAY-OVERDUE", customer: "", severity: "P2" });
		expect(findAlertSummary([delay], { ruleId: "DELAY-OVERDUE", warehouseId: "W01", dimension: { supplier: "S1" } })).toBe(delay);
		expect(findAlertSummary([], alert)).toBeNull();
	});

	it("来源标签与降级说明：模型摘要不提示降级，模板摘要有原因才提示", () => {
		expect(summarySourceLabel("llm")).toBe("模型摘要");
		expect(summarySourceLabel("template")).toBe("模板摘要");
		expect(fallbackNote({ summarySource: "llm", fallbackReason: "timeout" })).toBe("");
		expect(fallbackNote({ summarySource: "template" })).toBe("");
		expect(fallbackNote({ summarySource: "template", fallbackReason: "timeout" })).toBe("模型响应超时，摘要按模板生成");
		expect(fallbackNote({ summarySource: "template", fallbackReason: "something-new" })).toBe(
			"模型摘要已降级（something-new），按模板生成",
		);
	});

	it("扫描未结束时不认为已有摘要；级别分布只列出非零项", () => {
		expect(isScanSettled("succeeded")).toBe(true);
		expect(isScanSettled("failed")).toBe(true);
		expect(isScanSettled("running")).toBe(false);
		expect(isScanSettled("")).toBe(false);
		expect(severityCountsText({ P0: 1, P1: 0, P2: 2 })).toBe("P0 1 个、P2 2 个");
		expect(severityCountsText({ P0: 0, P1: 0, P2: 0 })).toBe("");
		expect(severityCountsText(undefined)).toBe("");
	});
});
