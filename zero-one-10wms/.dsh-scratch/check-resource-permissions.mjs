#!/usr/bin/env node
/**
 * Java HTTP 端点权限声明静态门禁（ADR-022）。
 *
 * 身份键 = HTTP 方法 + 规范化路径。baseline 之外的端点必须具有
 * @ResourcePermission 或显式 Spring Security 声明；baseline 只豁免存量，不自动增长。
 *
 * 用法：
 *   node .dsh-scratch/check-resource-permissions.mjs --check
 *   node .dsh-scratch/check-resource-permissions.mjs --self-test
 *   node .dsh-scratch/check-resource-permissions.mjs --write-baseline
 *   node .dsh-scratch/check-resource-permissions.mjs --write-baseline --force
 */
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";

const SCANNER_VERSION = 1;
const MAPPING_NAMES = new Set([
  "GetMapping", "PostMapping", "PutMapping", "DeleteMapping", "PatchMapping", "RequestMapping",
]);
const SHORTHAND_METHODS = {
  GetMapping: "GET",
  PostMapping: "POST",
  PutMapping: "PUT",
  DeleteMapping: "DELETE",
  PatchMapping: "PATCH",
};
const DECLARATION_NAMES = new Set([
  "ResourcePermission", "PreAuthorize", "Secured", "RolesAllowed", "PermitAll", "DenyAll",
]);
const HTTP_METHODS = new Set(["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "TRACE"]);

function parseArgs(argv) {
  const options = { root: null, baseline: null, mode: "check", force: false };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--check") options.mode = "check";
    else if (arg === "--self-test") options.mode = "self-test";
    else if (arg === "--write-baseline") options.mode = "write-baseline";
    else if (arg === "--force") options.force = true;
    else if (arg === "--root" || arg === "--baseline") {
      const value = argv[++i];
      if (!value) throw new Error(`${arg} 缺少参数`);
      options[arg.slice(2)] = path.resolve(value);
    } else if (arg === "--help" || arg === "-h") {
      options.mode = "help";
    } else {
      throw new Error(`未知参数: ${arg}`);
    }
  }
  return options;
}

function isIdentifierStart(code) {
  return /[A-Za-z_$]/.test(code) || code.charCodeAt(0) >= 0x80;
}

function isIdentifierPart(code) {
  return /[A-Za-z0-9_$]/.test(code) || code.charCodeAt(0) >= 0x80;
}

function decodeJavaString(raw, file, line) {
  let result = "";
  for (let i = 0; i < raw.length; i += 1) {
    const ch = raw[i];
    if (ch !== "\\") {
      result += ch;
      continue;
    }
    i += 1;
    if (i >= raw.length) throw new Error(`${file}:${line} Java 字符串转义不完整`);
    const escaped = raw[i];
    const simple = { n: "\n", r: "\r", t: "\t", b: "\b", f: "\f", '"': '"', "'": "'", "\\": "\\" };
    if (Object.hasOwn(simple, escaped)) {
      result += simple[escaped];
    } else if (escaped === "u") {
      const hex = raw.slice(i + 1, i + 5);
      if (!/^[0-9a-fA-F]{4}$/.test(hex)) throw new Error(`${file}:${line} Java Unicode 转义非法`);
      result += String.fromCharCode(Number.parseInt(hex, 16));
      i += 4;
    } else if (/[0-7]/.test(escaped)) {
      let octal = escaped;
      while (octal.length < 3 && /[0-7]/.test(raw[i + 1] || "")) octal += raw[++i];
      result += String.fromCharCode(Number.parseInt(octal, 8));
    } else {
      throw new Error(`${file}:${line} 不支持的 Java 字符串转义 \\${escaped}`);
    }
  }
  return result;
}

function tokenize(source, file) {
  const tokens = [];
  let i = 0;
  let line = 1;
  while (i < source.length) {
    const ch = source[i];
    if (/\s/.test(ch)) {
      if (ch === "\n") line += 1;
      i += 1;
      continue;
    }
    if (ch === "/" && source[i + 1] === "/") {
      i += 2;
      while (i < source.length && source[i] !== "\n") i += 1;
      continue;
    }
    if (ch === "/" && source[i + 1] === "*") {
      const startLine = line;
      i += 2;
      while (i < source.length && !(source[i] === "*" && source[i + 1] === "/")) {
        if (source[i] === "\n") line += 1;
        i += 1;
      }
      if (i >= source.length) throw new Error(`${file}:${startLine} 块注释未闭合`);
      i += 2;
      continue;
    }
    if (ch === '"' || ch === "'" || ch === "`") {
      const quote = ch;
      const startLine = line;
      const textBlock = quote === '"' && source.slice(i, i + 3) === '"""';
      if (textBlock) i += 3;
      else i += 1;
      let raw = "";
      let closed = false;
      while (i < source.length) {
        if (textBlock && source.slice(i, i + 3) === '"""') {
          i += 3;
          closed = true;
          break;
        }
        if (!textBlock && source[i] === quote) {
          i += 1;
          closed = true;
          break;
        }
        if (source[i] === "\\") {
          raw += source[i] + (source[i + 1] || "");
          if (source[i + 1] === "\n") line += 1;
          i += 2;
          continue;
        }
        if (!textBlock && source[i] === "\n") throw new Error(`${file}:${startLine} 字符串未闭合`);
        if (source[i] === "\n") line += 1;
        raw += source[i];
        i += 1;
      }
      if (!closed) throw new Error(`${file}:${startLine} 字符串/文本块未闭合`);
      tokens.push({ kind: "string", symbol: null, value: decodeJavaString(raw, file, startLine), line: startLine, offset: i });
      continue;
    }
    if (isIdentifierStart(ch)) {
      const start = i;
      i += 1;
      while (i < source.length && isIdentifierPart(source[i])) i += 1;
      tokens.push({ kind: "identifier", symbol: null, value: source.slice(start, i), line, offset: i });
      continue;
    }
    if (/[0-9]/.test(ch)) {
      const start = i;
      i += 1;
      while (i < source.length && /[A-Za-z0-9_.]/.test(source[i])) i += 1;
      tokens.push({ kind: "number", symbol: null, value: source.slice(start, i), line, offset: i });
      continue;
    }
    tokens.push({ kind: "symbol", symbol: ch, value: ch, line, offset: ++i });
  }

  let depth = 0;
  let parentheses = 0;
  let brackets = 0;
  for (const token of tokens) {
    token.depthBefore = depth;
    token.parenthesesBefore = parentheses;
    token.bracketsBefore = brackets;
    if (token.symbol === "{") depth += 1;
    else if (token.symbol === "}") {
      depth -= 1;
      if (depth < 0) throw new Error(`${file}:${token.line} 多余的右花括号`);
    } else if (token.symbol === "(") parentheses += 1;
    else if (token.symbol === ")") parentheses -= 1;
    else if (token.symbol === "[") brackets += 1;
    else if (token.symbol === "]") brackets -= 1;
    if (parentheses < 0 || brackets < 0) throw new Error(`${file}:${token.line} 多余的右括号`);
    token.depthAfter = depth;
  }
  if (depth !== 0 || parentheses !== 0 || brackets !== 0) throw new Error(`${file} 括号未闭合`);
  return tokens;
}

function matchingToken(tokens, openIndex, file) {
  const open = tokens[openIndex].value;
  const close = { "(": ")", "{": "}", "[": "]" }[open];
  if (!close) throw new Error(`${file}:${tokens[openIndex].line} 内部错误：不是成对符号`);
  let balance = 0;
  for (let i = openIndex; i < tokens.length; i += 1) {
    if (tokens[i].symbol === open) balance += 1;
    else if (tokens[i].symbol === close) {
      balance -= 1;
      if (balance === 0) return i;
    }
  }
  throw new Error(`${file}:${tokens[openIndex].line} ${open}${close} 未闭合`);
}

function readAnnotation(tokens, index, file) {
  if (tokens[index]?.symbol !== "@") return null;
  let cursor = index + 1;
  if (tokens[cursor]?.kind !== "identifier") return null;
  let name = tokens[cursor].value;
  cursor += 1;
  while (tokens[cursor]?.symbol === "." && tokens[cursor + 1]?.kind === "identifier") {
    name += `.${tokens[cursor + 1].value}`;
    cursor += 2;
  }
  let args = [];
  let end = cursor - 1;
  if (tokens[cursor]?.symbol === "(") {
    const close = matchingToken(tokens, cursor, file);
    args = tokens.slice(cursor + 1, close);
    end = close;
  }
  return { name, simpleName: name.split(".").at(-1), start: index, end, args, line: tokens[index].line };
}

function splitTopLevel(tokens, delimiter, file) {
  const parts = [];
  let start = 0;
  const stack = [];
  const pairs = { "(": ")", "{": "}", "[": "]" };
  for (let i = 0; i < tokens.length; i += 1) {
    const value = tokens[i].symbol;
    if (Object.hasOwn(pairs, value)) stack.push(pairs[value]);
    else if (stack.length > 0 && value === stack.at(-1)) stack.pop();
    else if (value === delimiter && stack.length === 0) {
      parts.push(tokens.slice(start, i));
      start = i + 1;
    }
  }
  if (stack.length > 0) throw new Error(`${file}:${tokens[0]?.line || "?"} 注解参数括号未闭合`);
  parts.push(tokens.slice(start));
  return parts;
}

function annotationArguments(annotation, file) {
  if (annotation.args.length === 0) return [];
  const result = [];
  for (const part of splitTopLevel(annotation.args, ",", file)) {
    if (part.length === 0) continue;
    let equal = -1;
    const stack = [];
    const pairs = { "(": ")", "{": "}", "[": "]" };
    for (let i = 0; i < part.length; i += 1) {
      const value = part[i].symbol;
      if (Object.hasOwn(pairs, value)) stack.push(pairs[value]);
      else if (stack.length > 0 && value === stack.at(-1)) stack.pop();
      else if (value === "=" && stack.length === 0) { equal = i; break; }
    }
    if (equal >= 0) {
      if (equal !== 1 || part[0].kind !== "identifier") {
        throw new Error(`${file}:${annotation.line} 无法解析 @${annotation.simpleName} 的命名参数`);
      }
      result.push({ name: part[0].value, tokens: part.slice(equal + 1) });
    } else {
      result.push({ name: null, tokens: part });
    }
  }
  return result;
}

function unwrapOuter(tokens, open, close, file) {
  if (tokens.length < 2 || tokens[0].symbol !== open || tokens.at(-1).symbol !== close) return null;
  try {
    return matchingToken(tokens, 0, file) === tokens.length - 1 ? tokens.slice(1, -1) : null;
  } catch {
    return null;
  }
}

function stringExpression(tokens, file, annotation) {
  let current = tokens;
  const unwrapped = unwrapOuter(current, "(", ")", file);
  if (unwrapped) current = unwrapped;
  if (current.length === 0) throw new Error(`${file}:${annotation.line} @${annotation.simpleName} 路径表达式为空`);
  const values = [];
  let expectString = true;
  for (const token of current) {
    if (expectString) {
      if (token.kind !== "string") {
        throw new Error(`${file}:${annotation.line} @${annotation.simpleName} 仅支持字面量路径，不支持常量/动态拼接`);
      }
      values.push(token.value);
    } else if (token.symbol !== "+") {
      throw new Error(`${file}:${annotation.line} @${annotation.simpleName} 路径仅支持字符串字面量 + 拼接`);
    }
    expectString = !expectString;
  }
  if (expectString) throw new Error(`${file}:${annotation.line} @${annotation.simpleName} 字符串拼接不完整`);
  return values.join("");
}

function stringArrayExpression(tokens, file, annotation) {
  const inner = unwrapOuter(tokens, "{", "}", file);
  if (!inner) return [stringExpression(tokens, file, annotation)];
  const parts = splitTopLevel(inner, ",", file).filter((part) => part.length > 0);
  return parts.map((part) => stringExpression(part, file, annotation));
}

function mappingPaths(annotation, file) {
  const args = annotationArguments(annotation, file);
  const named = args.filter((arg) => arg.name === "value" || arg.name === "path");
  const positional = args.filter((arg) => arg.name === null);
  if (named.length > 2 || positional.length > 1) {
    throw new Error(`${file}:${annotation.line} @${annotation.simpleName} 的 value/path 参数过多`);
  }
  let selected = named.length > 0 ? named[0].tokens : positional[0]?.tokens;
  if (named.length === 2) {
    const first = stringArrayExpression(named[0].tokens, file, annotation);
    const second = stringArrayExpression(named[1].tokens, file, annotation);
    if (JSON.stringify(first) !== JSON.stringify(second)) {
      throw new Error(`${file}:${annotation.line} @${annotation.simpleName} 的 value 与 path 不一致`);
    }
    selected = named[0].tokens;
  }
  if (positional.length > 0 && named.length > 0) {
    throw new Error(`${file}:${annotation.line} @${annotation.simpleName} 不能混用位置参数与 value/path`);
  }
  return selected === undefined ? [""] : stringArrayExpression(selected, file, annotation);
}

function mappingMethods(annotation, file) {
  if (Object.hasOwn(SHORTHAND_METHODS, annotation.simpleName)) {
    return [SHORTHAND_METHODS[annotation.simpleName]];
  }
  const methodArg = annotationArguments(annotation, file).find((arg) => arg.name === "method");
  if (!methodArg) return ["*"];
  const inner = unwrapOuter(methodArg.tokens, "{", "}", file) || methodArg.tokens;
  const methods = splitTopLevel(inner, ",", file).filter((part) => part.length > 0).map((part) => {
    if (part.length === 3 && part[1].symbol === "." && part[0].kind === "identifier" && part[2].kind === "identifier"
        && ["RequestMethod", "HttpMethod"].includes(part[0].value)) return part[2].value;
    if (part.length === 1 && part[0].kind === "identifier") return part[0].value;
    throw new Error(`${file}:${annotation.line} @RequestMapping 仅支持 RequestMethod/HttpMethod 字面量`);
  });
  if (methods.length === 0 || methods.some((method) => !HTTP_METHODS.has(method))) {
    throw new Error(`${file}:${annotation.line} @RequestMapping 含有不支持的 HTTP 方法`);
  }
  return [...new Set(methods)];
}

function normalizePath(rawPath, file, line) {
  if (/[?#]/.test(rawPath)) throw new Error(`${file}:${line} 映射路径不得包含 query/fragment: ${rawPath}`);
  const withSlash = rawPath.startsWith("/") ? rawPath : `/${rawPath}`;
  const segments = withSlash.split("/").filter((segment) => segment.length > 0);
  if (segments.some((segment) => segment === "." || segment === "..")) {
    throw new Error(`${file}:${line} 映射路径不得包含 . 或 ..: ${rawPath}`);
  }
  return `/${segments.join("/")}`;
}

function joinPath(base, child) {
  if (!base || base === "/") return child || "/";
  if (!child || child === "/") return base;
  return `${base.replace(/\/$/, "")}/${child.replace(/^\//, "")}`;
}

function endpointKey(method, route) {
  return `${method} ${route}`;
}

function validateDeclaration(annotation, file) {
  const args = annotationArguments(annotation, file);
  if (annotation.simpleName === "ResourcePermission") {
    const namedRolesArg = args.find((arg) => arg.name === "roles");
    const publicArg = args.find((arg) => arg.name === "allowPublic");
    const positional = args.filter((arg) => arg.name === null);
    if (args.some((arg) => !["roles", "allowPublic"].includes(arg.name) && arg.name !== null)) {
      throw new Error(`${file}:${annotation.line} @ResourcePermission 含未知参数`);
    }
    if (positional.length > 1 || (positional.length > 0 && namedRolesArg)) {
      throw new Error(`${file}:${annotation.line} @ResourcePermission 的 roles 位置参数与命名参数不能重复`);
    }
    const rolesArg = namedRolesArg || (positional.length === 1 ? { tokens: positional[0].tokens } : null);
    const roles = rolesArg ? stringArrayExpression(rolesArg.tokens, file, annotation) : [];
    if (roles.some((role) => !role.trim())) throw new Error(`${file}:${annotation.line} @ResourcePermission roles 含空角色`);
    let allowPublic = false;
    if (publicArg) {
      if (publicArg.tokens.length !== 1 || !["true", "false"].includes(publicArg.tokens[0].value)) {
        throw new Error(`${file}:${annotation.line} @ResourcePermission allowPublic 必须是 true/false 字面量`);
      }
      allowPublic = publicArg.tokens[0].value === "true";
    }
    if (roles.length === 0 && !allowPublic) {
      throw new Error(`${file}:${annotation.line} @ResourcePermission 必须声明非空 roles 或 allowPublic=true`);
    }
    if (roles.length > 0 && allowPublic) {
      throw new Error(`${file}:${annotation.line} @ResourcePermission 不能同时声明 roles 与 allowPublic=true`);
    }
    return { kind: annotation.simpleName, roles, allowPublic };
  }
  if (["PreAuthorize", "Secured", "RolesAllowed"].includes(annotation.simpleName)) {
    const valueArg = args.find((arg) => arg.name === "value") || args.find((arg) => arg.name === null);
    const values = valueArg ? stringArrayExpression(valueArg.tokens, file, annotation) : [];
    if (values.length === 0 || values.some((value) => !value.trim())) {
      throw new Error(`${file}:${annotation.line} @${annotation.simpleName} 必须包含非空显式表达式/角色`);
    }
    return { kind: annotation.simpleName, values };
  }
  if (args.length !== 0) throw new Error(`${file}:${annotation.line} @${annotation.simpleName} 不接受参数`);
  return { kind: annotation.simpleName };
}

function previousMemberBoundary(tokens, index, memberDepth, file) {
  for (let i = index - 1; i >= 0; i -= 1) {
    const token = tokens[i];
    if (token.parenthesesBefore !== 0 || token.bracketsBefore !== 0) continue;
    if (token.symbol === ";" && token.depthBefore === memberDepth) return i;
    if (token.symbol === "}" && token.depthBefore === memberDepth + 1 && token.depthAfter === memberDepth) return i;
  }
  return -1;
}

function parseJavaFile(file, source) {
  const tokens = tokenize(source, file);
  const annotations = new Map();
  for (let i = 0; i < tokens.length; i += 1) {
    if (tokens[i].symbol !== "@") continue;
    const annotation = readAnnotation(tokens, i, file);
    if (annotation) annotations.set(i, annotation);
  }

  const endpoints = [];
  const consumedAnnotations = new Set();
  const classAnnotationStarts = new Set();
  const typeRanges = [];
  for (let i = 0; i < tokens.length; i += 1) {
    const token = tokens[i];
    if (!["class", "interface"].includes(token.value) || token.kind !== "identifier") continue;
    if (tokens[i - 1]?.symbol === "@" || tokens[i - 1]?.symbol === ".") continue;
    if (tokens[i + 1]?.kind !== "identifier") continue;
    const depth = token.depthBefore;
    let open = -1;
    for (let j = i + 1; j < tokens.length; j += 1) {
      if (tokens[j].symbol === ";" && tokens[j].depthBefore === depth) break;
      if (tokens[j].symbol === "{" && tokens[j].depthBefore === depth) { open = j; break; }
    }
    if (open < 0) continue;
    const close = matchingToken(tokens, open, file);
    typeRanges.push({ start: i, open, close, name: tokens[i + 1].value, depth });
    const boundary = previousMemberBoundary(tokens, i, depth, file);
    const classAnnotations = [];
    for (let j = boundary + 1; j < i; j += 1) {
      const annotation = annotations.get(j);
      if (annotation && annotation.line <= token.line && tokens[j].depthBefore === depth) {
        classAnnotations.push(annotation);
        classAnnotationStarts.add(j);
        consumedAnnotations.add(j);
      }
    }
    const classMappings = classAnnotations.filter((annotation) => MAPPING_NAMES.has(annotation.simpleName));
    if (classMappings.some((annotation) => annotation.simpleName !== "RequestMapping")) {
      throw new Error(`${file}:${token.line} 类型上只能使用 @RequestMapping`);
    }
    if (classMappings.length > 1) throw new Error(`${file}:${token.line} 类型上存在多个 @RequestMapping`);
    const isFeign = classAnnotations.some((annotation) => annotation.simpleName === "FeignClient");
    const classPaths = classMappings.length === 0
      ? [""]
      : mappingPaths(classMappings[0], file).map((route) => normalizePath(route, file, classMappings[0].line));
    if (classMappings.length > 0 && annotationArguments(classMappings[0], file).some((arg) => arg.name === "method")) {
      throw new Error(`${file}:${classMappings[0].line} 不支持类型级 @RequestMapping(method=...)`);
    }
    const classDeclarations = classAnnotations
      .filter((annotation) => DECLARATION_NAMES.has(annotation.simpleName))
      .map((annotation) => validateDeclaration(annotation, file));

    const memberDepth = depth + 1;
    for (let j = open + 1; j < close; j += 1) {
      const annotation = annotations.get(j);
      if (!annotation || !MAPPING_NAMES.has(annotation.simpleName)) continue;
      if (tokens[j].depthBefore !== memberDepth || classAnnotationStarts.has(j)) continue;
      consumedAnnotations.add(j);
      if (isFeign) continue; // 出站 Feign 契约不是网关入站端点。

      let parameterOpen = -1;
      let cursor = annotation.end + 1;
      while (cursor < close) {
        const nextAnnotation = annotations.get(cursor);
        if (nextAnnotation) { cursor = nextAnnotation.end + 1; continue; }
        const value = tokens[cursor].value;
        if (tokens[cursor].depthBefore === memberDepth && value === "(") { parameterOpen = cursor; break; }
        if (tokens[cursor].depthBefore === memberDepth && [";", "=", "{", "}"].includes(value)) {
          throw new Error(`${file}:${annotation.line} @${annotation.simpleName} 未标注到方法上`);
        }
        cursor += 1;
      }
      if (parameterOpen < 0 || tokens[parameterOpen - 1]?.kind !== "identifier") {
        throw new Error(`${file}:${annotation.line} 无法定位 @${annotation.simpleName} 对应的方法名`);
      }
      const methodName = tokens[parameterOpen - 1].value;
      const boundary = previousMemberBoundary(tokens, j, memberDepth, file);
      const methodAnnotations = [];
      for (let k = boundary + 1; k < parameterOpen; k += 1) {
        const candidate = annotations.get(k);
        if (candidate && tokens[k].depthBefore === memberDepth && !classAnnotationStarts.has(k)) {
          methodAnnotations.push(candidate);
        }
      }
      const methodDeclarations = methodAnnotations
        .filter((candidate) => DECLARATION_NAMES.has(candidate.simpleName))
        .map((candidate) => validateDeclaration(candidate, file));
      const declaration = methodDeclarations.length > 0 ? methodDeclarations : classDeclarations;
      const methodPaths = mappingPaths(annotation, file).map((route) => normalizePath(route, file, annotation.line));
      const methods = mappingMethods(annotation, file);
      for (const base of classPaths) {
        for (const child of methodPaths) {
          const route = normalizePath(joinPath(base, child), file, annotation.line);
          for (const method of methods) {
            endpoints.push({
              key: endpointKey(method, route), method, path: route,
              source: file, line: annotation.line, typeName: typeRanges.find((range) =>
                range.open < j && j < range.close && range.depth === depth)?.name || tokens[i + 1].value,
              methodName, declaration,
            });
          }
        }
      }
    }
  }

  for (const [index, annotation] of annotations) {
    if (MAPPING_NAMES.has(annotation.simpleName) && !consumedAnnotations.has(index)) {
      throw new Error(`${file}:${annotation.line} 发现无法归类的 @${annotation.simpleName}，静态门禁拒绝漏扫`);
    }
  }
  return endpoints;
}

function javaSources(root) {
  const javaRoot = path.join(root, "wms-java");
  if (!fs.existsSync(javaRoot)) throw new Error(`找不到 Java 根目录: ${javaRoot}`);
  const files = [];
  function walk(directory) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      if (["target", ".git", "node_modules"].includes(entry.name)) continue;
      const full = path.join(directory, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (entry.isFile() && entry.name.endsWith(".java")) files.push(full);
    }
  }
  walk(javaRoot);
  return files.filter((file) => {
    const relative = path.relative(javaRoot, file).replaceAll("\\", "/");
    return relative.includes("/src/main/java/");
  }).sort();
}

function scanJava(root) {
  const files = javaSources(root);
  const endpoints = [];
  const errors = [];
  for (const full of files) {
    const file = path.relative(root, full).replaceAll("\\", "/");
    try {
      let source = fs.readFileSync(full, "utf8");
      if (source.charCodeAt(0) === 0xfeff) source = source.slice(1);
      endpoints.push(...parseJavaFile(file, source));
    } catch (error) {
      errors.push(`${file}: ${error.message}`);
    }
  }
  if (endpoints.length === 0 && errors.length === 0) errors.push("未扫描到任何 Java HTTP 端点，疑似解析或范围故障");
  const byKey = new Map();
  for (const endpoint of endpoints) {
    if (byKey.has(endpoint.key)) {
      errors.push(`重复端点 ${endpoint.key}: ${byKey.get(endpoint.key).source} 与 ${endpoint.source}`);
    } else {
      byKey.set(endpoint.key, endpoint);
    }
  }
  endpoints.sort((a, b) => a.key.localeCompare(b.key));
  return { files: files.length, endpoints, errors };
}

function defaultRoot() {
  return path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
}

function defaultBaseline() {
  return path.join(path.dirname(fileURLToPath(import.meta.url)), "resource-permission-baseline.json");
}

function loadBaseline(file) {
  if (!fs.existsSync(file)) throw new Error(`baseline 不存在: ${file}；首次生成须显式执行 --write-baseline`);
  const baseline = JSON.parse(fs.readFileSync(file, "utf8"));
  if (baseline.schemaVersion !== SCANNER_VERSION) throw new Error(`baseline schemaVersion 不兼容: ${baseline.schemaVersion}`);
  if (!Array.isArray(baseline.endpoints)) throw new Error("baseline.endpoints 必须是数组");
  const keys = new Set();
  for (const endpoint of baseline.endpoints) {
    if (!HTTP_METHODS.has(endpoint.method) && endpoint.method !== "*") throw new Error(`baseline HTTP 方法非法: ${endpoint.method}`);
    if (typeof endpoint.path !== "string" || !endpoint.path.startsWith("/")) throw new Error("baseline 路径非法");
    const expected = endpointKey(endpoint.method, endpoint.path);
    if (endpoint.key !== expected) throw new Error(`baseline key 与 method/path 不一致: ${endpoint.key}`);
    if (keys.has(expected)) throw new Error(`baseline 含重复 key: ${expected}`);
    keys.add(expected);
  }
  if (baseline.endpointCount !== baseline.endpoints.length) throw new Error("baseline.endpointCount 与 endpoints 数量不一致");
  return baseline;
}

function evaluate(root, baselineFile) {
  const baseline = loadBaseline(baselineFile);
  const scan = scanJava(root);
  const errors = [...scan.errors];
  const baselineKeys = new Set(baseline.endpoints.map((endpoint) => endpoint.key));
  const currentKeys = new Set(scan.endpoints.map((endpoint) => endpoint.key));
  const newDeclared = [];
  const newUndeclared = [];
  for (const endpoint of scan.endpoints) {
    if (baselineKeys.has(endpoint.key)) continue;
    if (endpoint.declaration.length > 0) newDeclared.push(endpoint);
    else newUndeclared.push(endpoint);
  }
  for (const endpoint of newUndeclared) {
    errors.push(`新增端点缺少显式权限声明: ${endpoint.key} (${endpoint.source}:${endpoint.line})；请添加 @ResourcePermission 或等价声明`);
  }
  const stale = baseline.endpoints.filter((endpoint) => !currentKeys.has(endpoint.key));
  return {
    ok: errors.length === 0,
    errors,
    warnings: stale.map((endpoint) => `baseline 端点已不存在: ${endpoint.key} (${endpoint.source})`),
    summary: {
      files: scan.files,
      current: scan.endpoints.length,
      baseline: baseline.endpoints.length,
      grandfathered: scan.endpoints.length - newDeclared.length - newUndeclared.length,
      newDeclared: newDeclared.length,
      newUndeclared: newUndeclared.length,
      stale: stale.length,
    },
    newDeclared,
    newUndeclared,
  };
}

function writeBaseline(root, baselineFile, force) {
  if (fs.existsSync(baselineFile) && !force) {
    throw new Error(`baseline 已存在: ${baselineFile}；如确需更新，请人工审查后显式加 --force`);
  }
  const scan = scanJava(root);
  if (scan.errors.length > 0) throw new Error(`扫描失败，拒绝写 baseline:\n${scan.errors.join("\n")}`);
  const baseline = {
    schemaVersion: SCANNER_VERSION,
    generatedAt: new Date().toISOString(),
    identity: "HTTP method + normalized path",
    scope: "wms-java/**/src/main/java/**/*.java (excluding outbound @FeignClient)",
    grandfathered: true,
    note: "仅豁免 2026-11-26 扫描时已存在的 Java 端点；不得用自动更新掩盖新增权限债。",
    filesScanned: scan.files,
    endpointCount: scan.endpoints.length,
    endpoints: scan.endpoints.map((endpoint) => ({
      key: endpoint.key,
      method: endpoint.method,
      path: endpoint.path,
      source: endpoint.source,
      line: endpoint.line,
      typeName: endpoint.typeName,
      methodName: endpoint.methodName,
    })),
  };
  fs.mkdirSync(path.dirname(baselineFile), { recursive: true });
  fs.writeFileSync(baselineFile, `${JSON.stringify(baseline, null, 2)}\n`, "utf8");
  return baseline;
}

function makeFixture(files) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "wms-resource-permission-"));
  for (const [relative, source] of Object.entries(files)) {
    const full = path.join(root, relative);
    fs.mkdirSync(path.dirname(full), { recursive: true });
    fs.writeFileSync(full, source, "utf8");
  }
  return root;
}

