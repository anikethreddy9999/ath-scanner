"""
Daily scanner for the "all-time high + 200 DMA exit" strategy.  (Self-contained.)

Each run it:
  1. downloads prices for the stocks in my_stocks.txt,
  2. finds stocks that NEWLY came within --near-pct % of their all-time high
     while above the 200-day moving average,
  3. lists every stock currently qualifying (the watchlist),
  4. checks your holdings and flags any that closed below the 200 DMA (SELL),
  5. writes a phone-friendly dashboard (docs/index.html + manifest + icons),
  6. optionally sends a Telegram message and/or email (--notify).

Holdings (stocks you own) come from the HOLDINGS environment variable
(e.g. "TCS, INFY, ITC") or from holdings.txt if you run it on your own computer.

Notifications (environment variables / GitHub secrets):
  Telegram: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
  Email   : SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASS, EMAIL_TO
  Optional: DASHBOARD_URL (added to the alert message)

Signals are end-of-day. Educational tool, not financial advice.
"""
import argparse
import base64
import html
import json
import os
import re
import smtplib
import urllib.parse
import urllib.request
from datetime import datetime
from email.message import EmailMessage
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ICON192 = "iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAIAAADdvvtQAAACz0lEQVR42u3d23WDQBBEQWXgTP2p9HEKFiC2e6c4NwKmdHgI2NfP+1c63csuEEACSAAJIAkgASSABJAEkAASQAJIAkgACSABJAEkgASQABJAEkACSAAJIAkgASSABJAE0GYd/94A0kk6D0gCaASd7zECaBCdbxgCaJyeexkBNJHOjYYAmqvnFkMAjdZz3RBAAF0yBBA9ANGzzhBAAF0yBBA9ANGzzhBAAAEE0DpDANEDEEAACSBtAugjQwABBBA9AAEEkAASQAABBBBDAMmNRAEEEEAAMQSQttQDED0A0eOheoAA0kQ9ANEDED3ejaenVA9AAPnAFD0+cUdPqR6A6AGIHh8ap6dUD0C+HAUQPYvW6QHI1+YBoudtwTl6ANJMPQA5eAFED0APDI8egG6YnFMfgG4YGz0AXR2bgxdAcYuoD9RTDyhnJDP1dAPKmc1YPcWAciY08MS5HlDOkIbrqQQUNarhevoARQ2MnjJAUU/x0VMGKOphUHrKAEU9UOzEuQxQ1MsM9JQBSnuRip4mQGkv49HTBOg4sr6gQ08ToGPeBhA94/QkAqIHIHqm6MkCRA9A9MzSkwLoGLkBRM90PesB0QMQPXP1rARED0D0TNezBtDDAwNoK0BLpkXPJoDWTouebkAJ06KnFVDOtOjpA5Q2LYCaAGWOip4OQMk/dHrSAVUcJugJBVR0kkFPHKC6U1R6ggCVXuAAFAGo+vKYnsWANri5Qs8yQDvdmqNnW0DT1k6YAmjLG7vobAVo8vpRALm6AWgdIEMCiB6A/CWpLkBmAxA9ALUtvqTpgIzEXxn0AORZCHU9zmESAJ03ZAwAnTdkBgCdN2QAAJ1kZNcDJAEkgASQABJAEkACSAAJIAkgASSABJAEkAASQAJIAkgACSABJIAkgASQABJAEkACSAAJIAkgASSABJAEkAASQAJIANkLAkgACSABJAGkx/oDkr1WV5IDxiwAAAAASUVORK5CYII="
ICON512 = "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"
IST = ZoneInfo("Asia/Kolkata")


# ------------------------------------------------------------------ data
def read_list(path):
    if not path or not os.path.exists(path):
        return []
    out = []
    for line in open(path):
        line = line.split("#")[0].strip()
        if line:
            out.extend(re.split(r"[,\s]+", line))
    return [x for x in out if x]


def norm(t):
    t = t.strip().upper()
    return t if t.endswith((".NS", ".BO")) or t.startswith("^") else f"{t}.NS"


