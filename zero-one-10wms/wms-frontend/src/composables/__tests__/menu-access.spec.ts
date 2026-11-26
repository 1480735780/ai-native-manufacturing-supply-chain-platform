import { describe, expect, it } from "vitest";

import {
	collectMenuPaths,
	isPathPermitted,
	isSensitivePath,
	normalizePath,
} from "@/composables/menu-access";

/**
 * 复核缺陷（2026-11-26 第六轮）：`routers/index.ts` 的守卫只检查 token，
 * 手动输入 `/inspection/alerts` 即可进入巡检页面（仅靠后端 code 9997 拦数据）。
 * 这里锁定「敏感路径必须有菜单授权」的判定，以及非敏感路径不受影响。
 */
describe("menu-access", () => {
	it("normalizePath 去掉 query/hash、末尾斜杠并统一大小写", () => {
		expect(normalizePath("/inspection/alerts/")).toBe("/inspection/alerts");
		expect(normalizePath("/inspection/alerts?x=1#top")).toBe("/inspection/alerts");
		expect(normalizePath("/Inspection/Alerts")).toBe("/inspection/alerts");
		expect(normalizePath("/")).toBe("/");
		expect(normalizePath(undefined)).toBe("");
	});

	it("collectMenuPaths 递归收集 functionurl", () => {
		const paths = collectMenuPaths([
			{ id: 1, functionname: "root", iconName: "", functionurl: undefined },
			{
				id: 2,
				functionname: "每日检查",
				iconName: "",
				children: [
					{ id: 3, functionname: "异常巡检", iconName: "", functionurl: "/inspection/alerts" },
				],
			},
		] as any);
		expect(paths).toEqual(["/inspection/alerts"]);
		expect(collectMenuPaths(null)).toEqual([]);
	});

	it("isSensitivePath 只标记巡检前缀", () => {
		expect(isSensitivePath("/inspection")).toBe(true);
		expect(isSensitivePath("/inspection/alerts")).toBe(true);
		expect(isSensitivePath("/inspection/alerts/detail/1")).toBe(true);
		expect(isSensitivePath("/inspectionX/alerts")).toBe(false);
		expect(isSensitivePath("/daycheck/temperature")).toBe(false);
	});

	it("敏感路径必须有菜单授权，菜单为空时拒绝", () => {
		expect(isPathPermitted("/inspection/alerts", ["/inspection/alerts"])).toBe(true);
		expect(isPathPermitted("/Inspection/Alerts", ["/inspection/alerts"])).toBe(true);
		expect(isPathPermitted("/inspection/alerts/", ["/inspection/alerts"])).toBe(true);
		expect(isPathPermitted("/inspection/alerts/detail/1", ["/inspection/alerts"])).toBe(true);
		// cs/KH：后端菜单为空
		expect(isPathPermitted("/inspection/alerts", [])).toBe(false);
		expect(isPathPermitted("/inspection/alerts", null)).toBe(false);
		// cw：菜单不含巡检
		expect(isPathPermitted("/inspection/alerts", ["/home", "/md/goods"])).toBe(false);
	});

	it("非敏感路径不受路由级校验影响（避免存量页面大面积被挡）", () => {
		expect(isPathPermitted("/home", [])).toBe(true);
		expect(isPathPermitted("/md/goods", [])).toBe(true);
		expect(isPathPermitted("/daycheck/temperature", ["/home"])).toBe(true);
	});
});
