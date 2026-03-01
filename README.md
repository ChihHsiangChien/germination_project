# 咸豐草瘦果發芽自動化監測系統 (Bidens pilosa Germination Monitor)

本專案用於 2025 科展實驗，旨在透過 Raspberry Pi 與相機自動追蹤大爪草（咸豐草）瘦果的發芽進程，並計算 $T_{50}$ 等生理指標。

## 🛠 目前功能
* **多盤自動擷取**：透過 ArUco Marker (DICT_4X4_50) 定位 5 個培養皿，並自動執行透視校正。
* **定時縮時攝影**：支援每分鐘自動擷取一次 5 盤影像。
* **Master 座標映射**：以單一影像為基準鎖定 30 顆種子座標，並自動過濾同盤且晚於基準點的影像進行批次切割。
* **每日成長矩陣生成**：自動將種子縮時影像排列為固定時間網格 (10 分鐘一格) 的橫式佈局，便於跨日期對照發芽關鍵點。
* **PDF 實驗報告導出**：按 Dish 將所有種子的每日成長矩陣編譯成 PDF 報告，方便系統性查閱。
* **參數視覺化調校**：整合 OpenCV Slider 介面，可動態調整 Threshold 與 ROI 邊距。

## 📁 目錄結構與腳本說明

### 1. ArUco 標記準備 (`scripts/0_markers/`)
在實驗開始前，需準備好定位用的標記。
*   `gen_markers_pdf.py`: 自動生成含 20 個 ArUco 標記 (ID 0-19) 的 A4 PDF，直接列印即可使用。
*   `check_marker_ids.py`: 開啟相機即時檢測畫面上所有的 ArUco ID，用於確認列印品質與相機焦距。
*   `find_camera.py`: **[新工具]** 掃描並開啟系統中所有的相機 Index，協助確認 `camera_id` 該填什麼。

### 2. 種子位置與實驗設計 (`scripts/1_setSeedsPosition/`)
*   `generate_staggered_map.py`: 生成 30 顆種子的「交錯式」排列圖與 `map_dish_X.csv` 紀錄表。
    *   **黑實心**：去芒組 (Treated)
    *   **黑空心**：未處理組 (Untreated)

### 3. 五盤全自動監測系統
本系統的核心監控邏輯，支援載入不同實驗的設定檔。
*   `auto_timelapse_monitor.py`: **[最常用]** 每分鐘自動執行多盤定位、校正、切割與存擋。支援參數指定設定檔。
*   `multi_dish_extractor.py`: 手動版監測工具，僅在按 `s` 時儲存當下可見的盤子影像。
*   `test_single_dish.py`: 專門針對 Dish_A (ID 0-3) 進行校正測試的小工具。

### 4. 實驗設定檔系統 (`scripts/configs/`)
為了支援不同規格（長寬比、Marker ID）的盤子，系統採用 JSON 設定檔：
*   `exp_default_16x11.json`: **預設設定**，適用於標準 16:11.5 比例的長方形盤子。
*   `template_new_exp.json`: 新實驗範本，可用於設定不同的寬高（如正方形盤子）與 Marker ID 組。

### 5. 後端種子切割處理
*   `master_seed_processor.py`: **[重要]** 讀取監測影像，讓使用者手動微調種子精準座標。支援命令列傳入特定影像，並依據該影像時間自動過濾後續圖檔進行批次處理。

### 6. 視覺化分析與對照
*   `daily_seed_montage_generator.py`: 讀取切割後的種子序列，按日期生成 18x8 (10 分鐘一格) 的橫式成長大圖，確保特定時間出現在固定座標。
*   `seed_lifecycle_montage.py`: **[新功能]** 將單一種子的所有歷史影像合稱為一張長時序大圖，支援透過變數設定起訖時間，方便觀察單一粒種子的完整發芽行為。

### 7. 自動化報告生成
*   `montages_to_pdf.py`: **[新功能]** 將 `daily_montages/` 下的大圖按 Dish 進行封裝，依 seed 編號依序存入單一 PDF，作為最終實驗報告。