def short(t):
    return t.replace(".NS", "").replace(".BO", "")


def load_prices(tickers, data_start, synthetic):
    if synthetic:
        rng = np.random.default_rng(7)
        idx = pd.bdate_range(data_start, periods=4500)
        market = rng.normal(0.0003, 0.008, len(idx))
        cols = {f"STK{i:02d}": 100 * np.exp(np.cumsum(market + rng.normal(rng.normal(0.0002, 0.0003), 0.014, len(idx))))
                for i in range(40)}
        return pd.DataFrame(cols, index=idx)
    import yfinance as yf

    raw = yf.download(tickers, start=data_start, auto_adjust=True, progress=False)["Close"]
    if isinstance(raw, pd.Series):
        raw = raw.to_frame(tickers[0])
    empty = [c for c in raw.columns if raw[c].dropna().empty]
    if empty:
        print(f"Warning: no data for {[short(c) for c in empty]}; skipped")
    return raw.drop(columns=empty).sort_index()


# ------------------------------------------------------------------ analysis
def analyse(prices, ma_len, near_pct):
    prices = prices.dropna(how="all")
    ma = prices.rolling(ma_len).mean()
    ath = prices.cummax()
    dist = 1 - prices / ath
    entry = (dist <= near_pct / 100) & (prices > ma) & ma.notna()
    below = (prices < ma) & ma.notna()
    tbl = pd.DataFrame({
        "price": prices.iloc[-1],
        "ath": ath.iloc[-1],
        "dist_ath": dist.iloc[-1] * 100,
        "ma": ma.iloc[-1],
        "vs_ma": (prices.iloc[-1] / ma.iloc[-1] - 1) * 100,
        "qualifies": entry.iloc[-1],
        "qualified_yday": entry.iloc[-2],
        "below_ma": below.iloc[-1],
    }).dropna(subset=["price"])
    tbl["at_ath"] = tbl["dist_ath"] <= 1e-9
    return prices.index[-1], tbl


def build_report(tbl, holdings, as_of):
    held = [h for h in holdings if h in tbl.index]
    missing = [h for h in holdings if h not in tbl.index]
    held_tbl = tbl.loc[held]
    sells = held_tbl[held_tbl["below_ma"]].sort_values("vs_ma")
    near_ma = held_tbl[(~held_tbl["below_ma"]) & (held_tbl["vs_ma"] < 5)].sort_values("vs_ma")
    free = tbl[~tbl.index.isin(held)]
    new = free[free["qualifies"] & ~free["qualified_yday"]].sort_values("dist_ath")
    watch = free[free["qualifies"]].sort_values("dist_ath")
    return {"as_of": as_of, "sells": sells, "near_ma": near_ma, "new": new,
            "watch": watch, "holdings": held_tbl.sort_values("vs_ma"), "missing": missing}


# ------------------------------------------------------------------ outputs
def message_text(r, near_pct, ma_len, limit=15):
    lines = [f"ATH scan - {r['as_of'].date()}"]
    if len(r["sells"]):
        lines.append(f"\nSELL (closed below {ma_len} DMA):")
        for t, x in r["sells"].iterrows():
            lines.append(f"  {short(t)}  {x.price:,.2f}  ({x.vs_ma:+.1f}% vs DMA)")
    if len(r["near_ma"]):
        lines.append(f"\nHolding, within 5% of {ma_len} DMA:")
        for t, x in r["near_ma"].iterrows():
            lines.append(f"  {short(t)}  {x.vs_ma:+.1f}% above DMA")
    if len(r["new"]):
        lines.append(f"\nNEW near all-time high (within {near_pct:g}%):")
        for t, x in r["new"].head(limit).iterrows():
            tag = "AT ATH" if x.at_ath else f"{x.dist_ath:.1f}% below ATH"
            lines.append(f"  {short(t)}  {x.price:,.2f}  {tag}")
        if len(r["new"]) > limit:
            lines.append(f"  ...and {len(r['new']) - limit} more")
    lines.append(f"\nWatchlist size: {len(r['watch'])}")
    if r["missing"]:
        lines.append("No data for holdings: " + ", ".join(short(m) for m in r["missing"]))
    url = os.environ.get("DASHBOARD_URL")
    if url:
        lines.append(f"\nDashboard: {url}")
    return "\n".join(lines)


