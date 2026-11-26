import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";

/**
 * 2026-11-26 生产构建浏览器回归发现的缺陷：403/404/500 页面放在 src/components/status/ 下，
 * 而 unplugin-vue-router 只扫描 src/views（并排除 **\/components 与 src/views/status/**），
 * 因此这些组件里的 definePage() 既不会注册路由，也不会被编译期转换，
 * 运行时直接抛 ReferenceError: definePage is not defined —— 守卫 next({ name: "Forbidden" }) 落空后页面空白。
 *
 * 这条测试不导入 routers/index.ts（它依赖 virtual:meta-layouts，在 vitest 环境不可用），
 * 只做源码级契约断言，避免该缺陷回归。
 */
// __dirname 指向 src/routers/__tests__，向上三级才是 wms-frontend 根目录。
const FRONTEND_ROOT = path.resolve(__dirname, "../../..");

function read(relative: string): string {
	return fs.readFileSync(path.join(FRONTEND_ROOT, relative), "utf8");
}

describe("状态页路由契约", () => {
	it("routers/index.ts 显式登记 403/404/500 三条静态路由", () => {
		const source = read("src/routers/index.ts");
		expect(source).toContain('name: "Forbidden"');
		expect(source).toContain('path: "/forbidden"');
		expect(source).toContain('name: "NotFound"');
		expect(source).toContain('path: "/:pathMatch(.*)*"');
		expect(source).toContain('name: "Error"');
		expect(source).toContain('path: "/error"');
		expect(source).toContain("setupLayouts([...originRoutes, ...routes])");
	});

	it("HTTP 拦截器必须先于路由安装，避免深链接首次身份请求无令牌", () => {
		const source = read("src/main.ts");
		expect(source.indexOf("installHttp(router)")).toBeLessThan(source.indexOf("app.use(router)"));
		expect(source.indexOf("installAxiosWithVueUse(router, axiosInstance)")).toBeLessThan(source.indexOf("app.use(router)"));
	});

	it("状态页组件不再调用 definePage（不在自动路由扫描目录内，调用会在运行时抛 ReferenceError）", () => {
		for (const file of ["403.vue", "404.vue", "500.vue"]) {
			const source = read(`src/components/status/${file}`);
			// 只匹配真实调用 definePage({ ... })，注释里提到该函数名不算。
			expect(source, `${file} 不应包含 definePage({...}) 调用`).not.toMatch(/definePage\s*\(\s*\{/);
		}
	});
});
