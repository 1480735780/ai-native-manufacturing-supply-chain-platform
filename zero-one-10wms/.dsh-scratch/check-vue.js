// 校验 .vue 单文件组件 <script setup> 语法（用 esbuild 转译 TS）
const fs = require("fs");
const path = require("path");
const esbuild = require(path.join(process.cwd(), "node_modules", "esbuild"));

const files = process.argv.slice(2);
let failed = 0;

for (const file of files) {
	const source = fs.readFileSync(file, "utf8");
	const match = source.match(/<script[^>]*>([\s\S]*?)<\/script>/);
	if (!match) {
		console.log(`SKIP  ${file}（未找到 script 块）`);
		continue;
	}
	const code = match[1];
	try {
		esbuild.transformSync(code, { loader: "ts", target: "es2020" });
		console.log(`OK    ${path.basename(path.dirname(file))}/${path.basename(file)}`);
	} catch (err) {
		failed++;
		console.log(`FAIL  ${file}`);
		for (const e of err.errors || []) {
			console.log(`      ${e.text} (line ${e.location && e.location.line})`);
		}
	}
}

// 同时校验 template 里标签是否成对（粗校验：统计开闭标签数量）
for (const file of files) {
	const source = fs.readFileSync(file, "utf8");
	const tpl = source.match(/<template>([\s\S]*)<\/template>/);
	if (!tpl) continue;
	const opens = (tpl[1].match(/<el-[a-z-]+(?=[\s>])/g) || []).length;
	const selfClose = (tpl[1].match(/<el-[a-z-]+[^>]*\/>/g) || []).length;
	const closes = (tpl[1].match(/<\/el-[a-z-]+>/g) || []).length;
	if (opens - selfClose !== closes) {
		failed++;
		console.log(`FAIL  ${file} 模板标签不匹配：开 ${opens}（自闭合 ${selfClose}）闭 ${closes}`);
	}
}

console.log(failed === 0 ? "\nALL_PASS" : `\n${failed} 个文件存在问题`);
process.exit(failed === 0 ? 0 : 1);