function baselineFixture(root, endpoints) {
  const file = path.join(root, "baseline.json");
  const normalized = endpoints.map((endpoint) => {
    const item = typeof endpoint === "string"
      ? { method: endpoint.split(" ")[0], path: endpoint.slice(endpoint.indexOf(" ") + 1) }
      : endpoint;
    return { ...item, key: endpointKey(item.method, item.path), source: "fixture", line: 1 };
  });
  fs.writeFileSync(file, JSON.stringify({
    schemaVersion: SCANNER_VERSION, endpointCount: normalized.length, endpoints: normalized,
  }), "utf8");
  return file;
}

const controllerPath = "wms-java/demo/src/main/java/com/example/DemoController.java";
const baseController = `package com.example;
@RestController
@RequestMapping("/demo")
public class DemoController {
  @GetMapping("/list") public String list() { return "ok"; }
}
`;
const addMethods = (...methods) => baseController.replace(/\n}\n$/, `\n${methods.join("\n")}\n}\n`);

function selfTest() {
  const tests = [];
  const test = (name, fn) => tests.push({ name, fn });
  const withFixture = (files, fn) => {
    const root = makeFixture(files);
    try { fn(root); } finally { fs.rmSync(root, { recursive: true, force: true }); }
  };

  test("baseline 豁免存量未声明端点", () => withFixture({ [controllerPath]: baseController }, (root) => {
    assert.equal(evaluate(root, baselineFixture(root, ["GET /demo/list"])).ok, true);
  }));

  test("baseline 之外新增未声明端点失败", () => withFixture({
    [controllerPath]: addMethods(`  @PostMapping("/add") public String add() { return "ok"; }`),
  }, (root) => {
    const result = evaluate(root, baselineFixture(root, ["GET /demo/list"]));
    assert.equal(result.ok, false);
    assert.match(result.errors.join("\n"), /POST \/demo\/add/);
  }));

  test("类级 @ResourcePermission 覆盖新端点", () => withFixture({
    [controllerPath]: addMethods(`  @PostMapping("/add") public String add() { return "ok"; }`)
      .replace("@RestController", "@RestController\n@ResourcePermission(roles = {\"cg\", \"ckjl\"})"),
  }, (root) => {
    const result = evaluate(root, baselineFixture(root, ["GET /demo/list"]));
    assert.equal(result.ok, true, JSON.stringify(result.errors));
    assert.equal(result.summary.newDeclared, 1);
  }));

  test("方法级 allowPublic 覆盖类级声明", () => withFixture({
    [controllerPath]: addMethods(`  @GetMapping("/health") @ResourcePermission(allowPublic = true) public String health() { return "ok"; }`)
      .replace("@RestController", "@RestController\n@ResourcePermission(roles = {\"cg\"})"),
  }, (root) => {
    assert.equal(evaluate(root, baselineFixture(root, ["GET /demo/list"])).ok, true);
  }));

  test("空声明、角色与 public 冲突均失败", () => {
    for (const declaration of ["@ResourcePermission", "@ResourcePermission(roles = {\"cg\"}, allowPublic = true)"]) {
      withFixture({ [controllerPath]: addMethods(`  @PostMapping("/add") ${declaration} public String add() { return "ok"; }`) }, (root) => {
        assert.equal(evaluate(root, baselineFixture(root, ["GET /demo/list"])).ok, false);
      });
    }
  });

  test("等价 Spring Security 显式声明可通过", () => {
    for (const declaration of [
      "@PreAuthorize(\"hasRole('cg')\")", "@Secured({\"ROLE_cg\"})", "@RolesAllowed(\"ROLE_cg\")", "@PermitAll", "@DenyAll", "@ResourcePermission(\"cg\")",
    ]) {
      withFixture({ [controllerPath]: addMethods(`  @PostMapping("/add") ${declaration} public String add() { return "ok"; }`) }, (root) => {
        assert.equal(evaluate(root, baselineFixture(root, ["GET /demo/list"])).ok, true, declaration);
      });
    }
  });

  test("注释和字符串中的假映射不会成端点", () => withFixture({
    [controllerPath]: baseController.replace(/\n}\n$/, `\n// @GetMapping("/fake")\n/* @PostMapping("/fake2") */\nString text = "@DeleteMapping(\\\"/fake3\\\")";\n}\n`),
  }, (root) => {
    const result = evaluate(root, baselineFixture(root, ["GET /demo/list"]));
    assert.equal(result.ok, true);
    assert.equal(result.summary.current, 1);
  }));

  test("支持 value/path 数组、RequestMethod 数组与路径规范化", () => withFixture({
    [controllerPath]: `package com.example;
@RestController
@RequestMapping({"/demo/", "/v2/demo"})
public class DemoController {
  @RequestMapping(path = {"/list", "detail/{id}"}, method = {RequestMethod.GET, RequestMethod.POST})
  public String list() { return "ok"; }
}
`,
  }, (root) => {
    const baseline = baselineFixture(root, [
      "GET /demo/list", "POST /demo/list", "GET /demo/detail/{id}", "POST /demo/detail/{id}",
      "GET /v2/demo/list", "POST /v2/demo/list", "GET /v2/demo/detail/{id}", "POST /v2/demo/detail/{id}",
    ]);
    const result = evaluate(root, baseline);
    assert.equal(result.ok, true);
    assert.equal(result.summary.current, 8);
  }));

  test("非字面量路径失败关闭", () => withFixture({
    [controllerPath]: `package com.example;
@RestController
public class DemoController {
  private static final String BASE = "/demo";
  @GetMapping(BASE + "/list") public String list() { return "ok"; }
}
`,
  }, (root) => {
    assert.equal(evaluate(root, baselineFixture(root, [])).ok, false);
  }));

  test("出站 Feign 映射不计入网关端点", () => withFixture({
    [controllerPath]: baseController,
    "wms-java/demo/src/main/java/com/example/RemoteClient.java": `package com.example;
@FeignClient(name = "remote")
public interface RemoteClient { @PostMapping("/remote/push") void push(); }
`,
  }, (root) => {
    const result = evaluate(root, baselineFixture(root, ["GET /demo/list"]));
    assert.equal(result.ok, true);
    assert.equal(result.summary.current, 1);
  }));

  test("API 接口上的入站 HTTP 映射纳入扫描", () => withFixture({
    "wms-java/demo/src/main/java/com/example/DemoApis.java": `package com.example;
public interface DemoApis { @GetMapping("/api/list") String list(); }
`,
  }, (root) => {
    assert.equal(evaluate(root, baselineFixture(root, ["GET /api/list"])).ok, true);
  }));

  test("重复 HTTP 方法 + 路径失败", () => withFixture({
    [controllerPath]: baseController,
    "wms-java/demo/src/main/java/com/example/DuplicateController.java": `package com.example;
@RestController public class DuplicateController { @GetMapping("/demo/list") public String list() { return "ok"; } }
`,
  }, (root) => {
    assert.equal(evaluate(root, baselineFixture(root, ["GET /demo/list"])).ok, false);
  }));

  test("baseline 缺失失败", () => withFixture({ [controllerPath]: baseController }, (root) => {
    assert.throws(() => evaluate(root, path.join(root, "missing.json")), /baseline 不存在/);
  }));

  test("删除的存量端点只告警，不阻断", () => withFixture({ [controllerPath]: baseController }, (root) => {
    const result = evaluate(root, baselineFixture(root, ["GET /demo/list", "GET /demo/old"]));
    assert.equal(result.ok, true);
    assert.equal(result.summary.stale, 1);
  }));

  let passed = 0;
  for (const { name, fn } of tests) {
    try {
      fn();
      console.log(`[PASS] ${name}`);
      passed += 1;
    } catch (error) {
      console.error(`[FAIL] ${name}`);
      throw error;
    }
  }
  console.log(`[PASS] resource-permission self-test: ${passed}/${tests.length}`);
}