def _rows(df, cols):
    if not len(df):
        return '<p class="empty">None today.</p>'
    heads = "".join(f"<th>{h}</th>" for _, h, _ in cols)
    body = ""
    for t, x in df.iterrows():
        cells = f"<td class='t'>{html.escape(short(t))}</td>"
        for key, _, fmt in cols:
            cells += f"<td>{fmt(x[key])}</td>"
        body += f"<tr>{cells}</tr>"
    return f"<table><tr><th>Stock</th>{heads}</tr>{body}</table>"


def dashboard_html(r, near_pct, ma_len, include_holdings):
    px = lambda v: f"{v:,.2f}"
    pct = lambda v: f"{v:.1f}%"
    spct = lambda v: f"{v:+.1f}%"
    cols_watch = [("price", "Price", px), ("ath", "All-time high", px),
                  ("dist_ath", "Below ATH", pct), ("vs_ma", f"vs {ma_len} DMA", spct)]
    cols_hold = [("price", "Price", px), ("ma", f"{ma_len} DMA", px), ("vs_ma", f"vs {ma_len} DMA", spct)]

    cards = (f"<div class='card'><b>{len(r['new'])}</b><span>new today</span></div>"
             f"<div class='card'><b>{len(r['watch'])}</b><span>on watchlist</span></div>")
    sections = (f"<h2>New near all-time high</h2><div class='wrap'>{_rows(r['new'], cols_watch)}</div>"
                f"<h2>Full watchlist</h2><p class='sub'>Within {near_pct:g}% of all-time high and above the {ma_len}-day average</p>"
                f"<div class='wrap'>{_rows(r['watch'], cols_watch)}</div>")
    if include_holdings:
        cards = (f"<div class='card sell'><b>{len(r['sells'])}</b><span>sell alerts</span></div>" + cards)
        sections = (f"<h2>Sell alerts</h2><div class='wrap'>{_rows(r['sells'], cols_hold)}</div>"
                    + sections + f"<h2>Your holdings</h2><div class='wrap'>{_rows(r['holdings'], cols_hold)}</div>")
    now = datetime.now(IST).strftime("%d %b %Y, %H:%M IST")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0f766e">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="ATH Scanner">
