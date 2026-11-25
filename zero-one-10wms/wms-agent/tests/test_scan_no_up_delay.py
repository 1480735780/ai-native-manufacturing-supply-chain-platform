"""F-015 v0.2.0 第二轮：no_up / delay 规则、数据源与编排集成测试。

不依赖 PG/Nacos/真实网络；规则分级确定性，mock gateway + 固定输入回放。
覆盖：分级阈值边界、未来时间/解析失败跳过、司机信息脱敏、source 去重与
5xx 重试/4xx 不重试、service 编排多类型合并与 skippedTypes。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import pytest

from app.scan.repository import MemoryScanStore
from app.scan.rules.base import RuleContext
from app.scan.rules.delay import evaluate_delay
from app.scan.rules.no_up import evaluate_no_up
from app.scan.service import DEFAULT_CONFIG, SUPPORTED_TYPES, run_scan
from app.scan.sources.delay import fetch_delay
from app.scan.sources.no_up import fetch_no_up
from app.security import Principal
from app.tools.gateway_client import GatewayClient

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)
TOKEN = "header.payload.signature"
NOUP_PATH = "/daycheck/no-up/get-no-up-goods-page"
DELAY_PATH = "/daycheck/delay/im-delay"


def _ctx() -> RuleContext:
    return RuleContext(warehouse="W01", now=NOW)


def _minutes_ago(minutes: float) -> str:
    return (NOW - timedelta(minutes=minutes)).isoformat()


def _user() -> Principal:
    return Principal(user_id="u-1", user_name="tester", authorities=["insp_read"])


# ---------- no_up rule ----------

def _no_up_row(**overrides: Any) -> dict[str, Any]:
    row = {
        "rowId": "R1", "noticeId": "N1", "goods_id": "G1", "bin_id": "B1",
        "tin_id": "T1", "cus_code": "C1", "shp_ming_cheng": "小蓝管",
        "create_date": _minutes_ago(500),
    }
    row.update(overrides)
    return row


def test_no_up_p0_over_8h() -> None:
    out = evaluate_no_up([_no_up_row(create_date=_minutes_ago(9 * 60))], _ctx())
    assert len(out) == 1
    assert out[0].rule_id == "NOUP-OVERDUE" and out[0].severity == "P0"
    assert out[0].object_type == "no_up_goods"
    assert out[0].suggested_actions == ("MOVE_TO_BIN", "CONTACT_CUSTOMER")
    assert out[0].rule_params == {"p0Hours": 8, "p1Hours": 4, "p2Hours": 2}


def test_no_up_p1_between_4_and_8h() -> None:
    out = evaluate_no_up([_no_up_row(create_date=_minutes_ago(6 * 60))], _ctx())
    assert len(out) == 1 and out[0].severity == "P1"


def test_no_up_p2_between_2_and_4h() -> None:
    out = evaluate_no_up([_no_up_row(create_date=_minutes_ago(3 * 60))], _ctx())
    assert len(out) == 1 and out[0].severity == "P2"


def test_no_up_skips_below_2h_and_future_and_bad_date() -> None:
    rows = [
        _no_up_row(rowId="R1", create_date=_minutes_ago(30)),
        _no_up_row(rowId="R2", create_date=(NOW + timedelta(hours=1)).isoformat()),
        _no_up_row(rowId="R3", create_date="not-a-date"),
    ]
    assert evaluate_no_up(rows, _ctx()) == []


def test_no_up_boundaries_exact() -> None:
    # 恰好 8h 不触发 P0（条件严格 >），恰好 4h 落在 P1，恰好 2h 落在 P2
    assert evaluate_no_up([_no_up_row(create_date=_minutes_ago(8 * 60))], _ctx())[0].severity == "P1"
    assert evaluate_no_up([_no_up_row(create_date=_minutes_ago(4 * 60))], _ctx())[0].severity == "P2"
    assert evaluate_no_up([_no_up_row(create_date=_minutes_ago(2 * 60))], _ctx()) == []


def test_no_up_object_id_excludes_bin() -> None:
    finding = evaluate_no_up(
        [_no_up_row(noticeId="N9", goods_id="G9", tin_id="T9", bin_id="B9",
                    create_date=_minutes_ago(500))], _ctx()
    )[0]
    assert finding.object_id == "N9|G9|T9"
    assert "B9" not in finding.object_id


# ---------- delay rule ----------

def _delay_row(**overrides: Any) -> dict[str, Any]:
    row = {
        "noticeId": "D1", "supName": "供应商甲",
        "imData": _minutes_ago(25 * 60), "imSta": "待到货",
        "imCarDri": "张三", "imCarMobile": "13800138000", "imCarNo": "沪A12345",
    }
    row.update(overrides)
    return row


def test_delay_p0_over_24h() -> None:
    out = evaluate_delay([_delay_row()], _ctx())
    assert len(out) == 1
    assert out[0].rule_id == "DELAY-OVERDUE" and out[0].severity == "P0"
    assert out[0].object_type == "delivery_notice"
    assert out[0].suggested_actions == ("CONTACT_CUSTOMER", "NOTIFY_QC")
    assert out[0].evidence["delayHours"] >= 24


def test_delay_p1_between_2_and_24h() -> None:
    out = evaluate_delay([_delay_row(imData=_minutes_ago(5 * 60))], _ctx())
    assert len(out) == 1 and out[0].severity == "P1"


def test_delay_p2_between_0_and_2h() -> None:
    out = evaluate_delay([_delay_row(imData=_minutes_ago(60))], _ctx())
    assert len(out) == 1 and out[0].severity == "P2"


def test_delay_skips_future_now_and_bad_date() -> None:
    rows = [
        _delay_row(noticeId="D1", imData=(NOW + timedelta(hours=1)).isoformat()),
        _delay_row(noticeId="D2", imData=NOW.isoformat()),
        _delay_row(noticeId="D3", imData="bad"),
        _delay_row(noticeId="D4", imData=None),
    ]
    assert evaluate_delay(rows, _ctx()) == []


def test_delay_masks_driver_fields() -> None:
    finding = evaluate_delay([_delay_row()], _ctx())[0]
    ev = finding.evidence
    assert "张三" not in ev["driver"]
    assert "13800138000" not in ev["driverPhone"]
    assert "沪A12345" not in ev["vehicleNo"]
    assert ev["driverPhone"].endswith("8000")


# ---------- sources ----------

def _gateway(path: str, handler) -> GatewayClient:
    def wrapped(request: httpx.Request) -> httpx.Response:
        assert request.url.path == path
        return handler(request)

    return GatewayClient("http://gateway.test", transport=httpx.MockTransport(wrapped))


@pytest.mark.asyncio
async def test_no_up_source_sorts_oldest_and_dedupes() -> None:
    seen_params: list[Any] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_params.append(request.url.params)
        # PageDTO.total 是查询的 COUNT（含联表重复行），与返回的原始行数一致
        return httpx.Response(200, json={
            "code": 10000,
            "data": {
                "pageIndex": 1, "pageSize": 100, "total": 3, "pages": 1,
                "rows": [_no_up_row(rowId="R1"), _no_up_row(rowId="R1"), _no_up_row(rowId="R2")],
            },
        })

    result = await fetch_no_up(_gateway(NOUP_PATH, handler), TOKEN)
    assert result.status == "ok"
    assert len(result.rows) == 2  # 按 rowId 去重
    assert seen_params[0].get("sort") == "oldest"


@pytest.mark.asyncio
async def test_no_up_source_walks_all_pages_without_truncation() -> None:
    """多页（>100 行）必须全部覆盖，不能把第一页当完整结果。"""
    page_size = 100
    total = 201  # 跨 3 页，第三页仅 1 行

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params.get("pageIndex"))
        start = (page - 1) * page_size
        count = min(page_size, total - start)
        rows = [_no_up_row(rowId=f"R{i}") for i in range(start, start + count)]
        return httpx.Response(200, json={"code": 10000, "data": {
            "pageIndex": page, "pageSize": page_size, "total": total,
            "pages": 3, "rows": rows,
        }})

    result = await fetch_no_up(_gateway(NOUP_PATH, handler), TOKEN)
    assert result.status == "ok"
    assert len(result.rows) == total  # 201，未被 100 截断
    assert result.pages == 3


@pytest.mark.asyncio
async def test_no_up_source_marks_partial_on_list_payload() -> None:
    """旧裸 List 出现在新端点时视为不可信，必须标 partial。"""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 10000, "data": [_no_up_row()]})

    result = await fetch_no_up(_gateway(NOUP_PATH, handler), TOKEN)
    assert result.status == "partial"
    assert result.truncated is True


@pytest.mark.asyncio
async def test_delay_source_dedupes_by_notice_id() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params.get("sort") == "oldest"
        return httpx.Response(200, json={
            "code": 10000,
            "data": {"rows": [_delay_row(noticeId="D1"), _delay_row(noticeId="D1")],
                     "total": 2},
        })

    result = await fetch_delay(_gateway(DELAY_PATH, handler), TOKEN)
    assert result.status == "ok"
    assert len(result.rows) == 1


@pytest.mark.asyncio
async def test_no_up_source_retries_5xx_once_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, json={"code": 9994})
        return httpx.Response(200, json={"code": 10000, "data": {
            "pageIndex": 1, "pageSize": 100, "total": 1, "pages": 1,
            "rows": [_no_up_row()],
        }})

    result = await fetch_no_up(_gateway(NOUP_PATH, handler), TOKEN)
    assert calls["n"] == 2
    assert result.status == "ok"
    assert len(result.rows) == 1


@pytest.mark.asyncio
async def test_delay_source_4xx_not_retried_and_marks_partial() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(400, json={"message": "bad request"})

    result = await fetch_delay(_gateway(DELAY_PATH, handler), TOKEN)
    assert calls["n"] == 1
    assert result.status == "error"
    assert result.truncated is True


# ---------- service integration ----------

@pytest.mark.asyncio
async def test_run_scan_supports_three_row_types_with_no_skips() -> None:
    # backlog 自阶段3起是受支持类型（需要快照端点与历史基线），见 test_scan_backlog_scan.py；
    # 本用例只覆盖三类"逐行"规则的多类型合并。
    assert SUPPORTED_TYPES == ("expiry", "no_up", "delay", "backlog")

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/stock/expiry-warning/query-all":
            data = {
                "rows": [{"id": "S1", "resDate": -1.0, "guoqibili": "0.01",
                          "bzhiQi": "360", "goodsId": "G1", "shpMingCheng": "小蓝管"}],
                "total": 1,
            }
        elif path == NOUP_PATH:
            data = {"pageIndex": 1, "pageSize": 100, "total": 1, "pages": 1,
                    "rows": [_no_up_row(rowId="R1", create_date=_minutes_ago(500))]}
        elif path == DELAY_PATH:
            data = {"rows": [_delay_row(noticeId="D1", imData=_minutes_ago(25 * 60))],
                    "total": 1}
        else:
            raise AssertionError(f"unexpected path {path}")
        return httpx.Response(200, json={"code": 10000, "data": data})

    client = GatewayClient("http://gateway.test", transport=httpx.MockTransport(handler))
    store = MemoryScanStore()
    run = await run_scan(
        scan_id="scan-multi", scan_types=["expiry", "no_up", "delay"],
        principal=_user(), token=TOKEN, client=client, store=store,
        allowed_warehouses=["W01"], dry_run=False, notification_mode="dry_run",
    )
    assert run["status"] == "succeeded"
    assert run["partial"] is False
    assert run["counts"]["findings"] == 3
    assert run["counts"]["alertsCreated"] == 3
    assert run["counts"]["skippedTypes"] == []
    assert len(run["sourceStatus"]) == 3
    assert {s["source"] for s in run["sourceStatus"]} == {"expiry", "no_up", "delay"}


@pytest.mark.asyncio
async def test_no_up_delay_config_thresholds_are_applied() -> None:
    """自定义阈值必须改变分级，证明配置读取生效而非硬编码。"""
    from app.scan.rules.delay import evaluate_delay as rule_delay
    from app.scan.rules.no_up import evaluate_no_up as rule_no_up

    # create_date 3h 前：默认落在 P2（>2h），把 p2 提到 4h 后不再触发
    row = _no_up_row(create_date=_minutes_ago(3 * 60))
    assert rule_no_up([row], _ctx())[0].severity == "P2"
    assert rule_no_up([row], _ctx(), p1_hours=8, p2_hours=4) == []

    # imData 3h 前：默认 P1，把 p1 提到 4h 后落 P2
    drow = _delay_row(imData=_minutes_ago(3 * 60))
    assert rule_delay([drow], _ctx())[0].severity == "P1"
    assert rule_delay([drow], _ctx(), p1_hours=4)[0].severity == "P2"
