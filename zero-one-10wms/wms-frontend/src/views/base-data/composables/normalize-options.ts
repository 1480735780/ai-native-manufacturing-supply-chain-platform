/**
 * 跨模块下拉 / 树的响应归一化。
 *
 * 背景：基础资料页面要用到 7 个其他服务的字典接口，它们的响应结构完全不统一，
 * 实测（读后端源码确认）如下：
 *
 *  - `/indclas/get-indclasnamelist`   C++ c2-comconfig → `{ enterpriseNameList: string[] }`
 *  - `/entattr/get-entattrnamelist`   C++ c2-comconfig → `{ rows: [{ com_type_code, com_type_name, id }] }`
 *  - `/entstat/get-entstatforlist`    C++ c2-comconfig → `{ items: [{ statusonlyid, enterpriseid, enterprisename }] }`
 *  - `/entleve/level-name`            C++ c2-comconfig → `{ name: [], code: [], id: [], ban: [] }`（平行数组）
 *  - `/othermana/goodsbrand/name-list` Java j8-othermana → `[{ id, goodsBrandName, goodsBrandCode }]`
 *  - `/gc/query-category-tree`        C++ c1-bconf    → `{ DTOList: [{ id, category_code, category_name, category_level, pid, top_node }] }`（扁平，非树）
 *  - `/measurementunit/getnamelist`   Java j4-baseConfig → `string[]`
 *
 * 所以统一在这里做一次归一化，页面只拿 `{ label, value }` 或 `{ label, value, children }`。
 */

export interface DictOption {
	label: string;
	value: string;
}

export interface DictTreeNode extends DictOption {
	children?: DictTreeNode[];
}

/** 取出响应里的数组：兼容裸数组、rows、items、DTOList、list */
export function pickList(data: any): any[] {
	if (Array.isArray(data)) return data;
	if (!data || typeof data !== "object") return [];
	const candidates = [data.rows, data.items, data.DTOList, data.list, data.records];
	for (const item of candidates) {
		if (Array.isArray(item)) return item;
	}
	return [];
}

function firstNonEmpty(item: any, keys: string[]) {
	for (const key of keys) {
		const value = item?.[key];
		if (value !== undefined && value !== null && value !== "") return value;
	}
	return undefined;
}

/**
 * 对象数组 → 下拉选项。
 * @param nameKeys 名称候选字段，按优先级排列
 * @param codeKeys 取值候选字段，按优先级排列（都取不到时退回名称）
 */
export function toOptions(data: any, nameKeys: string[], codeKeys: string[] = []): DictOption[] {
	const list = pickList(data);
	const options: DictOption[] = [];
	for (const item of list) {
		if (item === null || item === undefined) continue;
		if (typeof item === "string" || typeof item === "number") {
			const text = String(item);
			if (text !== "") options.push({ label: text, value: text });
			continue;
		}
		const label = firstNonEmpty(item, nameKeys);
		if (label === undefined) continue;
		const value = firstNonEmpty(item, codeKeys) ?? label;
		options.push({ label: String(label), value: String(value) });
	}
	return options;
}

/** 平行数组（`{ name: [], code: [], id: [] }`）→ 下拉选项 */
export function toParallelOptions(data: any): DictOption[] {
	if (!data || typeof data !== "object") return [];
	const names = Array.isArray(data.name) ? data.name : Array.isArray(data.enterpriseNameList) ? data.enterpriseNameList : null;
	if (!names) return [];
	const codes = Array.isArray(data.code) ? data.code : [];
	const ids = Array.isArray(data.id) ? data.id : [];
	return names
		.map((name: any, index: number) => ({
			label: String(name ?? ""),
			value: String(codes[index] ?? ids[index] ?? name ?? ""),
		}))
		.filter((item: DictOption) => item.label !== "");
}

/** 统一入口：先试平行数组，再试对象数组 */
export function toDictOptions(data: any, nameKeys: string[], codeKeys: string[] = []): DictOption[] {
	const parallel = toParallelOptions(data);
	if (parallel.length > 0) return parallel;
	return toOptions(data, nameKeys, codeKeys);
}

/**
 * 扁平列表 → 树。
 *
 * 后端 `/gc/query-category-tree` 返回的是全量扁平数据，靠 `pid` 关联父子，前端必须自己建树。
 * 注意：`pid` 指向的是**主键 `id`**，而表单要存的是 `category_code`，
 * 所以「建树用的节点标识」和「选项值」必须分开传（nodeIdKeys / valueKeys）。
 */
export function toTree(
	data: any,
	options: { nodeIdKeys: string[]; nameKeys: string[]; pidKeys: string[]; valueKeys?: string[] },
): DictTreeNode[] {
	const list = pickList(data);
	const nodes = new Map<string, DictTreeNode>();
	const parentOf = new Map<string, string>();

	for (const item of list) {
		if (!item || typeof item !== "object") continue;
		const nodeId = firstNonEmpty(item, options.nodeIdKeys);
		const label = firstNonEmpty(item, options.nameKeys);
		if (nodeId === undefined || label === undefined) continue;
		const key = String(nodeId);
		const value = options.valueKeys ? firstNonEmpty(item, options.valueKeys) ?? nodeId : nodeId;
		nodes.set(key, { label: String(label), value: String(value) });
		const pid = firstNonEmpty(item, options.pidKeys);
		if (pid !== undefined) parentOf.set(key, String(pid));
	}

	const roots: DictTreeNode[] = [];
	nodes.forEach((node, key) => {
		const pid = parentOf.get(key);
		const parent = pid === undefined || pid === key ? undefined : nodes.get(pid);
		if (parent) {
			if (!parent.children) parent.children = [];
			parent.children.push(node);
		} else {
			roots.push(node);
		}
	});
	return roots;
}
