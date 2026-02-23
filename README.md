# 咸豐草瘦果發芽自動化監測系統 (Bidens pilosa Germination Monitor)

本專案用於 2025 科展實驗，旨在透過 Raspberry Pi 與相機自動追蹤大爪草（咸豐草）瘦果的發芽進程，並計算 $T_{50}$ 等生理指標。

## 🛠 目前功能
* **多盤自動擷取**：透過 ArUco Marker (DICT_4X4_50) 定位 5 個培養皿，並自動執行透視校正。
* **定時縮時攝影**：支援每分鐘自動擷取一次 5 盤影像。
* **Master 座標映射**：以單一影像為基準鎖定 30 顆種子座標，解決動態偵測造成的種子身分錯置問題。
* **參數視覺化調校**：整合 OpenCV Slider 介面，可動態調整 Threshold 與 ROI 邊距。

## 📁 目錄結構與腳本說明

### 1. ArUco 標記準備 (`scripts/0_markers/`)
在實驗開始前，需準備好定位用的標記。
*   `gen_markers_pdf.py`: 自動生成含 20 個 ArUco 標記 (ID 0-19) 的 A4 PDF，直接列印即可使用。
*   `check_marker_ids.py`: 開啟相機即時檢測畫面上所有的 ArUco ID，用於確認列印品質與相機焦距。

### 2. 種子位置與實驗設計 (`scripts/1_setSeedsPosition/`)
*   `generate_staggered_map.py`: 生成 30 顆種子的「交錯式」排列圖與 `map_dish_X.csv` 紀錄表。
    *   **黑實心**：去芒組 (Treated)
    *   **黑空心**：未處理組 (Untreated)

### 3. 五盤全自動監測系統
本系統的核心監控邏輯。
*   `auto_timelapse_monitor.py`: **[最常用]** 每分鐘自動執行 5 盤定位、校正、切割與存擋。
*   `multi_dish_extractor.py`: 手動版監測工具，僅在按 `s` 時儲存當下可見的盤子影像。
*   `test_single_dish.py`: 專門針對 Dish_A (ID 0-3) 進行校正測試的小工具。

### 4. 後端種子切割處理
*   `master_seed_processor.py`: **[重要]** 讀取監測影像，讓使用者手動微調種子精準座標，並一次性對所有歷史影像進行「批次切割」。

## ⚙️ 黃金參數 (Current Master Config)
目前針對 Dish_A 調校出的最佳參數如下：

```json
{
    "threshold": 137,
    "min_area": 59,
    "max_area": 347,
    "margin_top": 164,
    "margin_bottom": 95,
    "margin_left": 90,
    "margin_right": 127
}
```

註：此參數已同步於 `scripts/config_Dish_A.json`。

## 🚀 實驗執行 SOP

### 第一階段：硬體佈署
1.  列印 `markers/` 下的標記 PDF 並裁切貼至培養皿底部邊緣（ID 0-3 對應左上、右上、右下、左下）。
2.  執行 `python3 scripts/0_markers/check_marker_ids.py` 確認所有盤子都能被辨識。
3.  執行 `python3 scripts/1_setSeedsPosition/generate_staggered_map.py` 參考圖示擺放種子並記錄 Treatment。

### 第二階段：自動縮時紀錄
啟動監控，系統會自動在 `temp_data/extracted_dishes` 下產生影像。
```bash
python3 scripts/auto_timelapse_monitor.py
```
*   按 `s` 手動儲存，按 `q` 安全退出。

### 第三階段：鎖定座標與批次切割
實驗結束後（或過程中），利用表現最好的一張盤面圖作為基準：
```bash
python3 scripts/master_seed_processor.py
```
*   調整 Slider 直到 30 顆種子都被綠框包覆且編號正確。
*   按 `s` 儲存座標，系統將自動處理該盤子的所有歷史影像，並將 30 顆種子的序列影像存於 `temp_data/time_series_crops/`。

## ⚠️ 注意事項
1. **光源一致性**：若環境光線大幅改變，需重新透過 `master_seed_processor.py` 調整 threshold。
2. **資料備份**：由於 `temp_data/` 已被 `.gitignore` 排除，請務必手動將生成的 `time_series_crops` 備份至外部硬碟。
