import { describe, expect, it } from "vitest";

import { READONLY_ROLES, WRITABLE_ROLES, isReadOnly, isKnownReadonlyRole } from "@/composables/use-permission";

/**
 * 复核缺陷（2026-11-26）：原实现把「无角色」当作可写，导致 cs/KH 这类只读角色
 * 在角色信息缺失时看到录入/修改/删除按钮。这里锁定失败关闭与只读名单行为。
 */
describe("use-permission isReadOnly", () => {
	it("无角色信息时按只读处理（失败关闭）", () => {
		expect(isReadOnly([])).toBe(true);
		expect(isReadOnly(undefined)).toBe(true);
		expect(isReadOnly(null)).toBe(true);
	});

	it("cs/cw/KH 命中只读名单", () => {
		expect(READONLY_ROLES).toContain("cs");
		expect(isReadOnly(["cs"])).toBe(true);
		expect(isReadOnly(["cw"])).toBe(true);
		expect(isReadOnly(["KH"])).toBe(true);
	});

	it("可写角色可写，只读+可写混合仍可写", () => {
		expect(WRITABLE_ROLES).toContain("cg");
		expect(isReadOnly(["ckjl"])).toBe(false);
		expect(isReadOnly(["gly"])).toBe(false);
		expect(isReadOnly(["cw", "cg"])).toBe(false);
	});

	it("未知/未登记角色一律只读（不再默认放行）", () => {
		// 第六轮复核缺陷：旧实现用「全命中只读名单」判断，xyz 这类未登记角色被判可写。
		expect(isReadOnly(["xyz"])).toBe(true);
		expect(isReadOnly(["cg_typo"])).toBe(true);
		expect(isReadOnly(["cs", "xyz"])).toBe(true);
		expect(isKnownReadonlyRole("cs")).toBe(true);
		expect(isKnownReadonlyRole("xyz")).toBe(false);
	});
});
