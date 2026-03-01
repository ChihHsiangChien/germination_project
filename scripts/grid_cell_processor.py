import cv2
import numpy as np
import os
import glob
import json
import sys

# ==========================================================
# [ 預設參數設定 ]
# ==========================================================
CONFIG = {
    "margin_top": 50,
    "margin_bottom": 50,
    "margin_left": 50,
    "margin_right": 50,
    "cols": 4,      # 4行 (Columns)
    "rows": 3,      # 3列 (Rows)
    "gap_x": 10,    # 網格間距 X
    "gap_y": 10     # 網格間距 Y
}

def print_ui_instructions():
    print("\n" + "="*50)
    print("      咸豐草實驗：覆土育苗盆 (4x3) 網格切割系統")
    print("="*50)
    print(" [ 操作說明 ]")
    print(" 1. 調整視窗上方 Slider，設定四邊邊界 (Margins) 排除非土壤區域。")
    print(" 2. 調整 Gap (X/Y) 以扣除穴位之間的塑膠隔板。")
    print(" 3. 確認 12 個網格綠框精確對準 4x3 的獨立穴孔。")
    print("\n [ 熱鍵功能 ]")
    print("  's' 鍵：鎖定網格座標 + 儲存參數 + 啟動全自動批次切割")
    print("  'q' 鍵：放棄並退出程式")
    print("="*50 + "\n")

def nothing(x):
    pass

def save_config(dish_label, current_params, project_root):
    # 將網格參數存入 configs 目錄
    config_dir = os.path.join(project_root, "scripts", "configs")
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, f"grid_{dish_label}.json")
    with open(config_path, 'w') as f:
        json.dump(current_params, f, indent=4)
    print(f"\n[系統] 參數檔已更新: {config_path}")

