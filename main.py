import os
import sys
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://sb.sb"
SIGNIN_URL = f"{BASE_URL}/signin/"
COOKIE = os.getenv("SB_COOKIE", "").strip()
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "").strip()
TG_CHAT_ID = os.getenv("TG_CHAT_ID", "").strip()
TIMEOUT = 25


@dataclass
class SigninState:
    status: str   # signed / pending / guest / unknown
    csrf: Optional[str]


def notify_telegram(message: str) -> None:
    """Optional Telegram notification."""
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
            data={"chat_id": TG_CHAT_ID, "text": message},
            timeout=15,
        )
        r.raise_for_status()
    except Exception as exc:
        print(f"[WARN] Telegram notification failed: {exc}")


def create_session() -> requests.Session:
    if not COOKIE:
        raise RuntimeError(
            "Missing SB_COOKIE. Add it under GitHub "
            "Settings -> Secrets and variables -> Actions."
        )

    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/152.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Cookie": COOKIE,
        }
    )
    return s


def parse_signin_page(html: str, final_url: str = "") -> SigninState:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    signed_text = "今日已签到" in text

    action = soup.select_one(".signin-hero-action")
    button = action.find("button") if action else None
    disabled = bool(button and button.has_attr("disabled"))

    csrf_input = soup.select_one('input[name="_csrf"]')
    csrf = csrf_input.get("value") if csrf_input else None

    if signed_text or disabled:
        return SigninState("signed", csrf)

    if button and csrf:
        return SigninState("pending", csrf)

    lower_url = final_url.lower()
    if "/login" in lower_url or ("登录" in text and not csrf):
        return SigninState("guest", csrf)

    return SigninState("unknown", csrf)


def fetch_signin_state(session: requests.Session) -> SigninState:
    r = session.get(SIGNIN_URL, timeout=TIMEOUT, allow_redirects=True)

    if r.status_code in (401, 403):
        raise RuntimeError(
            f"GET /signin/ returned HTTP {r.status_code}. "
            "The Cookie may be expired, or GitHub Actions may be blocked by site protection."
        )

    r.raise_for_status()
    return parse_signin_page(r.text, r.url)


def submit_signin(session: requests.Session, csrf: str) -> requests.Response:
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": BASE_URL,
        "Referer": SIGNIN_URL,
    }
    return session.post(
        SIGNIN_URL,
        data={"_csrf": csrf},
        headers=headers,
        timeout=TIMEOUT,
        allow_redirects=True,
    )


def main() -> int:
    session = create_session()

    before = fetch_signin_state(session)
    print(f"[INFO] Before: status={before.status}")

    if before.status == "signed":
        msg = "✅ 烧饼论坛（sb.sb）今日已经签到，无需重复签到"
        print(msg)
        notify_telegram(msg)
        return 0

    if before.status == "guest":
        raise RuntimeError("Cookie is invalid or expired; sb.sb appears to require login.")

    if before.status != "pending":
        raise RuntimeError(
            "Could not recognize the sb.sb sign-in page. "
            "The page structure may have changed."
        )

    if not before.csrf:
        raise RuntimeError("No _csrf token found on /signin/.")

    r = submit_signin(session, before.csrf)
    print(f"[INFO] POST /signin/: HTTP {r.status_code}")

    if r.status_code in (401, 403):
        raise RuntimeError(
            f"POST /signin/ returned HTTP {r.status_code}. "
            "Cookie may be invalid or the request may be blocked."
        )

    returned_state = parse_signin_page(r.text, r.url)
    if returned_state.status == "signed":
        msg = "✅ 烧饼论坛（sb.sb）签到成功"
        print(msg)
        notify_telegram(msg)
        return 0

    after = fetch_signin_state(session)
    print(f"[INFO] After: status={after.status}")

    if after.status != "signed":
        raise RuntimeError(
            f"Sign-in submission was not confirmed. Final status: {after.status}"
        )

    msg = "✅ 烧饼论坛（sb.sb）签到成功"
    print(msg)
    notify_telegram(msg)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        msg = f"❌ 烧饼论坛（sb.sb）签到失败\n{type(exc).__name__}: {exc}"
        print(msg, file=sys.stderr)
        notify_telegram(msg)
        sys.exit(1)
