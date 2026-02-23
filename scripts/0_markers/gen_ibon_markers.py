import cv2
import numpy as np
import cv2.aruco as aruco
import os

# --- 自動偵測專案路徑 ---
# 取得腳本自己所在的位置 (scripts 目錄)
script_path = os.path.abspath(__file__)
# 取得專案根目錄 (germination_project)
project_root = os.path.dirname(os.path.dirname(script_path))
# 設定正確的 markers 資料夾路徑
output_dir = os.path.join(project_root, "markers")

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

output_path = os.path.join(output_dir, 'ibon_markers_v10.png')

# --- 設定列印參數 (300 DPI) ---
DPI = 300
CM_TO_INCH = 2.54
A4_W, A4_H = 2480, 3508 

# Marker 2.0cm (236 px)
MARKER_PIX = int((2.0 / CM_TO_INCH) * DPI) 

canvas = np.ones((A4_H, A4_W), dtype=np.uint8) * 255
dictionary = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)

# --- 精確分配空間 ---
MARGIN_X = 250
# 第一組從 200 開始，第二組從 1950 開始 (確保中間有超過 200px 的緩衝區)
SET_START_Y = [200, 1950] 
ROW_GAP = 300 # 每列間距 (縮小一點，增加容錯)
COL_GAP = 500

for idx, start_y in enumerate(SET_START_Y):
    # 畫分隔線 (僅在第二組上方)
    if idx > 0:
        line_y = start_y - 180
        cv2.line(canvas, (150, line_y), (A4_W - 150, line_y), (180), 3)
    
    # 畫組別標籤
    cv2.putText(canvas, f"SET {idx + 1} (ID 0-19)", (MARGIN_X, start_y - 80), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0), 3)

    for i in range(20):
        row = i // 4
        col = i % 4
        
        marker_img = aruco.generateImageMarker(dictionary, i, MARKER_PIX)
        y_pos = start_y + (row * ROW_GAP)
        x_pos = MARGIN_X + (col * COL_GAP)
        
        # 最終檢查防止邊界報錯
        if y_pos + MARKER_PIX < A4_H:
            canvas[y_pos : y_pos + MARKER_PIX, x_pos : x_pos + MARKER_PIX] = marker_img
            # 標註 ID
            cv2.putText(canvas, f"ID:{i}", (x_pos, y_pos - 15), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0), 2)

# 儲存到指定路徑
output_path = os.path.join(output_dir, 'ibon_markers_v10.png')
cv2.imwrite(output_path, canvas)

print(f"--- 處理完成 ---")
print(f"檔案已成功儲存至: {output_path}")
print(f"排版更新：SET 1 與 SET 2 之間已預留大量空間，無重疊風險。")
