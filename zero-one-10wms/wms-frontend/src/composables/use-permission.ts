/**
 * 页面级写权限判断。
 *
 * 背景：项目目前只有「菜单级」权限（t_s_function + 前端 definePage 自动生成路由），
 * 没有按钮级权限表。但业务上存在纯查看角色（财务、客户、领导），他们能进商品/客户等
 * 列表页，却不该看到「录入 / 修改 / 删除」按钮。
 *
 * 策略（刻意保守，避免误伤）：
 *  1. 用户信息里的 `roles` 为空或取不到 → **视为可写**。宁可多显示按钮，也不把现有功能锁死。
 *  2. 只要拥有任意一个「可写角色」，就是可写（财务 + 仓管 → 可写）。
 *  3. 全部角色都命中只读名单 → 只读。
 *
 * 只读名单来自 `t_s_role` 现有角色（cw 财务、KH 客户），并兼容中英文与常见叫法。
 * 产品/运维确认实际只读角色后，只改这一个常量即可，页面无需改动。
 */

import { computed } from "vue";
import { useUserStore } from "@/stores/user";

/** 只读角色名单：角色编码或角色名称，命中任意一个即视为只读角色 */
export const READONLY_ROLES = ["cw", "财务", "KH", "客户", "只读", "查看", "readonly", "read_only", "viewer", "guest"];

function normalizeRole(role: any): string {
	return String(role ?? "")
		.trim()
		.toLowerCase();
}

const READONLY_SET = new Set(READONLY_ROLES.map(normalizeRole));

export function usePermission() {
	const userStore = useUserStore();

	/** 当前用户的角色列表（角色名称或编码，取决于后端 LoginVO.roles 的填充方式） */
	const roles = computed<string[]>(() => {
		const roles = userStore.getUser?.roles;
		return Array.isArray(roles) ? roles.map((item: any) => String(item)) : [];
	});

	/** 是否只读：无角色信息时一律按可写处理 */
	const readOnly = computed(() => {
		if (roles.value.length === 0) return false;
		return roles.value.every((role) => READONLY_SET.has(normalizeRole(role)));
	});

	/** 是否可写 */
	const canWrite = computed(() => !readOnly.value);

	return { roles, readOnly, canWrite };
}
