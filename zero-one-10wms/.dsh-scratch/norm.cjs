var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);
var normalize_options_exports = {};
__export(normalize_options_exports, {
  pickList: () => pickList,
  toDictOptions: () => toDictOptions,
  toOptions: () => toOptions,
  toParallelOptions: () => toParallelOptions,
  toTree: () => toTree
});
module.exports = __toCommonJS(normalize_options_exports);
function pickList(data) {
  if (Array.isArray(data)) return data;
  if (!data || typeof data !== "object") return [];
  const candidates = [data.rows, data.items, data.DTOList, data.list, data.records];
  for (const item of candidates) {
    if (Array.isArray(item)) return item;
  }
  return [];
}
function firstNonEmpty(item, keys) {
  for (const key of keys) {
    const value = item?.[key];
    if (value !== void 0 && value !== null && value !== "") return value;
  }
  return void 0;
}
function toOptions(data, nameKeys, codeKeys = []) {
  const list = pickList(data);
  const options = [];
  for (const item of list) {
    if (item === null || item === void 0) continue;
    if (typeof item === "string" || typeof item === "number") {
      const text = String(item);
      if (text !== "") options.push({ label: text, value: text });
      continue;
    }
    const label = firstNonEmpty(item, nameKeys);
    if (label === void 0) continue;
    const value = firstNonEmpty(item, codeKeys) ?? label;
    options.push({ label: String(label), value: String(value) });
  }
  return options;
}
function toParallelOptions(data) {
  if (!data || typeof data !== "object") return [];
  const names = Array.isArray(data.name) ? data.name : Array.isArray(data.enterpriseNameList) ? data.enterpriseNameList : null;
  if (!names) return [];
  const codes = Array.isArray(data.code) ? data.code : [];
  const ids = Array.isArray(data.id) ? data.id : [];
  return names.map((name, index) => ({
    label: String(name ?? ""),
    value: String(codes[index] ?? ids[index] ?? name ?? "")
  })).filter((item) => item.label !== "");
}
function toDictOptions(data, nameKeys, codeKeys = []) {
  const parallel = toParallelOptions(data);
  if (parallel.length > 0) return parallel;
  return toOptions(data, nameKeys, codeKeys);
}
function toTree(data, options) {
  const list = pickList(data);
  const nodes = /* @__PURE__ */ new Map();
  const parentOf = /* @__PURE__ */ new Map();
  for (const item of list) {
    if (!item || typeof item !== "object") continue;
    const nodeId = firstNonEmpty(item, options.nodeIdKeys);
    const label = firstNonEmpty(item, options.nameKeys);
    if (nodeId === void 0 || label === void 0) continue;
    const key = String(nodeId);
    const value = options.valueKeys ? firstNonEmpty(item, options.valueKeys) ?? nodeId : nodeId;
    nodes.set(key, { label: String(label), value: String(value) });
    const pid = firstNonEmpty(item, options.pidKeys);
    if (pid !== void 0) parentOf.set(key, String(pid));
  }
  const roots = [];
  nodes.forEach((node, key) => {
    const pid = parentOf.get(key);
    const parent = pid === void 0 || pid === key ? void 0 : nodes.get(pid);
    if (parent) {
      if (!parent.children) parent.children = [];
      parent.children.push(node);
    } else {
      roots.push(node);
    }
  });
  return roots;
}
