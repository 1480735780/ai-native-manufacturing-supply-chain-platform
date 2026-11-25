#!/usr/bin/env bash
# zero-one-10wms harness 入口：环境检查、状态检查、C++ 静态检查、按需构建。
# 运行环境：Git Bash / Linux / macOS。Windows PowerShell 不能直接执行本脚本。

set -u
set -o pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_ROOT="$(cd "$ROOT/.." && pwd)"
cd "$ROOT" || exit 1

MODE="quick"
JAVA_MODULE=""
DO_SNAPSHOT=0
DO_CPP=0
DO_FRONTEND=0
DO_JAVA=0
DO_AGENT=0
DO_JAVA_TEST=0
FAILED=0

usage() {
	cat <<'EOF'
用法: ./init.sh [选项]

默认: --quick 环境/状态/基线/关键文件检查

  --quick            快速检查（默认）
  --verify           完整静态验证：Java 编译 + 前端构建 + C++ 静态检查
  --snapshot         追加一条开工基线快照到 $WMS_STATE_DIR
  --java [模块]      编译 Java；不带模块时编译整个 reactor
  --frontend         前端构建（corepack pnpm build）
  --cpp              C++ 静态检查（模块注册、词条重复键）
  --agent            问数 Agent（wms-agent）依赖同步 + pytest
  --java-test        巡检前置 Java 测试（wms-login / wms-j3-daycheck / wms-oauth2 跑 test）
  --help             显示帮助

环境变量:
  WMS_STATE_DIR      状态目录，默认 $PARENT_ROOT/.wms-harness-state（已忽略）
  WMS_AGENT_PYTHON   问数 Agent 使用的解释器（路径或版本，如 3.14）；缺省由 uv 自行选择
  WMS_AGENT_STORE_BACKEND / WMS_AGENT_DB_URL
                      trace 持久化配置，默认在 wms-agent/.env 中为 postgres（库 ragent）；
                      无 PG 环境可改回 memory 降级（persisted=false）。密钥与连接串只在
                      .env（gitignore 排除），.env.example 为非密模板。

说明:
  - 本机无 C++ 编译器时只做静态检查，不把结果写成“通过”。
  - --verify 会跑较慢的编译/构建；失败时按输出修复，不要跳过。
  - --agent 需要 uv；依赖缓存写在 wms-agent/.uv/cache，不污染用户目录。
EOF
}

say() { printf '[init] %s\n' "$*"; }
ok() { printf '[PASS] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*"; }
skip() { printf '[SKIP] %s\n' "$*"; }
fail() {
	printf '[FAIL] %s\n' "$*" >&2
	FAILED=$((FAILED + 1))
}

have() { command -v "$1" >/dev/null 2>&1; }

while [ "$#" -gt 0 ]; do
	case "$1" in
		--quick)
			MODE="quick"
			;;
		--verify | --full)
			MODE="verify"
			DO_JAVA=1
			DO_FRONTEND=1
			DO_CPP=1
			;;
		--snapshot)
			DO_SNAPSHOT=1
			;;
		--cpp)
			DO_CPP=1
			;;
		--agent)
			DO_AGENT=1
			;;
		--java-test)
			DO_JAVA_TEST=1
			;;
		--frontend)
			DO_FRONTEND=1
			;;
		--java)
			DO_JAVA=1
			if [ "$#" -ge 2 ] && [ "${2#--}" = "$2" ]; then
				JAVA_MODULE="$2"
				shift
			fi
			;;
		--help | -h)
			usage
			exit 0
			;;
		*)
			printf '未知参数: %s\n' "$1" >&2
			usage
			exit 2
			;;
	esac
	shift
done

