"""CGV 용산아이파크몰 프로젝트 헤일메리 IMAX 신규 회차 감시 (18:00 이후)."""
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

MOVIE_KEYWORDS = ("헤일메리", "Hail Mary", "hailmary", "HAIL MARY")
MIN_TIME = "1800"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

PAGES_URL = "https://lsy980507.github.io/cgv-imax-watcher/"


def app_link(web_url: str) -> str:
    return f"{PAGES_URL}?v=3&u={urllib.parse.quote(web_url, safe='')}"


def showing_url(ymd: str, mov_no: str, scns_no: str, scn_sseq: str) -> str:
    """검증된 /cnm/movieBook/cinema 경로 + 가능한 모든 식별자.

    CGV의 단일 회차 좌석 페이지 URL은 공개돼 있지 않아, 극장 예매 페이지에
    영화/날짜/스크린/회차 시퀀스를 모두 넣어 최대한 좌석 단계로 내려가도록 유도.
    """
    qs = (
        f"siteNo={SITE_NO}&scnYmd={ymd}&movNo={mov_no}"
        f"&scnsNo={scns_no}&scnSseq={scn_sseq}"
    )
    return f"https://cgv.co.kr/cnm/movieBook/cinema?{qs}"


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


def is_target_movie(row: dict) -> bool:
    blob = " ".join(
        (row.get(k) or "")
        for k in ("prodNm", "movNm", "engProdNm", "movEnm", "expoProdNm")
    )
    return any(kw in blob for kw in MOVIE_KEYWORDS)


def fetch_snapshot() -> dict[str, list[dict]]:
    """{YYYYMMDD: [showing, ...]} — 헤일메리 IMAX & 18:00 이후만."""
    today = date.today()
    out: dict[str, list[dict]] = {}
    for i in range(DAYS_AHEAD + 1):
        ymd = (today + timedelta(days=i)).strftime("%Y%m%d")
        rows = signed_get(
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
        keep: list[dict] = []
        for r in rows:
            if not (is_imax(r) and is_target_movie(r)):
                continue
            start = r.get("scnsrtTm") or ""
            if len(start) != 4 or not start.isdigit() or start < MIN_TIME:
                continue
            keep.append(
                {
                    "scnsNo": r.get("scnsNo") or "",
                    "scnSseq": r.get("scnSseq") or "",
                    "scnsrtTm": start,
                    "scnendTm": r.get("scnendTm") or "",
                    "scnsNm": r.get("scnsNm") or "",
                    "prodNm": r.get("prodNm") or "",
                    "movNo": r.get("movNo") or "",
                    "frSeatCnt": r.get("frSeatCnt") or "",
                }
            )
        if keep:
            keep.sort(key=lambda x: x["scnsrtTm"])
            out[ymd] = keep
    return out


def load_state() -> dict | None:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
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


def fmt_time(hhmm: str) -> str:
    return f"{hhmm[:2]}:{hhmm[2:]}" if len(hhmm) == 4 and hhmm.isdigit() else hhmm


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fmt_showing(ymd: str, s: dict) -> str:
    link = app_link(
        showing_url(ymd, s.get("movNo", ""), s["scnsNo"], s["scnSseq"])
    )
    label = (
        f'{fmt_time(s["scnsrtTm"])}~{fmt_time(s["scnendTm"])} '
        f'· {esc(s["scnsNm"])} · 잔여 {esc(s["frSeatCnt"])}석'
    )
    return f'      - <a href="{link}">{label} (예매)</a>'


def main() -> int:
    try:
        current = fetch_snapshot()
    except Exception as e:
        print(f"[error] fetch failed: {e}", file=sys.stderr)
        return 1

    prev = load_state()

    if prev is None:
        total = sum(len(v) for v in current.values())
        lines = [
            f"🎬 <b>{SITE_NM} 프로젝트 헤일메리 IMAX 감시 시작</b>",
            f"18:00 이후 회차: {total}개 / {len(current)}일",
        ]
        if current:
            lines.append("")
            lines.append("📅 <b>현재 오픈 회차</b>")
            for ymd in sorted(current):
                lines.append(f"  • <b>{fmt_date(ymd)}</b>")
                for s in current[ymd]:
                    lines.append(fmt_showing(ymd, s))
        else:
            lines.append("")
            lines.append("(아직 오픈된 회차 없음 — 열리면 알림 발송)")
        send_telegram("\n".join(lines))
        save_state(current)
        print(f"initialized: {total} showings across {len(current)} days")
        return 0

    new_showings: list[tuple[str, dict]] = []
    for ymd, shows in current.items():
        prev_keys = {(s["scnsNo"], s["scnSseq"]) for s in prev.get(ymd, [])}
        for s in shows:
            if (s["scnsNo"], s["scnSseq"]) not in prev_keys:
                new_showings.append((ymd, s))
    new_showings.sort(key=lambda x: (x[0], x[1]["scnsrtTm"]))

    if new_showings:
        lines = [
            f"🎬 <b>{SITE_NM} 프로젝트 헤일메리 IMAX 신규 회차!</b> (18:00 이후)",
            "",
        ]
        by_date: dict[str, list[dict]] = {}
        for ymd, s in new_showings:
            by_date.setdefault(ymd, []).append(s)
        for ymd in sorted(by_date):
            lines.append(f"  • <b>{fmt_date(ymd)}</b>")
            for s in by_date[ymd]:
                lines.append(fmt_showing(ymd, s))
        send_telegram("\n".join(lines))
        print(f"notified: {len(new_showings)} new showings")
    else:
        print("no changes")

    save_state(current)
    return 0


if __name__ == "__main__":
    sys.exit(main())
