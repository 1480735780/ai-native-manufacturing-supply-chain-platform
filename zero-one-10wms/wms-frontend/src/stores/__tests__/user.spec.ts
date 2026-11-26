import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

const { requestForm } = vi.hoisted(() => ({ requestForm: vi.fn() }));

vi.mock("@/apis/request", () => ({
	default: { GET: "GET", requestForm },
}));

import { useUserStore } from "../user";

describe("user store authorization state", () => {
	beforeEach(() => {
		localStorage.clear();
		setActivePinia(createPinia());
		requestForm.mockReset();
	});

	it("空菜单响应清掉旧账号菜单", async () => {
		const store = useUserStore();
		store.menus = [{ id: 1, functionurl: "/inspection/alerts" }] as any;
		requestForm.mockResolvedValue({ data: [] });

		await store.loadMenus();

		expect(store.getMenus).toEqual([]);
	});

	it("设置新令牌时清掉旧用户、菜单和加载标记", () => {
		const store = useUserStore();
		store.user = { username: "old" } as any;
		store.menus = [{ id: 1, functionurl: "/inspection/alerts" }] as any;
		store.setLoaded(true);

		store.setToken({ token: "new-token", refreshToken: "new-refresh" });

		expect(store.getUser).toBeNull();
		expect(store.getMenus).toEqual([]);
		expect(store.isLoaded).toBe(false);
	});

	it("重置会话时同时清掉菜单", () => {
		const store = useUserStore();
		store.menus = [{ id: 1, functionurl: "/inspection/alerts" }] as any;
		store.setToken({ token: "token", refreshToken: "refresh" });

		store.resetSaveData();

		expect(store.getMenus).toEqual([]);
		expect(localStorage.getItem("token")).toBeNull();
		expect(localStorage.getItem("refreshToken")).toBeNull();
	});
});
