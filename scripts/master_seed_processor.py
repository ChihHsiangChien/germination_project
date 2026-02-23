import cv2
import numpy as np
import os
import glob
import json

CONFIG = {
    "threshold": 137,
    "min_area": 59,
    "max_area": 347,
    "margin_top": 164,
    "margin_bottom": 95,
    "margin_left": 90,
    "margin_right": 127,
    "crop_size": 32,
}

def print_ui_instructions():
    print("\n" + "="*50)
    print("      咸豐草實驗：種子 Master 影像處理系統")
    print("="*50)
    print(" [ 操作說明 ]")
    print(" 1. 調整視窗上方 Slider，直到所有種子都被綠框標記。")
    print(" 2. 觀察編號：確保 Z 字型順序 (1-30) 符合實驗設計。")
    print(" 3. 調整邊界：利用 M_Top/Bottom/Left/Right 徹底排除 Marker。")
    print("\n [ 熱鍵功能 ]")
    print("  's' 鍵：鎖定當前座標 + 儲存參數 + 啟動全自動批次切割")
    print("  'q' 鍵：放棄並退出程式")
    print("="*50 + "\n")

def nothing(x):
    pass

def save_config(dish_label, current_params, project_root):
    config_path = os.path.join(project_root, "scripts", f"config_{dish_label}.json")
    with open(config_path, 'w') as f:
        json.dump(current_params, f, indent=4)
    print(f"\n[系統] 參數檔已更新: {config_path}")

def run_master_processor(image_name, dish_label='Dish_A'):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    image_path = os.path.join(project_root, "temp_data", "extracted_dishes", image_name)
    
    img = cv2.imread(image_path)
    if img is None: 
        print(f"錯誤：找不到基準影像 {image_path}")
        return

    # 啟動時顯示操作說明
    print_ui_instructions()

    win_name = 'Seed_Master_Tuning'
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_name, 1000, 800)

    # 建立調整桿
    cv2.createTrackbar('Thresh', win_name, CONFIG["threshold"], 255, nothing)
    cv2.createTrackbar('MinArea', win_name, CONFIG["min_area"], 500, nothing)
    cv2.createTrackbar('MaxArea', win_name, CONFIG["max_area"], 3000, nothing)
    cv2.createTrackbar('M_Top', win_name, CONFIG["margin_top"], 350, nothing)
    cv2.createTrackbar('M_Bottom', win_name, CONFIG["margin_bottom"], 350, nothing)
    cv2.createTrackbar('M_Left', win_name, CONFIG["margin_left"], 350, nothing)
    cv2.createTrackbar('M_Right', win_name, CONFIG["margin_right"], 350, nothing)

    master_centers = []

    while True:
        # 讀取當前 Slider 參數
        params = {
            "threshold": cv2.getTrackbarPos('Thresh', win_name),
            "min_area": cv2.getTrackbarPos('MinArea', win_name),
            "max_area": cv2.getTrackbarPos('MaxArea', win_name),
            "margin_top": cv2.getTrackbarPos('M_Top', win_name),
            "margin_bottom": cv2.getTrackbarPos('M_Bottom', win_name),
            "margin_left": cv2.getTrackbarPos('M_Left', win_name),
            "margin_right": cv2.getTrackbarPos('M_Right', win_name),
            "crop_size": CONFIG["crop_size"]
        }

        # 影像預處理
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, params["threshold"], 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        display_img = img.copy()
        h, w = img.shape[:2]
        
        # 繪製半透明遮罩
        overlay = display_img.copy()
        cv2.rectangle(overlay, (0, 0), (w, params["margin_top"]), (40, 40, 40), -1)
        cv2.rectangle(overlay, (0, h-params["margin_bottom"]), (w, h), (40, 40, 40), -1)
        cv2.rectangle(overlay, (0, params["margin_top"]), (params["margin_left"], h-params["margin_bottom"]), (40, 40, 40), -1)
        cv2.rectangle(overlay, (w-params["margin_right"], params["margin_top"]), (w, h-params["margin_bottom"]), (40, 40, 40), -1)
        cv2.addWeighted(overlay, 0.5, display_img, 0.5, 0, display_img)

        current_centers = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            bx, by, bw, bh = cv2.boundingRect(cnt)
            cx, cy = bx + bw//2, by + bh//2

            if params["margin_left"] < cx < (w - params["margin_right"]) and \
               params["margin_top"] < cy < (h - params["margin_bottom"]):
                if params["min_area"] < area < params["max_area"]:
                    current_centers.append((cx, cy))
                    cv2.rectangle(display_img, (bx, by), (bx + bw, by + bh), (0, 255, 0), 2)

        # 重新排序 Z 字型
        if current_centers:
            current_centers.sort(key=lambda p: p[1])
            sorted_centers = []
            row = []; last_y = current_centers[0][1]
            for p in current_centers:
                if p[1] - last_y < 55: row.append(p)
                else:
                    row.sort(key=lambda p: p[0]); sorted_centers.extend(row)
                    row = [p]; last_y = p[1]
            row.sort(key=lambda p: p[0]); sorted_centers.extend(row)
            
            for i, pt in enumerate(sorted_centers):
                cv2.putText(display_img, str(i+1), (pt[0]-10, pt[1]-15), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
            master_centers = sorted_centers

        cv2.imshow(win_name, display_img)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'): 
            print("\n[系統] 使用者中止操作。")
            break
        elif key == ord('s'):
            if len(master_centers) > 0:
                print(f"\n[系統] 偵測到 {len(master_centers)} 個種子。正在鎖定座標並執行批次切割...")
                save_config(dish_label, params, project_root)
                
                # 自動批次處理邏輯
                input_dir = os.path.join(project_root, "temp_data", "extracted_dishes")
                output_base = os.path.join(project_root, "temp_data", "time_series_crops", dish_label)
                images = sorted(glob.glob(os.path.join(input_dir, f"*{dish_label}.jpg")))
                
                for img_path in images:
                    base_name = os.path.basename(img_path)
                    parts = base_name.split('_')
                    timestamp = f"{parts[0]}_{parts[1]}"
                    batch_img = cv2.imread(img_path)
                    
                    for i, (cx, cy) in enumerate(master_centers):
                        seed_dir = os.path.join(output_base, f"seed_{i+1:02d}")
                        os.makedirs(seed_dir, exist_ok=True)
                        s = params["crop_size"]
                        crop = batch_img[max(0,cy-s):cy+s, max(0,cx-s):cx+s]
                        cv2.imwrite(os.path.join(seed_dir, f"{timestamp}.jpg"), crop)
                    print(f"  > 處理完畢: {base_name}")
                
                print(f"\n[成功] 所有種子縮時序列已存於: {output_base}")
                break
            else:
                print("\n[錯誤] 畫面中沒有綠框，請調整 Slider 直到種子被偵測。")

    cv2.destroyAllWindows()

if __name__ == "__main__":
    # 使用 30 顆最全的那張圖作為 Master 基準
    run_master_processor("20260222_191223_Dish_A.jpg", "Dish_A")