<link rel="manifest" href="manifest.json">
<link rel="apple-touch-icon" href="icon-192.png">
<link rel="icon" href="icon-192.png">
<title>ATH Scanner</title>
<style>
:root{{--bg:#fff;--fg:#1a1a1a;--mut:#6b6b6b;--line:#e4e4e4;--card:#f5f5f4;--red:#b3261e}}
@media(prefers-color-scheme:dark){{:root{{--bg:#161616;--fg:#eee;--mut:#9a9a9a;--line:#333;--card:#222;--red:#ff8a80}}}}
body{{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;margin:0 auto;max-width:860px;padding:16px;padding-top:max(16px,env(safe-area-inset-top))}}
h1{{font-size:22px;margin:4px 0}}h2{{font-size:16px;margin:26px 0 6px}}
.sub{{color:var(--mut);font-size:13px;margin:0 0 6px}}.cards{{display:flex;gap:10px;margin:14px 0;flex-wrap:wrap}}
.card{{background:var(--card);border-radius:10px;padding:10px 16px;min-width:100px}}
.card b{{display:block;font-size:24px}}.card span{{color:var(--mut);font-size:12px}}
.sell b{{color:var(--red)}}
table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}}
th,td{{text-align:right;padding:6px 8px;border-bottom:1px solid var(--line);white-space:nowrap}}
th:first-child,td:first-child{{text-align:left}}th{{color:var(--mut);font-weight:500;font-size:12px}}
td.t{{font-weight:600}}.empty{{color:var(--mut)}}.wrap{{overflow-x:auto}}
</style></head><body>
<h1>All-time-high scanner</h1>
<div class="sub">Prices as of {r['as_of'].date()} close &middot; updated {now} &middot; not financial advice</div>
<div class="cards">{cards}</div>
{sections}
</body></html>"""


def write_site(out, r, near_pct, ma_len, include_holdings):
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "index.html"), "w") as f:
        f.write(dashboard_html(r, near_pct, ma_len, include_holdings))
    manifest = {"name": "ATH Scanner", "short_name": "ATH Scanner", "start_url": "./",
                "display": "standalone", "background_color": "#ffffff", "theme_color": "#0f766e",
                "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
                          {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"}]}
    with open(os.path.join(out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    for name, b64 in (("icon-192.png", ICON192), ("icon-512.png", ICON512)):
        with open(os.path.join(out, name), "wb") as f:
            f.write(base64.b64decode(b64))
    sig = {"as_of": str(r["as_of"].date()),
           "new": [short(t) for t in r["new"].index],
           "watchlist": [short(t) for t in r["watch"].index]}
    if include_holdings:
        sig["sell"] = [short(t) for t in r["sells"].index]
    with open(os.path.join(out, "signals.json"), "w") as f:
        json.dump(sig, f, indent=2)


def send_telegram(text):
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (tok and chat):
        return False
    data = urllib.parse.urlencode({"chat_id": chat, "text": text[:4000]}).encode()
    urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data, timeout=30)
    return True


def send_email(subject, text):
    host, to = os.environ.get("SMTP_HOST"), os.environ.get("EMAIL_TO")
    if not (host and to):
        return False
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, os.environ.get("SMTP_USER", to), to
    msg.set_content(text)
    with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", 587)), timeout=30) as s:
        s.starttls()
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
        s.send_message(msg)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers-file", default="my_stocks.txt")
    ap.add_argument("--holdings-file", default="holdings.txt")
    ap.add_argument("--near-pct", type=float, default=5.0)
    ap.add_argument("--ma", type=int, default=200)
    ap.add_argument("--data-start", default="2005-01-01")
    ap.add_argument("--out", default="docs")
    ap.add_argument("--notify", action="store_true", help="send Telegram/email")
    ap.add_argument("--always", action="store_true", help="notify even when nothing is new")
    ap.add_argument("--public", action="store_true",
                    help="leave holdings off the dashboard (use when it is published online)")
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()

    tickers = read_list(a.tickers_file)
    if not tickers and not a.synthetic:
        raise SystemExit(f"No stocks found in {a.tickers_file}")
    holdings = read_list(a.holdings_file) or [x for x in re.split(r"[,\s]+", os.environ.get("HOLDINGS", "")) if x]
    if not a.synthetic:
        tickers = [norm(t) for t in tickers]
        holdings = [norm(h) for h in holdings]
        tickers = list(dict.fromkeys(tickers + holdings))  # always include holdings

    prices = load_prices(tickers, a.data_start, a.synthetic)
    as_of, tbl = analyse(prices, a.ma, a.near_pct)
    age = (pd.Timestamp.now().normalize() - as_of).days
    if not a.synthetic and age > 5:
        raise SystemExit(f"Latest price data is {age} days old ({as_of.date()}). Data feed problem?")

    r = build_report(tbl, holdings, as_of)
    text = message_text(r, a.near_pct, a.ma)
    print(text)

    write_site(a.out, r, a.near_pct, a.ma, include_holdings=not a.public)
    print(f"\nDashboard written to {a.out}/index.html")

    if a.notify and (a.always or len(r["sells"]) or len(r["new"]) or len(r["near_ma"])):
        sent = []
        if send_telegram(text):
            sent.append("Telegram")
        if send_email(f"ATH scan {as_of.date()}", text):
            sent.append("email")
        print("Notified via: " + (", ".join(sent) if sent else "nothing (no credentials set)"))


if __name__ == "__main__":
    main()
