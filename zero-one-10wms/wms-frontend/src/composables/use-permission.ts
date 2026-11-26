/**
 * 页面级写权限判断。
 *
 * 背景：项目目前只有「菜单级」权限（t_s_function + 前端 definePage 自动生成路由），
 * 没有按钮级权限表。但业务上存在纯查看角色（财务、客户、领导），他们能进商品/客户等
 * 列表页，却不该看到「录入 / 修改 / 删除」按钮。
 *
 * 策略（2026-11-26 第六轮复核后改为白名单式失败关闭）：
 *  1. 用户信息里的 `roles` 为空或取不到 → **视为只读**。原来「无角色视为可写」在
 *     getMenus 为空、角色未填充时会把写按钮暴露给无权用户（cs/KH 复核缺陷）。
 *  2. 只有命中**可写角色白名单**才算可写（财务 + 仓管 → 任一可写即可写）。
 *  3. **未知角色一律只读**：第六轮复核指出旧实现用「全命中只读名单」判断，
 *     于是 `xyz` 这种没登记过的角色反而被当可写（默认放行）。现在反过来：
 *     未登记 = 不可写，新增角色必须显式加入 `WRITABLE_ROLES`。
 *
 * 名单来自 `t_s_role` 现有角色：可写 cg 仓管 / ckjl 仓库经理 / gly 管理员，
 * 只读 cs 测试、cw 财务、KH 客户。产品/运维确认角色后，只改这两个常量即可。
 */

import { computed } from "vue";
import { useUserStore } from "@/stores/user";

/** 只读角色名单：角色编码或角色名称，命中即视为只读角色 */
export const READONLY_ROLES = ["cs", "测试", "cw", "财务", "KH", "客户", "只读", "查看", "readonly", "read_only", "viewer", "guest"];

/**
 * 可写角色名单：只有显式列在这里的角色才可写。
 * 未登记角色（例如拼错或新加未评估的角色）→ 只读，避免默认放行。
 */
export const WRITABLE_ROLES = ["cg", "仓管", "仓库管理员", "ckjl", "仓库经理", "gly", "管理员", "admin", "wms_admin"];

function normalizeRole(role: any): string {
	return String(role ?? "")
		.trim()
		.toLowerCase();
}

const READONLY_SET = new Set(READONLY_ROLES.map(normalizeRole));
const WRITABLE_SET = new Set(WRITABLE_ROLES.map(normalizeRole));

/**
 * 纯函数形式的只读判定（便于单测）：
 * 无角色 → 只读；命中可写白名单 → 可写；其余（含只读名单与未知角色）→ 只读。
 */
export function isReadOnly(roles: string[] | null | undefined): boolean {
	const list = Array.isArray(roles) ? roles : [];
	if (list.length === 0) return true;
	const hasWritable = list.some((role) => WRITABLE_SET.has(normalizeRole(role)));
	if (hasWritable) return false;
	return true;
}

/** 该角色是否被显式登记为只读角色（供日志/提示使用） */
export function isKnownReadonlyRole(role: any): boolean {
	return READONLY_SET.has(normalizeRole(role));
}

export function usePermission() {
	const userStore = useUserStore();

	/** 当前用户的角色列表（角色名称或编码，取决于后端 LoginVO.roles 的填充方式） */
	const roles = computed<string[]>(() => {
		const roles = userStore.getUser?.roles;
		return Array.isArray(roles) ? roles.map((item: any) => String(item)) : [];
	});

	/** 是否只读：无角色信息时按只读处理（失败关闭） */
	const readOnly = computed(() => isReadOnly(roles.value));

	/** 是否可写 */
	const canWrite = computed(() => !readOnly.value);

	return { roles, readOnly, canWrite };
}
