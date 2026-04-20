"""CGV 용산아이파크몰 IMAX 신규 오픈 감시 → 텔레그램 알림."""
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.parse
from datetime import date, timedelta
from pathlib import Path

import requests as http
from curl_cffi import requests as cffi

STATE_FILE = Path(__file__).parent / "state.json"

SECRET = b"ydqXY0ocnFLmJGHr_zNzFcpjwAsXq_8JcBNURAkRscg"
BASE = "https://api.cgv.co.kr"
SITE_NO = "0013"
SITE_NM = "CGV 용산아이파크몰"
CO_CD = "A420"
RTCTL_SCOP_CD = "08"
DAYS_AHEAD = 30

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

THEATER_URL = f"https://cgv.co.kr/cnm/movieBook/cinema?siteNo={SITE_NO}"
APP_PACKAGE = "com.cgv.android.movieapp"


def app_link(web_url: str) -> str:
    """Android intent URL: opens CGV app if installed, else falls back to browser."""
    host_path = web_url.split("://", 1)[1]
    fallback = urllib.parse.quote(web_url, safe="")
    return (
        f"intent://{host_path}"
        f"#Intent;scheme=https;package={APP_PACKAGE};"
        f"S.browser_fallback_url={fallback};end"
    )


def book_link(ymd: str, mov_no: str | None = None) -> str:
    qs = f"siteNo={SITE_NO}&scnYmd={ymd}"
    if mov_no:
        qs += f"&movNo={mov_no}"
    return app_link(f"https://cgv.co.kr/cnm/movieBook/cinema?{qs}")


def signed_get(path: str, params: dict) -> dict:
    ts = str(int(time.time()))
    msg = f"{ts}|{path}|".encode()
    sig = base64.b64encode(hmac.new(SECRET, msg, hashlib.sha256).digest()).decode()
    url = f"{BASE}{path}?{urllib.parse.urlencode(params)}"
    headers = {
        "User-Agent": UA,
        "Accept": "application/json",
        "Accept-Language": "ko-KR",
        "Origin": "https://cgv.co.kr",
        "Referer": f"https://cgv.co.kr/cnm/movieBook/cinema?siteNo={SITE_NO}",
        "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Site": "same-site",
        "X-TIMESTAMP": ts,
        "X-SIGNATURE": sig,
    }
    r = cffi.get(url, headers=headers, timeout=30, impersonate="chrome")
    r.raise_for_status()
    return r.json()


def is_imax(row: dict) -> bool:
    return "IMAX" in (row.get("scnsNm") or "") or (
        row.get("movkndDsplNm") or ""
    ).startswith("IMAX")


def fetch_snapshot() -> dict[str, dict[str, str]]:
    """{YYYYMMDD: {영화명: movNo}}"""
    today = date.today()
    out: dict[str, dict[str, str]] = {}
    for i in range(DAYS_AHEAD + 1):
        ymd = (today + timedelta(days=i)).strftime("%Y%m%d")
        data = signed_get(
            "/cnm/atkt/searchMovScnInfo",
            {
                "coCd": CO_CD,
                "siteNo": SITE_NO,
                "scnYmd": ymd,
                "scnsNo": "",
                "scnSseq": "",
                "rtctlScopCd": RTCTL_SCOP_CD,
                "custNo": "",
            },
        ).get("data") or []
        movies: dict[str, str] = {}
        for row in data:
            if not is_imax(row):
                continue
            name = row.get("prodNm")
            if not name:
                continue
            movies.setdefault(name, row.get("movNo") or "")
        if movies:
            out[ymd] = movies
    return out


def load_state() -> dict | None:
    if STATE_FILE.exists():
        raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        # 구 포맷(list) 호환
        if raw and isinstance(next(iter(raw.values())), list):
            return {d: {m: "" for m in ms} for d, ms in raw.items()}
        return raw
    return None


def save_state(state: dict) -> None:
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def send_telegram(text: str) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    resp = http.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    resp.raise_for_status()


def fmt_date(ymd: str) -> str:
    return f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}" if len(ymd) == 8 and ymd.isdigit() else ymd


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fmt_entry(ymd: str, name: str, mov_no: str) -> str:
    link = book_link(ymd, mov_no)
    return f'      - <a href="{link}">{esc(name)}</a>'


def main() -> int:
    try:
        current = fetch_snapshot()
    except Exception as e:
        print(f"[error] fetch failed: {e}", file=sys.stderr)
        return 1

    prev = load_state()

    if prev is None:
        total = sum(len(m) for m in current.values())
        lines = [
            f"🎬 <b>{SITE_NM} IMAX 감시 시작</b>",
            f"현재 오픈 날짜: {len(current)} / 총 IMAX 회차: {total}",
        ]
        if current:
            furthest = max(current)
            lines.append(f"가장 먼 날짜: {fmt_date(furthest)}")
        lines += ["", f'🔗 <a href="{app_link(THEATER_URL)}">극장 예매 페이지</a>']
        send_telegram("\n".join(lines))
        save_state(current)
        print(f"initialized: {len(current)} dates, {total} IMAX entries")
        return 0

    new_dates = sorted(set(current) - set(prev))
    new_in_existing: list[tuple[str, str, str]] = []
    for ymd, movies in current.items():
        if ymd in new_dates:
            continue
        old = set(prev.get(ymd, {}).keys())
        for name, mov_no in movies.items():
            if name not in old:
                new_in_existing.append((ymd, name, mov_no))
    new_in_existing.sort()

    if new_dates or new_in_existing:
        lines = [f"🎬 <b>{SITE_NM} IMAX 신규 오픈!</b>", ""]
        if new_dates:
            lines.append("📅 <b>새로 열린 날짜</b>")
            for d in new_dates:
                lines.append(f"  • <b>{fmt_date(d)}</b>")
                for name, mov_no in current[d].items():
                    lines.append(fmt_entry(d, name, mov_no))
            lines.append("")
        if new_in_existing:
            lines.append("🎞️ <b>기존 날짜에 추가된 회차</b>")
            for ymd, name, mov_no in new_in_existing:
                lines.append(f"  • <b>{fmt_date(ymd)}</b>")
                lines.append(fmt_entry(ymd, name, mov_no))
            lines.append("")
        lines.append(f'🔗 <a href="{app_link(THEATER_URL)}">극장 페이지</a>')
        send_telegram("\n".join(lines))
        print(f"notified: {len(new_dates)} new dates, {len(new_in_existing)} new pairs")
    else:
        print("no changes")

    save_state(current)
    return 0


if __name__ == "__main__":
    sys.exit(main())