def run_grid_processor(image_name, dish_label=None):
    # 解析檔名取得基準時間與 Dish 標籤
    name_no_ext = os.path.splitext(image_name)[0]
    parts = name_no_ext.split('_')
    
    if dish_label is None:
        if len(parts) >= 3:
            dish_label = "_".join(parts[2:]) # e.g. "Dish_A"
        else:
            dish_label = "Unknown"
    
    # 紀錄基準時間點 (格式: YYYYMMDD_HHMMSS)
    start_timestamp = f"{parts[0]}_{parts[1]}" if len(parts) >= 2 else "00000000_000000"

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    image_path = os.path.join(project_root, "temp_data", "exp2_soil_tray", "extracted_dishes", image_name)
    
    img = cv2.imread(image_path)
    if img is None: 
        print(f"錯誤：找不到基準影像 {image_path}")
        print("請確認資料夾 temp_data/exp2_soil_tray/extracted_dishes/ 裡面有這張照片。")
        return

    # 顯示操作說明
    print_ui_instructions()

    win_name = 'Grid_Cell_Tuning'
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_name, 1000, 800)

    # 建立調整桿
    cv2.createTrackbar('M_Top', win_name, CONFIG["margin_top"], 300, nothing)
    cv2.createTrackbar('M_Bot', win_name, CONFIG["margin_bottom"], 300, nothing)
    cv2.createTrackbar('M_Left', win_name, CONFIG["margin_left"], 300, nothing)
    cv2.createTrackbar('M_Right', win_name, CONFIG["margin_right"], 300, nothing)
    cv2.createTrackbar('Gap_X', win_name, CONFIG["gap_x"], 100, nothing)
    cv2.createTrackbar('Gap_Y', win_name, CONFIG["gap_y"], 100, nothing)

    h, w = img.shape[:2]
    cols = CONFIG["cols"]
    rows = CONFIG["rows"]
    
    final_cells = []

    while True:
        # 讀取當下 Slider 參數
        params = {
            "margin_top": cv2.getTrackbarPos('M_Top', win_name),
            "margin_bottom": cv2.getTrackbarPos('M_Bot', win_name),
            "margin_left": cv2.getTrackbarPos('M_Left', win_name),
            "margin_right": cv2.getTrackbarPos('M_Right', win_name),
            "gap_x": cv2.getTrackbarPos('Gap_X', win_name),
            "gap_y": cv2.getTrackbarPos('Gap_Y', win_name),
            "cols": cols,
            "rows": rows
        }

        display_img = img.copy()
        overlay = display_img.copy()
        
        # 繪製半透明遮罩 (表示被裁切掉的邊界)
        m_top = params["margin_top"]
        m_bot = params["margin_bottom"]
        m_left = params["margin_left"]
        m_right = params["margin_right"]
        
        cv2.rectangle(overlay, (0, 0), (w, m_top), (40, 40, 40), -1)
        cv2.rectangle(overlay, (0, h-m_bot), (w, h), (40, 40, 40), -1)
        cv2.rectangle(overlay, (0, m_top), (m_left, h-m_bot), (40, 40, 40), -1)
        cv2.rectangle(overlay, (w-m_right, m_top), (w, h-m_bot), (40, 40, 40), -1)
        
        cv2.addWeighted(overlay, 0.5, display_img, 0.5, 0, display_img)

        # 計算內部工作區與網格座標
        work_w = w - m_left - m_right
        work_h = h - m_top - m_bot
        
        cells = []
        if work_w > 0 and work_h > 0:
            # 計算單一小方格的寬高 (扣掉間距)
            cell_w = (work_w - (cols - 1) * params["gap_x"]) // cols
            cell_h = (work_h - (rows - 1) * params["gap_y"]) // rows
            
            if cell_w > 0 and cell_h > 0:
                cell_idx = 1
                for r in range(rows):
                    for c in range(cols):
                        # 計算單一格的真實座標
                        x1 = m_left + c * (cell_w + params["gap_x"])
                        y1 = m_top + r * (cell_h + params["gap_y"])
                        x2 = x1 + cell_w
                        y2 = y1 + cell_h
                        
                        cells.append((cell_idx, x1, y1, x2, y2))
                        
                        # 畫出綠色網格
                        cv2.rectangle(display_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        # 標註穴孔編號 (cell_01 ~ cell_12)
                        cv2.putText(display_img, f"C{cell_idx:02d}", (x1 + 5, y1 + 25), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                        cell_idx += 1
                        
        final_cells = cells

        cv2.imshow(win_name, display_img)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'): 
            print("\n[系統] 使用者中止操作。")
            break
        elif key == ord('s'):
            if len(final_cells) == cols * rows:
                print(f"\n[系統] 偵測到 {len(final_cells)} 個有效穴孔。正在鎖定座標並執行批次切割...")
                save_config(dish_label, params, project_root)
                
                # 自動批次處理路徑
                input_dir = os.path.join(project_root, "temp_data", "exp2_soil_tray", "extracted_dishes")
                output_base = os.path.join(project_root, "temp_data", "exp2_soil_tray", "time_series_crops", dish_label)
                
                # 只過濾該 Dish，且時間在基準點之後的檔案
                all_images = sorted(glob.glob(os.path.join(input_dir, f"*{dish_label}.jpg")))
                images_to_process = []
                for img_path in all_images:
                    base_name = os.path.basename(img_path)
                    parts_current = base_name.split('_')
                    if len(parts_current) >= 2:
                        current_timestamp = f"{parts_current[0]}_{parts_current[1]}"
                        if current_timestamp >= start_timestamp:
                            images_to_process.append(img_path)

                print(f"[系統] 發現 {len(all_images)} 個該 Dish 的檔案，其中 {len(images_to_process)} 個在基準時間之後。")

                # 開始批次裁切
                for img_path in images_to_process:
                    base_name = os.path.basename(img_path)
                    parts_current = base_name.split('_')
                    if len(parts_current) >= 2:
                        timestamp = f"{parts_current[0]}_{parts_current[1]}"
                        batch_img = cv2.imread(img_path)
                        
                        if batch_img is not None:
                            for (c_idx, x1, y1, x2, y2) in final_cells:
                                cell_dir = os.path.join(output_base, f"cell_{c_idx:02d}")
                                os.makedirs(cell_dir, exist_ok=True)
                                crop = batch_img[y1:y2, x1:x2]
                                cv2.imwrite(os.path.join(cell_dir, f"{timestamp}.jpg"), crop)
                                
                        print(f"  > 處理完畢: {base_name}")
                
                print(f"\n[成功] 所有穴孔 (cell_01~cell_12) 最新縮時序列已存於: {output_base}")
                break
            else:
                print("\n[錯誤] 各項 Margin 或 Gap 值過大，導致小編格無法合理計算出面積。請縮小參數數值。")

    cv2.destroyAllWindows()

if __name__ == "__main__":
    target_image = None
    
    # 支援透過命令列直接指定檔名
    if len(sys.argv) > 1:
        target_image = sys.argv[1]
    else:
        # 自動搜尋 exp2 的 extracted_dishes 當中可用的第一張圖作為預設值
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        default_dir = os.path.join(project_root, "temp_data", "exp2_soil_tray", "extracted_dishes")
        if os.path.exists(default_dir):
            files = sorted(glob.glob(os.path.join(default_dir, "*.jpg")))
            if files:
                target_image = os.path.basename(files[0])
                print(f"[提示] 自動取用找到的第一張圖: {target_image}")
    
    if target_image:
        run_grid_processor(target_image)
    else:
        print("[錯誤] 未傳入指定圖片，且 temp_data/exp2_soil_tray/extracted_dishes 裡面沒有任何 jpg 照片。")
        print(">> 用法指示: python scripts/grid_cell_processor.py <檔名>")
