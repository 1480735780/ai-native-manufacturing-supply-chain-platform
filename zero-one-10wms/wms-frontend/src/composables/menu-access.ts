/**
 * 菜单级访问判定（路由守卫用，纯函数，便于单测）。
 *
 * 背景（2026-11-26 第六轮复核）：`src/routers/index.ts` 的守卫只判断「有没有 token」，
 * 手动输入 `/inspection/alerts` 就能进入页面；当时唯一拦截是后端 `/agent/alerts/page`
 * 返回 code 9997。也就是说「菜单隐藏」并没有阻止直接访问 URL。
 *
 * 策略：
 *  1. 只对**敏感前缀**做路由级校验（当前是 `/inspection`，即巡检告警页面），
 *     其余页面维持既有行为，避免把 120+ 个存量页面一次性挡死（存量菜单与
 *     `t_s_function` 的 functionurl 并不完全一致，贸然全量校验会大面积 404/403）。
 *  2. 敏感页面必须在后端 `/login/get-menus` 返回的菜单里出现（`functionurl` 命中），
 *     否则跳 403。菜单为空（含 cs/KH 这类无任何菜单的角色）时一律不放行。
 *  3. 菜单路径允许前缀命中：菜单登记 `/inspection/alerts` 时，
 *     `/inspection/alerts/detail/1` 也放行，避免详情路由被误挡。
 *
 * 数据面仍然是最终防线：即使绕过前端守卫，后端 `insp_read` 之外的请求会被
 * `/agent/alerts/page` 拒绝（code 9997），网关也会按角色 403。
 */

import type { MenuItem } from "types/MenuItem";

/** 需要路由级校验的敏感路径前缀 */
export const SENSITIVE_PATH_PREFIXES = ["/inspection"];

/** 把路径归一化：去掉 query/hash、末尾斜杠并统一小写（与 Vue Router 默认行为一致） */
export function normalizePath(path: any): string {
	const raw = String(path ?? "").trim();
	if (!raw) return "";
	const withoutQuery = raw.split("?")[0].split("#")[0];
	const withoutTrailingSlash =
		withoutQuery.length > 1 ? withoutQuery.replace(/\/+$/, "") : withoutQuery;
	return withoutTrailingSlash.toLowerCase();
}

/** 收集菜单里登记的 functionurl（递归 children） */
export function collectMenuPaths(menus: MenuItem[] | null | undefined): string[] {
	const collected: string[] = [];
	const walk = (items: MenuItem[] | null | undefined) => {
		if (!Array.isArray(items)) return;
		for (const item of items) {
			const url = normalizePath(item?.functionurl);
			if (url) collected.push(url);
			if (item?.children && item.children.length > 0) walk(item.children);
		}
	};
	walk(menus);
	return collected;
}

/** 该路径是否属于需要路由级校验的敏感路径 */
export function isSensitivePath(path: any): boolean {
	const normalized = normalizePath(path);
	if (!normalized) return false;
	return SENSITIVE_PATH_PREFIXES.some((prefix) => normalized === prefix || normalized.startsWith(`${prefix}/`));
}

/**
 * 判定某个路径是否允许访问。
 * - 非敏感路径：允许（既有行为不变）。
 * - 敏感路径：必须命中菜单登记路径（精确或前缀）。
 */
export function isPathPermitted(path: any, allowedPaths: string[] | null | undefined): boolean {
	const normalized = normalizePath(path);
	if (!isSensitivePath(normalized)) return true;
	const allowed = Array.isArray(allowedPaths) ? allowedPaths.map(normalizePath).filter(Boolean) : [];
	if (allowed.length === 0) return false;
	return allowed.some((item) => normalized === item || normalized.startsWith(`${item}/`));
}