check_tools() {
	say "检查工具链"

	if have git; then
		ok "git: $(git --version 2>/dev/null | head -n 1)"
	else
		fail "缺少 git"
	fi

	if have java; then
		ok "java: $(java -version 2>&1 | head -n 1)"
	else
		warn "缺少 java；Java 编译不可用"
	fi

	if have mvn; then
		ok "mvn: $(mvn -v 2>/dev/null | head -n 1)"
	else
		warn "缺少 mvn；Java 编译不可用"
	fi

	if have node; then
		ok "node: $(node -v 2>/dev/null)"
	else
		warn "缺少 node；前端构建不可用"
	fi

	if have corepack; then
		ok "corepack: $(corepack -v 2>/dev/null)"
	elif have pnpm; then
		ok "pnpm: $(pnpm -v 2>/dev/null)"
	else
		warn "缺少 corepack/pnpm；前端构建不可用"
	fi

	if have python; then
		ok "python: $(python --version 2>&1 | head -n 1)"
	elif have py; then
		ok "python: $(py --version 2>&1 | head -n 1)"
	else
		warn "缺少 python；JSON/词条静态检查会跳过"
	fi

	if have cmake; then
		ok "cmake: $(cmake --version 2>/dev/null | head -n 1)"
	else
		warn "缺少 cmake；C++ 只做静态检查，结果记 runtime_unverified"
	fi
}

check_key_files() {
	say "检查关键文件"

	local files=(
		"$PARENT_ROOT/AGENTS.md"
		"$ROOT/AGENTS.md"
		"$ROOT/architecture.md"
		"$ROOT/process.md"
		"$ROOT/feature_list.json"
		"$ROOT/PROGRESS.md"
		"$ROOT/wms-java/pom.xml"
		"$ROOT/wms-frontend/package.json"
		"$ROOT/wms-cpp/CMakeLists.txt"
	)
	local f
	for f in "${files[@]}"; do
		if [ -f "$f" ]; then
			ok "存在: ${f#"$PARENT_ROOT/"}"
		else
			fail "缺少关键文件: ${f#"$PARENT_ROOT/"}"
		fi
	done
}

check_json() {
	say "检查 feature_list.json"

	if [ ! -f "$ROOT/feature_list.json" ]; then
		fail "feature_list.json 不存在"
		return
	fi

	if have python; then
		if python -c 'import json,sys; json.load(open(sys.argv[1], encoding="utf-8"))' "$ROOT/feature_list.json"; then
			ok "feature_list.json 是合法 JSON"
			return
		fi
		# Windows 上 PATH 上的 python 可能是 Microsoft Store 存根，失败时改用其它解释器
	fi
	if have py; then
		if py -3 -c 'import json,sys; json.load(open(sys.argv[1], encoding="utf-8"))' "$ROOT/feature_list.json"; then
			ok "feature_list.json 是合法 JSON"
			return
		fi
	fi
	if have node; then
		if node -e 'JSON.parse(require("fs").readFileSync(process.argv[1],"utf8"))' "$ROOT/feature_list.json"; then
			ok "feature_list.json 是合法 JSON"
			return
		fi
	fi
	fail "feature_list.json 不是合法 JSON"
}

check_git() {
	say "检查 Git 基线"

	if ! have git; then
		fail "缺少 git，无法检查基线"
		return
	fi

	if ! git -C "$PARENT_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
		fail "父仓库不是 Git 工作区: $PARENT_ROOT"
		return
	fi

	path_mode="$(git -C "$PARENT_ROOT" ls-tree HEAD zero-one-10wms 2>/dev/null | awk '{print $1}')"
	if [ "$path_mode" != "040000" ]; then
		fail "zero-one-10wms 不是单仓普通目录树（mode=${path_mode:-missing}）；结构性漂移，先报告不自动修复"
		return
	fi

	local parent_branch parent_head
	parent_branch="$(git -C "$PARENT_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null)"
	parent_head="$(git -C "$PARENT_ROOT" rev-parse HEAD 2>/dev/null)"

	ok "单仓模式: $parent_branch @ ${parent_head:0:7}；zero-one-10wms 为普通目录树"

	local parent_dirty
	parent_dirty="$(git -C "$PARENT_ROOT" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
	ok "仓库脏改动: $parent_dirty 项"
}

run_frontend_pm() {
	if have corepack; then
		corepack pnpm "$@"
	elif have pnpm; then
		pnpm "$@"
	elif have npm; then
		npm "$@"
	else
		return 127
	fi
}

