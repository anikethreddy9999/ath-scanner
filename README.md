# ATH momentum: backtest + daily scanner

Strategy: buy stocks within 5% of their all-time high (and above the 200 DMA);
exit when the close falls below the 200 DMA. Educational, not financial advice.

## 1. Backtest on real history (on your computer)

    pip install yfinance pandas numpy matplotlib
    python ath_backtest.py --tickers-file my_stocks.txt

Put your universe in `my_stocks.txt` (one NSE symbol per line). Read `trades.csv`
and the printed stats. Then try `--near-pct 2`, `--near-pct 10`, `--ma 100`,
`--max-positions 10`. If results only look good for one setting, be suspicious.

## 2. Run the scanner once

    python scanner.py --tickers-file my_stocks.txt --holdings-file holdings.txt

Open `docs/index.html` for the dashboard.

## 3. Automate it free with GitHub (no computer needed)

1. Create a **private** GitHub repo and upload everything in this folder
   (including `.github/workflows/daily-scan.yml`, `my_stocks.txt`, `holdings.txt`).
2. Telegram alerts: message @BotFather, send /newbot, copy the token. Send any
   message to your new bot, then open
   `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy the `chat` `id`.
3. Repo > Settings > Secrets and variables > Actions: add `TELEGRAM_BOT_TOKEN`
   and `TELEGRAM_CHAT_ID`. (Email is optional: `SMTP_HOST`, `SMTP_USER`,
   `SMTP_PASS`, `EMAIL_TO`.)
4. Repo > Settings > Pages > Source: **GitHub Actions**.
5. Actions tab > daily-scan > Run workflow to test. After that it runs every
   weekday at 16:00 IST.

Note: GitHub Pages sites are public. The workflow uses `--public`, so your
holdings never appear on the dashboard; sell alerts come via Telegram/email.
For a dashboard with holdings, run `scanner.py` locally and open the file.
