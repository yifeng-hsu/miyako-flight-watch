# 宮古島機票價格追蹤網站

自動追蹤桃園 `TPE` 往返宮古島下地島 `SHI` 的直飛經濟艙票價，固定比較：

- 2027-05-24 → 2027-05-27
- 2027-05-25 → 2027-05-28
- 4 位成人

網站顯示 4 人總價、每人估價、航空公司、航班、歷史最低價與價格折線圖。GitHub Actions 每天台灣時間約 09:05 自動查價並更新網站。

## 網址形式

正式網址：

```text
https://yifeng-hsu.github.io/miyako-flight-watch/
```

## 部署步驟

### 1. 建立 SerpApi 金鑰

註冊 SerpApi 免費帳號並複製 API key。兩組日期每日查詢約使用 4–6 次額度，免費方案一般足夠。

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

### 4. 開啟 GitHub Pages

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

## 注意事項

- 搜尋結果是當下可見票價，不保證付款頁仍有相同艙等或座位數。
- 行李、選位及付款手續費可能未包含。
- GitHub 排程可能比設定時間延遲數分鐘。
- API 金鑰只能放在 GitHub Secrets，不要寫入程式或公開檔案。