function printResult(result) {
  for (const warning of result.warnings) console.warn(`[WARN] ${warning}`);
  const summary = result.summary;
  console.log(`[INFO] Java files=${summary.files}, endpoints=${summary.current}, baseline=${summary.baseline}, `
    + `grandfathered=${summary.grandfathered}, newDeclared=${summary.newDeclared}, newUndeclared=${summary.newUndeclared}, stale=${summary.stale}`);
  if (!result.ok) {
    for (const error of result.errors) console.error(`[FAIL] ${error}`);
    process.exitCode = 1;
    return;
  }
  console.log("[PASS] baseline 之外的新端点均有显式权限声明");
}

try {
  const options = parseArgs(process.argv.slice(2));
  if (options.mode === "help") {
    console.log("用法: check-resource-permissions.mjs [--check|--self-test|--write-baseline [--force]] [--root DIR] [--baseline FILE]");
  } else if (options.mode === "self-test") {
    selfTest();
  } else {
    const root = options.root || defaultRoot();
    const baseline = options.baseline || defaultBaseline();
    if (options.mode === "write-baseline") {
      const written = writeBaseline(root, baseline, options.force);
      console.log(`[PASS] baseline 已写入: ${baseline} (${written.endpointCount} endpoints)`);
    } else {
      printResult(evaluate(root, baseline));
    }
  }
} catch (error) {
  console.error(`[FAIL] ${error.message}`);
  process.exitCode = 1;
}
