# Kemono 視頻高級自選下載器

*支持多影片勾選、暗色現代介面、PySide6 GUI免命令列*  
（如有需要請自行添加真實使用介面截圖↑）

---

## 主要特點

- 支援 [kemono.su](https://kemono.su/) 「Fanbox」貼文影片（mp4/mov）下載  
- 通過「分析」→ 多影片列表顯示 → 自由勾選下載目標  
- 每部影片自動用「發表日期+原文件名」命名，儲存於指定資料夾  
- 完整現代暗色 UI（仿 VSCode/Mac 風，適合夜間長時間使用）  
- 操作流暢不卡 UI，進度支持  
- 打包後 exe 新機直接用（內建chromium與所有依賴）

---

## 環境需求

- Windows 10/11  
- Python 3.8+（若僅用exe則無需安裝python）
- **如需自行打包請先安裝：**
  ```bash
  pip install PySide6 playwright beautifulsoup4 requests
  playwright install chromium
  pip install pyinstaller
  ```

---

## 使用方法

### **執行方式一：使用單檔 exe**

1. 下載 `kemono_bulk_xxx.exe`（【*注意*：需作者自行打包，或使用下述打包教學產生】）
2. 直接雙擊打開
3. 貼上 Kemono 訊息頁網址 (如：https://kemono.su/fanbox/user/.../post/xxxxxxx)
4. 點擊「分析」
5. 選擇需下載的影片點「開始下載」
6. 可改保存位置於任意本機資料夾
7. 下載日誌與進度條可於下方查看進度

### **執行方式二：源碼運行**

適合自己想要二次開發、測試、再打包exe

```bash
# 1. 安裝依賴
pip install PySide6 playwright beautifulsoup4 requests
playwright install chromium

# 2. 執行主程式
python kemono_bulk_v2.py
```

---

## 打包成真正的單檔exe（開發&維護者用）

### 一鍵打包
> 請確保你的機器已安裝好chromium（`playwright install chromium`後本地有`ms-playwright`資料夾）

```bash
pyinstaller --noconfirm --onefile --add-data "C:\Users\你的用戶名\AppData\Local\ms-playwright;ms-playwright" kemono_bulk_v2.py
```
> ⚠️ 請將上面"C:\Users\你的用戶名\..."改為你的真實帳戶！

### 可用dist/資料夾下的exe單獨分發，即可脫離Python環境運作。
---

## 常見問題

- **"未能自動找到chromium內核" 錯誤？**  
  → 請確保打包時正確 --add-data 了`ms-playwright`全資料夾（內含chrome.exe等）。
- **分析貼文時會卡頓/UI凍結？**  
  → 本軟體已全面子線程分析不卡UI，如還卡請升級顯示卡驅動或回報問題。
- **新版Kemono結構變動導致無法提取？**  
  → 請發issue附網址與頁面元素截圖，開源可快速修補！

---

## 聯絡 & 貢獻

- 有問題或想提需改進請開 Issue
- 歡迎 PR、或自訂主題色再提供給社群

---

## 聲明

本軟體僅供學術 & 私人技術用途，請勿用於商業侵權下載。使用前請自覺遵守目標站點相關法律政策！
