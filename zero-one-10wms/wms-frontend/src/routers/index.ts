import { setupLayouts, createGetRoutes } from "virtual:meta-layouts";
import { routes, handleHotUpdate } from "vue-router/auto-routes";
import { createRouter, createWebHistory } from "vue-router/auto";

import { storeToRefs } from "pinia";
import { ElMessage } from "element-plus";
import { useUserStore } from "stores/user";

import { isConditionsSome } from "@ruan-cat/utils/conditions";

import { collectMenuPaths, isPathPermitted } from "composables/menu-access";

/**
 * 菜单类型
 * @description
 * 每一个页面都必须配置一个菜单类型
 * 告诉菜单自己属于什么类型？
 *
 * - 具体的页面
 * - 目录文件夹
 */
export type MenuType =
	// 页面类型
	| "page"
	// 文件夹类型 即菜单侧边栏的折叠目录
	| "folder"
	// 忽略 这个页面拥有路由，但不会在菜单中显示
	| "ignore";

/**
 * 拓展路由元信息
 * @description
 * 从菜单项复制粘贴部分可用的属性
 *
 * @see https://router.vuejs.org/zh/guide/advanced/meta#TypeScript
 */
declare module "vue-router" {
	interface RouteMeta {
		/** 菜单类型 */
		menuType: MenuType;

		/**
		 * 侧边栏标题
		 * @description
		 * 必须配置的侧边栏标题
		 */
		text: string;

		/**
		 * 侧边栏显示用的icon标签
		 * @description
		 * TODO: 将icon显示的取值列表 提取出来
		 */
		icon: string;

		// 配置侧边栏时 不需要配置子项
		// children?: MenuItem[];

		/**
		 * 是否是案例演示页面？
		 * @description
		 * 对案例演示页面做出专门的配置
		 */
		isSample?: boolean;

		/**
		 * 侧边栏菜单排序
		 * @description
		 * 默认按照降序排序
		 *
		 * 数值越小的，在菜单的位置越靠前
		 *
		 * 数值越大的，在菜单的位置越靠后
		 */
		order?: number;
	}
}

/**
 * 项目原本就有的路由
 * @description
 * 这里预设的都是静态路由
 */
const originRoutes = [
	// 警告 这三个状态页放在 src/components/status/ 下，而自动路由只扫描 src/views（且排除 src/views/status/**、**/components），
	// 因此 definePage 里的 name/path 根本不会注册。必须显式登记，否则守卫 next({ name: "Forbidden" }) 找不到目标，
	// 表现为停留在原 URL 且页面空白（2026-11-26 生产构建浏览器回归实测到的缺陷）。
	{
		path: "/:pathMatch(.*)*",
		name: "NotFound",
		component: () => import("../components/status/404.vue"),
		meta: { menuType: "ignore", text: "404", icon: "" },
	},
	{
		path: "/forbidden",
		name: "Forbidden",
		component: () => import("../components/status/403.vue"),
		meta: { menuType: "ignore", text: "403", icon: "" },
	},
	{
		path: "/error",
		name: "Error",
		component: () => import("../components/status/500.vue"),
		meta: { menuType: "ignore", text: "500", icon: "" },
	},
];

// 警告 不再需要读取主模块路由了 用自动路由的方式实现完毕
// // 读取main模块路由
// const mainRouter = import.meta.glob("./main/index.js", { eager: true });
// for (const path in mainRouter) {
// 	// @ts-ignore
// 	originRoutes.push(...mainRouter[path].default);
// }

// TODO[TEST_CODE]:读取示例演示模块路由
// TODO: 在自动化路由读取函数内 增加忽略匹配 忽略掉全部的 sample 菜单
if (import.meta.env.DEV) {
	// 手动地移除掉示例模块的路由 不再加载
	// const sampleRouter = import.meta.glob("./sample/index.js", { eager: true });
	// for (const path in sampleRouter) {
	// 	// @ts-ignore
	// 	originRoutes.push(...sampleRouter[path].default);
	// }
}

// 定义一个路由对象
const router = createRouter({
	history: createWebHistory(import.meta.env.BASE_URL),
	// 静态状态页路由（403/404/500）必须在这里合并，见 originRoutes 上的说明。
	routes: setupLayouts([...originRoutes, ...routes]),
});

/**
 * 获取路由
 * @description
 * 由于布局系统需要在最外层嵌套一层布局路由
 *
 * 因此在获取路由表时可能会造成混淆
 *
 * 此时可以使用辅助功能
 * @see https://github.com/dishait/vite-plugin-vue-meta-layouts/blob/main/README_EN.md#note
 */
export const getRoutes = createGetRoutes(router);

// 添加一个路由的全局前置守卫
router.beforeEach(async function (to, from, next) {
	// 判断是否是登录页面
	if (
		isConditionsSome([
			() => to.name === "Login",
			() => to.name === "NotFound",
			() => to.name === "Forbidden",
			() => to.name === "Error",
		])
	) {
		next();
		return;
	}

	// TODO[TEST_CODE]:放行示例模块访问
	if (import.meta.env.DEV) {
		if (to.path.indexOf("sample") !== -1) {
			next();
			return;
		}
	}

	// 判断本地是否记录token值
	const store = useUserStore();
	const { isLoaded: _isLoaded, getToken } = storeToRefs(store);
	const token = getToken.value;

	// 如果有token
	if (token) {
		try {
			// 判断是否已经加载数据
			const isLoaded = _isLoaded.value;
			// 如果没有加载
			if (!isLoaded) {
				// 加载用户信息
				await store.loadUser();
				// 加载菜单资源
				await store.loadMenus();
				// 设置加载完毕
				store.setLoaded(true);
			}
		} catch (error) {
			console.error("会话初始化失败", error instanceof Error ? error.message : "unknown");
			// 身份或菜单加载失败时清除旧授权，回登录页重新建立会话。
			store.resetSaveData();
			next({ name: "Login" });
			return;
		}

		// current-user 为空表示令牌无法映射到有效用户，失败关闭。
		if (!store.getUser) {
			next({ name: "Forbidden" });
			return;
		}

		// 加载完毕之后再判断敏感页面是否有菜单授权（见 composables/menu-access.ts）
		const allowedPaths = collectMenuPaths(store.getMenus);
		if (!isPathPermitted(to.path, allowedPaths)) {
			next({ name: "Forbidden" });
			return;
		}
		next();
	}
	// 如果没有token值，直接进入登录
	else {
		next({ name: "Login" });
		ElMessage.warning("在未登录时，禁止访问其他页面！");
	}
});

// This will update routes at runtime without reloading the page
if (import.meta.hot) {
	console.log("我正在热更新路由表！");
	handleHotUpdate(router);
}

export default router;
