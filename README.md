# 宮古島機票價格追蹤網站

自動追蹤桃園 `TPE` 往返宮古島下地島 `SHI` 的直飛經濟艙票價，固定比較：

- 2027-05-24 → 2027-05-27
- 2027-05-25 → 2027-05-28
- 4 位成人

網站顯示 4 人總價、每人估價、航空公司、航班、歷史最低價與價格折線圖。GitHub Actions 每天台灣時間約 09:05 自動查價並更新網站。頁面也提供繁體中文試聽與新資料播報；真正的手機背景提醒使用 Telegram 推播搭配 iPhone Siri 播報。

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

### 4. 設定 iPhone 自動播報

網頁上的「開啟並試聽」適合頁面開啟中或重新回到前景時使用。iOS 會暫停已關閉或長時間在背景的普通網頁，因此要在鎖定畫面、其他 App 或螢幕關閉時自動播報，請使用 Telegram＋Siri：

1. 在 Telegram 搜尋 `@BotFather`，輸入 `/newbot` 建立機器人並保存 Bot Token。
2. 開啟剛建立的機器人，傳送 `/start`。
3. 取得 Chat ID，然後到 repository 的 `Settings` → `Secrets and variables` → `Actions` 新增：

   ```text
   TELEGRAM_BOT_TOKEN = BotFather 提供的 Token
   TELEGRAM_CHAT_ID = 你的 Chat ID
   ```

4. iPhone 到「設定」→「輔助使用」→「Siri」→開啟「透過揚聲器播報通知」。
5. 再到「設定」→「通知」→「播報通知」。如果 App 清單中有 Telegram，開啟 Telegram 並選擇所有通知。
6. 使用 AirPods 或 CarPlay 時，也可在同一個「播報通知」頁面開啟耳機或 CarPlay 播報。

Apple 官方說明：

- [讓 Siri 透過 iPhone 揚聲器播報通知](https://support.apple.com/zh-tw/guide/iphone/iphaff1d606/ios)
- [使用 Siri 播報通知](https://support.apple.com/zh-tw/guide/iphone/iph838fd6fd4/ios)
- [AirPods 或 Beats 播報通知](https://support.apple.com/zh-tw/102536)

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

Telegram 只有符合以上條件時才通知，不會因網頁重新整理而重複推播。網頁語音偏好只保存在該支手機的瀏覽器中，不會上傳任何個人資料。

## 注意事項

- 搜尋結果是當下可見票價，不保證付款頁仍有相同艙等或座位數。
- 行李、選位及付款手續費可能未包含。
- GitHub 排程可能比設定時間延遲數分鐘。
- API 金鑰只能放在 GitHub Secrets，不要寫入程式或公開檔案。
