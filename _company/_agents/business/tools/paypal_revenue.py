#!/usr/bin/env python3
# version: paypal_revenue_v1
"""PayPal 매출 자동 분석 — Connect AI 비즈니스 에이전트 전용.

흐름:
  1. CLIENT_ID + CLIENT_SECRET 으로 OAuth2 access token 발급
  2. Transaction Search API 호출 (LOOKBACK_DAYS 기간)
  3. 거래 파싱 → 매출·환불·평균액·통화별 집계
  4. 마크다운 리포트 stdout 출력

config (paypal_revenue.json):
  MODE          — 'sandbox' (테스트) | 'live' (실제). 기본 sandbox
  CLIENT_ID     — PayPal Developer Dashboard 에서 발급
  CLIENT_SECRET — 같은 곳, 비밀로 보관 (password 필드)
  LOOKBACK_DAYS — 분석할 과거 일수 (기본 30)
  CURRENCY      — 기본 통화 (USD/KRW 등). 비우면 모든 통화 표시

발급: https://developer.paypal.com/dashboard/applications → Apps & Credentials
샌드박스 테스트: sandbox.paypal.com 계정 무료 생성 가능
"""
import os, sys, json, base64, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timedelta, timezone


HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "paypal_revenue.json")


def _log(msg, kind="info"):
    prefix = {"info": "💰", "ok": "✅", "warn": "⚠️ ", "err": "❌", "step": "▸"}.get(kind, "•")
    print(f"{prefix} {msg}", file=sys.stderr, flush=True)