check_frontend() {
	say "检查前端"

	if [ ! -f "$ROOT/wms-frontend/package.json" ]; then
		fail "wms-frontend/package.json 不存在"
		return
	fi

	if [ ! -d "$ROOT/wms-frontend/node_modules" ]; then
		if [ "$MODE" = "verify" ]; then
			say "node_modules 不存在，尝试安装依赖"
			if ! (cd "$ROOT/wms-frontend" && run_frontend_pm install --frozen-lockfile); then
				fail "前端依赖安装失败"
				return
			fi
		else
			warn "node_modules 不存在；跳过前端构建"
			return
		fi
	fi

	if [ ! -e "$ROOT/wms-frontend/node_modules/.bin/vite" ] && [ ! -e "$ROOT/wms-frontend/node_modules/.bin/vite.cmd" ]; then
		warn "未找到 vite 可执行文件；跳过前端构建"
		return
	fi

	say "执行前端生产构建（vite build --mode production）"
	if (cd "$ROOT/wms-frontend" && run_frontend_pm build); then
		ok "前端生产构建通过"
	else
		fail "前端生产构建失败"
	fi
}

check_java() {
	say "检查 Java"

	if ! have mvn; then
		fail "缺少 mvn，无法编译 Java"
		return
	fi

	if [ -n "$JAVA_MODULE" ]; then
		say "编译模块: $JAVA_MODULE"
		if (cd "$ROOT/wms-java" && mvn -o -q -pl "$JAVA_MODULE" -am compile -DskipTests); then
			ok "Java 模块编译通过: $JAVA_MODULE"
		else
			fail "Java 模块编译失败: $JAVA_MODULE"
		fi
	else
		say "编译整个 wms-java reactor（离线模式）"
		if (cd "$ROOT/wms-java" && mvn -o -q -DskipTests compile); then
			ok "Java reactor 编译通过"
		else
			fail "Java reactor 编译失败"
		fi
	fi
}

check_java_test() {
	say "运行巡检前置 Java 测试（mvn test）"

	if ! have mvn; then
		fail "缺少 mvn，无法运行 Java 测试"
		return
	fi

	local modules="wms-login,wms-j3-daycheck,wms-oauth2,wms-j1-dashboard"
	# 只跑新增的巡检前置测试类：
	# - 既有 test.java / test2.java 是 @SpringBootTest 手工联调用例，依赖 Nacos/MySQL，不属于 harness 门禁；
	# - wms-oauth2 仅编译其在 reactor 中的产物，不在本门禁内启动上下文；
	# - wms-j1-dashboard 的 PendSnapshot*Test 覆盖阶段3 一致快照端点（契约 + 资源角色种子）。
	local test_filter="AgentServiceTokenTest,DaycheckSortContractTest,NoUpMapperXmlTest,NoUpPageContractTest,NoUpPageServiceTest,NoUpPageResourceRoleSeedTest,DelayServiceSortTest,DelayControllerSortTest,PendSnapshotContractTest,PendSnapshotResourceRoleSeedTest"
	if (cd "$ROOT/wms-java" && mvn -o -pl "$modules" -am test -DskipTests=false \
		-Dtest="$test_filter" -Dsurefire.failIfNoSpecifiedTests=false); then
		ok "巡检前置 Java 测试执行完成"
	else
		fail "巡检前置 Java 测试失败"
		return
	fi

	# 必须确认每个门禁测试类都真的被执行，不能出现「0 tests 也 PASS」或某个类被静默跳过
	local report
	local found
	local missing=0
	for report in \
		"$ROOT/wms-java/wms-login/target/surefire-reports/"*AgentServiceTokenTest.txt \
		"$ROOT/wms-java/wms-j3-daycheck/target/surefire-reports/"*DelayServiceSortTest.txt \
		"$ROOT/wms-java/wms-j3-daycheck/target/surefire-reports/"*DelayControllerSortTest.txt \
		"$ROOT/wms-java/wms-j3-daycheck/target/surefire-reports/"*DaycheckSortContractTest.txt \
		"$ROOT/wms-java/wms-j3-daycheck/target/surefire-reports/"*NoUpMapperXmlTest.txt \
		"$ROOT/wms-java/wms-j3-daycheck/target/surefire-reports/"*NoUpPageContractTest.txt \
		"$ROOT/wms-java/wms-j3-daycheck/target/surefire-reports/"*NoUpPageServiceTest.txt \
		"$ROOT/wms-java/wms-j3-daycheck/target/surefire-reports/"*NoUpPageResourceRoleSeedTest.txt \
		"$ROOT/wms-java/wms-j1-dashboard/target/surefire-reports/"*PendSnapshotContractTest.txt \
		"$ROOT/wms-java/wms-j1-dashboard/target/surefire-reports/"*PendSnapshotResourceRoleSeedTest.txt; do
		# shellcheck disable=SC2086
		found=$(ls $report 2>/dev/null | head -n 1)
		if [ -z "$found" ]; then
			warn "缺少 surefire 报告: $report"
			missing=1
			continue
		fi
		if ! grep -Eq "Tests run: [1-9][0-9]*" "$found"; then
			warn "surefire 报告为 0 tests: $found"
			missing=1
		fi
	done
	if [ "$missing" = 0 ]; then
		ok "已确认巡检前置 10 个 Java 测试类全部实际执行（surefire 报告非 0 tests）"
	else
		fail "巡检前置 Java 测试执行记录不完整（surefire 报告缺失或 0 tests）"
	fi
}