### 8. 覆土出苗實驗專用 (Experiment 2: Soil Tray)
這組腳本專為了有覆土、需要 4x3 網格固定切割的試驗設計，資料儲存於 `temp_data/exp2_soil_tray/`：
*   `grid_cell_processor.py`: **[新功能]** 讀取透視圖，透過 GUI 調整 4x3 穴孔網格，過濾塑膠隔板與邊界，將影像一鍵批次切割成 12 個穴位的縮時序列 (`cell_01` ~ `cell_12`)。
*   `daily_cell_montage_generator.py`: **[新功能]** 讀取切割好的 `cell` 照片序列，按日期生成 24x12 (5 分鐘一格) 的每日成長大圖。
*   `cell_montages_to_pdf.py`: **[新功能]** 將每日出苗大圖封裝成 PDF 以供人工進行發芽判定。

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
2.  **確認相機 ID**：
    *   **Linux/Pi**：執行 `ls /dev/v4l/by-id/` 尋找含 `V4K` 字樣的長路徑（最穩定）。
    *   **Windows/通用**：執行 `python3 scripts/find_camera.py` 查看 V4K 對應的 Index (如 0, 1...)。
    *   將找到的 ID 填入 `scripts/configs/` 對應的 JSON 設定檔中。
3.  執行 `python3 scripts/0_markers/check_marker_ids.py` 確認所有盤子都能被辨識。
4.  執行 `python3 scripts/1_setSeedsPosition/generate_staggered_map.py` 參考圖示擺放種子並記錄 Treatment。

### 第二階段：自動縮時紀錄
啟動監控，系統會自動在 `temp_data` 下產生影像（路徑由設定檔決定）。
```bash
# 方式 A：使用預設設定 (16x11 規格)
python3 scripts/auto_timelapse_monitor.py

# 方式 B：指定特定實驗設定檔 (例如新規格盤子)
python3 scripts/auto_timelapse_monitor.py configs/my_new_experiment.json
```
*   按 `s` 手動儲存，按 `q` 安全退出。

### 第三階段：鎖定座標與批次切割
當種子位置可能因操作或震動位移時，可針對該時間點後的影像重新鎖定座標：
```bash
# 指定特定的基準影像 (系統會自動過濾該時間點之後的影像)
python3 scripts/master_seed_processor.py 20260228_082402_Dish_A.jpg
```
*   調整 Slider 直到 30 顆種子都被綠框包覆且編號正確。
*   按 `s` 儲存座標並啟動批次處理，影像將存於 `temp_data/time_series_crops/{Dish}/{Seed}/`。

### 第四階段：生成每日成長矩陣
為了快速檢查發芽狀況，生成固定網格的大圖：
```bash
python3 scripts/daily_seed_montage_generator.py
```
*   生成的大圖位於 `temp_data/daily_montages/`。
*   **佈局特點**：橫式 18x8 矩陣，每格代表 10 分鐘，每一橫列代表 3 小時。相同時間點永遠位於相同座標。

### 第五階段：進階生命週期分析
若需觀察單一種子跨日期的連續變化：
```bash
python3 scripts/seed_lifecycle_montage.py
```
*   **自訂範圍**：請修改腳本內的 `FILTER_CONFIG` 變數來調整時間區間。
*   生成的大圖位於 `temp_data/lifecycle_montages/`。

### 第六階段：彙整 PDF 報告
將所有視覺化結果整合為方便閱讀的 PDF：
```bash
python3 scripts/montages_to_pdf.py
```
*   生成的 PDF 位於 `temp_data/exp1_dish/reports_pdf/`。
*   每個 Dish 會有一個專屬 PDF，依 seed_01 ~ seed_30 順序排列。

### 第七階段：覆土實驗分析 (Experiment 2: Soil Tray)
若是進行含有土壤的育苗盆實驗，請替換上述第三、四、五階段操作：
1. **網格切割**：執行 `python3 scripts/grid_cell_processor.py` 進行 4x3 格線裁切。
2. **單日大圖生成**：執行 `python3 scripts/daily_cell_montage_generator.py` 生成排版良好的每日觀察圖 (`temp_data/exp2_soil_tray/daily_montages/`)。
3. **輸出 PDF 報告**：執行 `python3 scripts/cell_montages_to_pdf.py`，會輸出每穴孔連續變化的多頁 PDF (`temp_data/exp2_soil_tray/reports_pdf/`)，供人工進行破土時間判定。

## ⚠️ 注意事項
1. **光源一致性**：若環境光線大幅改變，需重新透過 `master_seed_processor.py` 調整 threshold。
2. **設定檔優先**：若要進行不同比例的實驗，請務必先在 `scripts/configs/` 建立對應的 JSON，避免影像長寬比被錯誤校正（擠壓或拉伸）。
3. **資料備份**：由於 `temp_data/` 已被 `.gitignore` 排除，請務必手動將生成的結果備份至外部硬碟。


土壤組遠端拉回
rsync -avz --progress -e "ssh -J user@IP1" student@IP2:~/germination_project/temp_data/extracted_dishes/ /home/pancala/Documents/germination_project/temp_data/exp2_soil_tray/extracted_dishes/