def _load():
    if not os.path.exists(CONFIG):
        return {}
    try:
        with open(CONFIG, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _base_url(mode: str) -> str:
    return "https://api-m.paypal.com" if mode.lower() == "live" else "https://api-m.sandbox.paypal.com"


def _get_access_token(base_url: str, client_id: str, client_secret: str) -> str:
    """OAuth2 client_credentials grant — 5분 정도 캐시 가능하지만 매번 새로 발급도 안전."""
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    req = urllib.request.Request(
        f"{base_url}/v1/oauth2/token",
        data=b"grant_type=client_credentials",
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
            return data["access_token"]
    except urllib.error.HTTPError as e:
        err_body = e.read().decode(errors="ignore")[:200]
        raise RuntimeError(f"OAuth 실패 (HTTP {e.code}): {err_body}")
    except Exception as e:
        raise RuntimeError(f"OAuth 요청 실패: {e}")


def _fetch_transactions(base_url: str, token: str, start: datetime, end: datetime, currency_filter: str = ""):
    """Transaction Search API — 페이지네이션 자동 처리.
    공식 API 는 한 번에 최대 31일·500건 → 여러 페이지로 나눠 호출."""
    all_txs = []
    cur = start
    while cur < end:
        page_end = min(cur + timedelta(days=31), end)
        params = {
            "start_date": cur.isoformat().replace("+00:00", "Z"),
            "end_date": page_end.isoformat().replace("+00:00", "Z"),
            "fields": "all",
            "page_size": "500",
            "page": "1",
        }
        if currency_filter:
            params["transaction_currency"] = currency_filter
        url = f"{base_url}/v1/reporting/transactions?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read().decode())
                txs = data.get("transaction_details", [])
                all_txs.extend(txs)
                _log(f"{cur.date()} ~ {page_end.date()}: {len(txs)}건 수신", "step")
                total_pages = int(data.get("total_pages", 1))
                if total_pages > 1:
                    for p in range(2, total_pages + 1):
                        params["page"] = str(p)
                        url2 = f"{base_url}/v1/reporting/transactions?" + urllib.parse.urlencode(params)
                        req2 = urllib.request.Request(url2, headers={"Authorization": f"Bearer {token}"})
                        with urllib.request.urlopen(req2, timeout=20) as r2:
                            d2 = json.loads(r2.read().decode())
                            all_txs.extend(d2.get("transaction_details", []))
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="ignore")[:300]
            _log(f"거래 조회 실패 ({cur.date()}~{page_end.date()}): HTTP {e.code} {body}", "warn")
        except Exception as e:
            _log(f"거래 조회 예외: {e}", "warn")
        cur = page_end
    return all_txs


def _summarize(txs, default_currency: str = ""):
    """거래 리스트 → 마크다운 리포트."""
    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    by_currency = {}            # {USD: {"gross": float, "fees": float, "refunds": float, "count": int}}
    by_period = {"today": 0.0, "week": 0.0, "month": 0.0}
    transactions_clean = []     # 정상 거래 (T0000 = 일반 결제)
    refunds = []

    for t in txs:
        info = t.get("transaction_info", {})
        amount = info.get("transaction_amount", {})
        currency = amount.get("currency_code", "USD")
        value = float(amount.get("value", "0") or 0)
        status = info.get("transaction_status", "")
        event_code = info.get("transaction_event_code", "")
        ts_str = info.get("transaction_initiation_date", "")
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except Exception:
            ts = None

        if currency not in by_currency:
            by_currency[currency] = {"gross": 0.0, "fees": 0.0, "refunds": 0.0, "count": 0}
        c = by_currency[currency]

        if event_code.startswith("T1") or "REFUND" in event_code or value < 0:
            c["refunds"] += abs(value)
            refunds.append((ts, value, currency))
        else:
            c["gross"] += value
            c["count"] += 1
            transactions_clean.append((ts, value, currency))
            if ts and currency == (default_currency or currency):
                if ts >= today_start:
                    by_period["today"] += value
                if ts >= week_start:
                    by_period["week"] += value
                if ts >= month_start:
                    by_period["month"] += value
        fee = float(info.get("fee_amount", {}).get("value", "0") or 0)
        c["fees"] += abs(fee)

    # 마크다운 리포트
    lines = []
    lines.append(f"# 💰 PayPal 매출 분석")
    lines.append(f"_{now.isoformat(timespec='minutes')} · 최근 거래 {len(txs)}건_")
    lines.append("")

    if not txs:
        lines.append("> ⚠️ 분석 기간에 거래가 없어요. PayPal Developer Dashboard 에서 모드(sandbox/live)·기간·계정을 확인하세요.")
        lines.append("")
        lines.append("**가능한 원인:**")
        lines.append("- 샌드박스 모드인데 실제 결제 데이터가 없음 → sandbox.paypal.com 에서 거래 시뮬레이션")
        lines.append("- API 권한 부족 → Developer Dashboard 에서 'Transaction Search' 권한 활성화")
        lines.append("- 너무 짧은 기간 → LOOKBACK_DAYS 늘려보기")
        return "\n".join(lines)

    # 통화별 집계
    lines.append("## 📊 통화별 매출")
    lines.append("")
    lines.append("| 통화 | 매출 (Gross) | 환불 | 수수료 | 순매출 | 거래수 |")
    lines.append("|---|---|---|---|---|---|")
    for cur, d in sorted(by_currency.items()):
        net = d["gross"] - d["refunds"] - d["fees"]
        lines.append(f"| **{cur}** | {d['gross']:,.2f} | -{d['refunds']:,.2f} | -{d['fees']:,.2f} | **{net:,.2f}** | {d['count']}건 |")
    lines.append("")

    # 기간별 (default_currency 기준)
    primary_cur = default_currency or (sorted(by_currency.items(), key=lambda x: -x[1]["gross"])[0][0] if by_currency else "USD")
    lines.append(f"## 📅 기간별 매출 ({primary_cur})")
    lines.append("")
    lines.append(f"- **오늘**: {by_period['today']:,.2f} {primary_cur}")
    lines.append(f"- **지난 7일**: {by_period['week']:,.2f} {primary_cur}")
    lines.append(f"- **지난 30일**: {by_period['month']:,.2f} {primary_cur}")
    lines.append("")
    # 평균 거래액
    if transactions_clean:
        primary_txs = [v for (_, v, c) in transactions_clean if c == primary_cur]
        if primary_txs:
            avg = sum(primary_txs) / len(primary_txs)
            lines.append(f"- 평균 거래액 ({primary_cur}): **{avg:,.2f}**")
            lines.append(f"- 최대 거래: {max(primary_txs):,.2f}")
            lines.append(f"- 최소 거래: {min(primary_txs):,.2f}")
    lines.append("")

    # 최근 거래 10건
    lines.append("## 🕐 최근 거래 10건")
    lines.append("")
    lines.append("| 일시 | 금액 | 통화 | 종류 |")
    lines.append("|---|---|---|---|")
    sorted_txs = sorted(
        [(ts, v, c, "결제") for ts, v, c in transactions_clean] +
        [(ts, -v, c, "환불") for ts, v, c in refunds],
        key=lambda x: x[0] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True
    )[:10]
    for ts, v, c, kind in sorted_txs:
        ts_str = ts.strftime("%Y-%m-%d %H:%M") if ts else "?"
        sign = "+" if kind == "결제" else "-"
        lines.append(f"| {ts_str} | {sign}{abs(v):,.2f} | {c} | {kind} |")
    lines.append("")

    # 환불 비율 경고
    total_count = sum(d["count"] for d in by_currency.values())
    if refunds and total_count > 0:
        refund_rate = len(refunds) / (total_count + len(refunds)) * 100
        if refund_rate > 10:
            lines.append(f"> 🚨 **환불율 경고**: {refund_rate:.1f}% — 평균(2~5%)보다 높음. 원인 분석 권장.")
            lines.append("")

    # 인사이트
    lines.append("## 💡 다음 액션")
    if by_period['month'] > 0:
        weekly_avg = by_period['month'] / 4
        if by_period['week'] > weekly_avg * 1.2:
            lines.append(f"- 🚀 이번 주 매출({by_period['week']:,.0f})이 월 평균({weekly_avg:,.0f})보다 20%↑ — 무엇이 잘됐는지 파악")
        elif by_period['week'] < weekly_avg * 0.7:
            lines.append(f"- ⚠️ 이번 주 매출({by_period['week']:,.0f})이 월 평균({weekly_avg:,.0f})보다 30%↓ — 원인 점검")
        else:
            lines.append(f"- 📈 이번 주 매출({by_period['week']:,.0f})은 월 평균 추세 유지")
    if len(by_currency) > 1:
        lines.append(f"- 💱 {len(by_currency)}개 통화로 매출 발생 — 환율 변동 위험 분산 또는 헤지 검토")

    return "\n".join(lines)


def main():
    cfg = _load()
    mode = (cfg.get("MODE") or "sandbox").strip().lower()
    client_id = (cfg.get("CLIENT_ID") or "").strip()
    client_secret = (cfg.get("CLIENT_SECRET") or "").strip()
    lookback = int(cfg.get("LOOKBACK_DAYS", 30))
    currency = (cfg.get("CURRENCY") or "").strip().upper()

    if not client_id or not client_secret:
        _log("CLIENT_ID 또는 CLIENT_SECRET 비어있음. PayPal Developer Dashboard 에서 발급:", "err")
        _log("  https://developer.paypal.com/dashboard/applications", "info")
        _log("  → Apps & Credentials → 본인 앱 → Client ID + Secret 복사", "info")
        sys.exit(1)

    base = _base_url(mode)
    _log(f"PayPal {mode.upper()} 모드 · 최근 {lookback}일 분석", "info")

    try:
        token = _get_access_token(base, client_id, client_secret)
        _log("OAuth 인증 성공", "ok")
    except Exception as e:
        _log(f"OAuth 실패: {e}", "err")
        sys.exit(1)

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=lookback)
    txs = _fetch_transactions(base, token, start, end, currency)
    _log(f"총 {len(txs)}건 거래 수집", "ok")

    report = _summarize(txs, currency)
    print(report)


if __name__ == "__main__":
    main()
