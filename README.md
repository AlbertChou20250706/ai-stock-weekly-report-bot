# AI 股市週報自動化

用 GitHub Actions 排程（cron + 手動 `workflow_dispatch`）驅動：抓台股資料 → Claude API 生成週報 → LINE Messaging API 推播。

完整技術規劃與背景說明見 content-hub 的紀錄：
https://github.com/AlbertChou20250706/content-hub/tree/main/topics/2026-08-27_ai-stock-weekly-report-line-bot

> ⚠️ 免責聲明（每次生成內容都固定附上，見 `prompts/system_prompt.md`）：
> 投資一定有風險，基金/ETF/股票投資有賺有賠，以上資訊非投資建議

## 架構

```
src/fetch_data.py      抓 config/watchlist.json 裡的標的（yfinance），輸出 data/latest.json
src/generate_report.py 讀 data/latest.json + prompts/system_prompt.md，呼叫 Claude API 生成週報
                        → 存檔到 reports/YYYY-MM-DD.md，並寫一份到 output/report.txt
src/send_line.py       讀 output/report.txt，push 給 LINE_PUSH_TARGET_IDS 裡的每個目標
src/notify_failure.py  任一步驟失敗時，發一則簡短告警訊息
```

`.github/workflows/weekly-stock-report.yml` 每週一台灣時間 08:00 自動跑一次，也可以在 GitHub 網頁上手動點 **Run workflow** 臨時觸發。

## 目前狀態：個人測試模式

`LINE_PUSH_TARGET_IDS` 目前應該填**你自己的 LINE User ID**（U 開頭），先驗證整條流程穩定，之後才切換成正式群組的 Group ID（C 開頭，可用逗號分隔多個）。詳見 content-hub 那篇規劃文件的「Bot 與群組導入策略」。

## 設定 GitHub Secrets

Settings → Secrets and variables → Actions，新增：

| Secret | 說明 |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key |
| `LINE_CHANNEL_ACCESS_TOKEN` | 沿用既有 ChouAP.Cloud channel 的 long-lived token |
| `LINE_PUSH_TARGET_IDS` | 個人測試階段填自己的 User ID；正式階段換成群組 Group ID（逗號分隔多個） |

## 本機測試

```bash
cp .env.example .env   # 填入真實值，.env 已加入 .gitignore 不會被 commit
pip install -r requirements.txt
export $(cat .env | xargs)   # 或用你習慣的方式載入環境變數
python src/fetch_data.py
python src/generate_report.py
python src/send_line.py
```

## 資料來源

預設用 [yfinance](https://pypi.org/project/yfinance/) 抓 `config/watchlist.json` 裡設定的大盤指數與 ETF 觀察清單，watchlist 可自行編輯調整，不用改程式碼。