check_cpp() {
	say "检查 C++ 静态一致性"

	local module_dir base
	for module_dir in "$ROOT"/wms-cpp/wms-c*; do
		[ -d "$module_dir" ] || continue
		base="${module_dir##*/}"
		if [ ! -f "$module_dir/CMakeLists.txt" ]; then
			fail "$base 缺少 CMakeLists.txt"
		fi
		if ! grep -Fq "add_subdirectory (\"$base\")" "$ROOT/wms-cpp/CMakeLists.txt"; then
			fail "$base 未注册到 wms-cpp/CMakeLists.txt"
		fi
	done
	ok "C++ 模块目录与 CMake 注册检查完成"

	local yaml_file
	while IFS= read -r -d '' yaml_file; do
		if have python; then
			if python - "$yaml_file" <<'PY'
import sys
from collections import Counter

path = sys.argv[1]
keys = []
with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
    for line in fh:
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-") or stripped.startswith("---"):
            continue
        if line[:1].isspace() or ":" not in line:
            continue
        key = line.split(":", 1)[0].strip().strip("\"'")
        if key:
            keys.append(key)

duplicates = sorted(k for k, count in Counter(keys).items() if count > 1)
if duplicates:
    print("重复顶层键: " + ", ".join(duplicates))
    sys.exit(1)
PY
			then
				ok "无重复顶层键: ${yaml_file#"$ROOT/"}"
			else
				fail "存在重复顶层键: ${yaml_file#"$ROOT/"}"
			fi
		else
			skip "没有 python，跳过词条重复键检查: ${yaml_file#"$ROOT/"}"
		fi
	done < <(find "$ROOT/wms-cpp" -maxdepth 2 -type f -name 'zh-dict.yaml' -print0 2>/dev/null)

	if ! have cmake; then
		warn "本机无 cmake；C++ 结果只能记 static_pass + runtime_unverified"
	fi
}

check_agent() {
	say "检查问数 Agent（wms-agent）"

	local agent_dir="$ROOT/wms-agent"
	if [ ! -d "$agent_dir" ]; then
		fail "缺少 wms-agent 目录"
		return
	fi

	local f
	for f in pyproject.toml config/scan.yaml app/main.py app/agent/react.py app/tools/registry.py app/storage/store.py app/scan/config.py app/scan/worker.py; do
		if [ -f "$agent_dir/$f" ]; then
			ok "存在: wms-agent/$f"
		else
			fail "缺少 wms-agent/$f"
		fi
	done

	local gateway_yaml="$ROOT/wms-java/wms-gateway/src/main/resources/application.yaml"
	if [ -f "$gateway_yaml" ] && grep -Fq "agent-route" "$gateway_yaml"; then
		ok "网关已配置 agent-route"
	else
		fail "网关 application.yaml 缺少 agent-route"
	fi

	local nacos_yaml="$ROOT/nacos-config/system.yaml"
	if [ -f "$nacos_yaml" ] && grep -Fq "agent:" "$nacos_yaml"; then
		ok "nacos-config/system.yaml 含 agent 端口配置"
	else
		fail "nacos-config/system.yaml 缺少 agent 端口配置"
	fi

	# 持久化配置模板应默认 postgres（实际连接串/口令只在本地 .env）
	local env_example="$agent_dir/.env.example"
	if [ -f "$env_example" ] && grep -Fq "WMS_AGENT_STORE_BACKEND=postgres" "$env_example"; then
		ok ".env.example 默认 postgres 持久化"
	else
		warn ".env.example 未默认 postgres 持久化（允许无 PG 环境改 memory 降级）"
	fi

	if ! have uv; then
		fail "缺少 uv；问数 Agent 无法同步依赖或运行测试"
		return
	fi
	ok "uv: $(uv --version 2>/dev/null | head -n 1)"

	local py_args=()
	if [ -n "${WMS_AGENT_PYTHON:-}" ]; then
		py_args=(--python "$WMS_AGENT_PYTHON")
	fi

	say "同步问数 Agent 依赖（uv sync）"
	if (cd "$agent_dir" && UV_CACHE_DIR="$agent_dir/.uv/cache" uv sync "${py_args[@]+"${py_args[@]}"}"); then
		ok "wms-agent 依赖同步完成"
	else
		fail "uv sync 失败"
		return
	fi

	say "运行问数 Agent 测试（uv run pytest）"
	if (cd "$agent_dir" && UV_CACHE_DIR="$agent_dir/.uv/cache" uv run "${py_args[@]+"${py_args[@]}"}" pytest); then
		ok "wms-agent 测试通过"
	else
		fail "wms-agent 测试失败"
	fi
}

