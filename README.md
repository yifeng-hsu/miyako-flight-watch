# 宮古島機票價格追蹤網站

自動追蹤桃園 `TPE` 往返宮古島下地島 `SHI` 的直飛經濟艙票價，固定比較：

- 2027-05-24 → 2027-05-27
- 2027-05-25 → 2027-05-28
- 4 位成人

網站顯示 4 人總價、每人估價、航空公司、航班、歷史最低價與價格折線圖。GitHub Actions 每天台灣時間約 09:05 自動查價並更新網站，符合提醒條件時透過 Telegram 傳送文字通知到手機。

## 網址形式

正式網址：

```text
https://yifeng-hsu.github.io/miyako-flight-watch/
```

## 部署步驟

### 1. 建立 SerpApi 金鑰

註冊 SerpApi 免費帳號並複製 API key。兩組日期每日查詢約使用 2–6 次額度，每月約 60–180 次，維持在每月 250 次的方案額度內。網站每 15 分鐘讀取一次已產生的 JSON 不會呼叫 SerpApi，也不會增加 API 用量。

### 2. 上傳專案到 GitHub

建立名稱為 `miyako-flight-watch` 的公開或私人 repository，將本專案全部檔案上傳到 `main` 分支。

### 3. 設定查價金鑰

進入 GitHub repository：

`Settings` → `Secrets and variables` → `Actions` → `New repository secret`

新增：

```text
Name: SERPAPI_KEY
Secret: 你的 SerpApi API key
```

可選設定：

- Repository variable `TARGET_TOTAL_TWD`：4 人目標總價，預設 `48000`
- Repository variable `DROP_ALERT_PERCENT`：降價提醒百分比，預設 `5`
- Secret `TELEGRAM_BOT_TOKEN` 與 `TELEGRAM_CHAT_ID`：啟用 Telegram 推播

### 4. 設定手機文字通知

手機通知使用 Telegram 機器人傳送純文字訊息，不需要開著網站：

1. 在 Telegram 搜尋 `@BotFather`，輸入 `/newbot` 建立機器人並保存 Bot Token。
2. 開啟剛建立的機器人，傳送 `/start`。
3. 取得 Chat ID，然後到 repository 的 `Settings` → `Secrets and variables` → `Actions` 新增：

   ```text
   TELEGRAM_BOT_TOKEN = BotFather 提供的 Token
   TELEGRAM_CHAT_ID = 你的 Chat ID
   ```

4. iPhone 到「設定」→「通知」→「Telegram」，開啟「允許通知」，並選擇鎖定畫面、通知中心與橫幅。

### 5. 開啟 GitHub Pages

進入：

`Settings` → `Pages` → `Build and deployment` → `Source: GitHub Actions`

再到 `Actions` 執行一次 **Miyako flight watch**，首次查價後網站就會上線。

## 本機測試

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export SERPAPI_KEY="你的金鑰"  # Windows PowerShell: $env:SERPAPI_KEY="你的金鑰"
python tracker.py
python -m http.server 8000 --directory docs
```

瀏覽器開啟 `http://localhost:8000`。

## 資料與提醒邏輯

資料保存在 `docs/data/prices.json`。Telegram 在下列情況推播：

- 首次查到可售票價
- 刷新歷史最低價
- 比前一次下降至少 5%
- 低於設定的 4 人目標總價

Telegram 只有符合以上條件時才傳送文字通知，不會因網頁重新整理而重複推播。

## 注意事項

- 搜尋結果是當下可見票價，不保證付款頁仍有相同艙等或座位數。
- 行李、選位及付款手續費可能未包含。
- GitHub 排程可能比設定時間延遲數分鐘。
- API 金鑰只能放在 GitHub Secrets，不要寫入程式或公開檔案。
