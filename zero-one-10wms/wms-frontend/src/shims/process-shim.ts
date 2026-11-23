/**
 * 浏览器端 node:process 垫片。
 * 部分第三方依赖（如 @ruan-cat/utils 的间接依赖）会读取 process.env，
 * 在 Vite 浏览器环境中会导致 "Cannot destructure property ... as it is undefined" 而阻塞挂载。
 */
export const env: Record<string, string | undefined> = {};
export const argv: string[] = [];
export const cwd = () => "/";

export default { env, argv, cwd };