hash_file() {
	local file="$1"
	if [ -f "$file" ] && have sha256sum; then
		sha256sum "$file" | awk '{print $1}'
	else
		printf 'unavailable'
	fi
}

write_snapshot() {
	say "写入开工基线快照"

	local state_dir="${WMS_STATE_DIR:-$PARENT_ROOT/.wms-harness-state}"
	local history="$state_dir/history.jsonl"
	mkdir -p "$state_dir" 2>/dev/null || {
		fail "无法创建状态目录: $state_dir"
		return
	}

	local ts parent_branch parent_head dirty_total prev_hash body hash
	ts="$(date -Iseconds 2>/dev/null || date)"
	parent_branch="$(git -C "$PARENT_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null)"
	parent_head="$(git -C "$PARENT_ROOT" rev-parse HEAD 2>/dev/null)"
	dirty_total="$(git -C "$PARENT_ROOT" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
	prev_hash=""
	if [ -f "$history" ]; then
		prev_hash="$(tail -n 1 "$history" 2>/dev/null | sed -n 's/.*"hash":"\([^"]*\)".*/\1/p')"
	fi

	body="$(printf '{"ts":"%s","event":"session_start","repository":{"branch":"%s","head":"%s","layout":"single-repo"},"dirty":{"total":%s},"files":{"AGENTS.md":"%s","process.md":"%s","architecture.md":"%s","feature_list.json":"%s","PROGRESS.md":"%s"},"prev_hash":"%s"' \
		"$ts" "$parent_branch" "$parent_head" \
		"$dirty_total" \
		"$(hash_file "$ROOT/AGENTS.md")" \
		"$(hash_file "$ROOT/process.md")" \
		"$(hash_file "$ROOT/architecture.md")" \
		"$(hash_file "$ROOT/feature_list.json")" \
		"$(hash_file "$ROOT/PROGRESS.md")" \
		"$prev_hash")"

	if have sha256sum; then
		hash="$(printf '%s' "$body" | sha256sum | awk '{print $1}')"
	else
		hash="unavailable"
	fi

	printf '%s,"hash":"%s"}\n' "$body" "$hash" >>"$history"
	ok "快照已追加: $history"
}

say "root: $ROOT"
check_tools
check_key_files
check_json
check_git

if [ "$DO_CPP" = 1 ]; then
	check_cpp
fi

if [ "$DO_JAVA" = 1 ]; then
	check_java
fi

if [ "$DO_FRONTEND" = 1 ]; then
	check_frontend
fi

if [ "$DO_AGENT" = 1 ]; then
	check_agent
fi

if [ "$DO_JAVA_TEST" = 1 ]; then
	check_java_test
fi

if [ "$DO_SNAPSHOT" = 1 ]; then
	write_snapshot
fi

echo
if [ "$FAILED" -eq 0 ]; then
	printf '结果: PASS\n'
	exit 0
else
	printf '结果: FAIL (%s 项)\n' "$FAILED" >&2
	exit 1
fi
