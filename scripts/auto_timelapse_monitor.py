import cv2
import cv2.aruco as aruco
import numpy as np
import os
import time
from datetime import datetime

# ==========================================================
# [ 集中參數設定區 ]
# ==========================================================
CONFIG = {
    "interval_minutes": 1,        # 抓圖頻率 (分鐘)
    # 使用固定 ID 路徑，確保重開機後依然能鎖定 V4K
    "camera_id": "/dev/v4l/by-id/usb-IPEVO_Corp._IPEVO_V4K_01.00.00-video-index0",
    "frame_width": 1600,          # 相機解析度寬
    "frame_height": 1200,         # 相機解析度高
    "dish_width": 800,            # 輸出盤子影像寬 (像素)
    "dish_height": 575,           # 輸出盤子影像高 (像素)
    "output_folder": "temp_data/extracted_dishes",
    
    # 盤子 ID 與顏色配置 (0-3 為 A, 4-7 為 B...)
    "dishes": {
        'Dish_A': {'ids': [0, 1, 2, 3],    'color': (0, 255, 0)},   # 綠
        'Dish_B': {'ids': [4, 5, 6, 7],    'color': (255, 255, 0)}, # 青
        'Dish_C': {'ids': [8, 9, 10, 11],  'color': (255, 0, 255)}, # 紫
        'Dish_D': {'ids': [12, 13, 14, 15], 'color': (0, 165, 255)}, # 橘
        'Dish_E': {'ids': [16, 17, 18, 19], 'color': (0, 0, 255)}    # 紅
    }
}

def print_ui_instructions():
    interval_sec = CONFIG["interval_minutes"] * 60
    print("\n" + "╔" + "═"*58 + "╗")
    print(f"║ {'咸豐草實驗：五盤全自動縮時監測系統 (4.13.0)':^44} ║")
    print("╠" + "═"*58 + "╣")
    print(f"║ [ 運作模式 ] 每 {CONFIG['interval_minutes']} 分鐘 ({interval_sec} 秒) 自動擷取 ║")
    print(f"║ [ 解析度 ]   {CONFIG['frame_width']} x {CONFIG['frame_height']} {' ':<23} ║")
    print(f"║ [ 設備路徑 ] V4K (Persistent ID) {' ':<25} ║")
    print("╠" + "═"*58 + "╣")
    print("║ [ 熱鍵 ] {' ':<47} ║")
    print("║  'q' 鍵 : 安全停止程式並關閉相機 {' ':<23} ║")
    print("║  's' 鍵 : 立即手動執行存檔 {' ':<31} ║")
    print("╚" + "═"*58 + "╝\n")

def run_auto_monitor():
    # --- 1. 初始化資料夾 ---
    script_path = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(script_path))
    output_dir = os.path.join(project_root, CONFIG["output_folder"])
    if not os.path.exists(output_dir): os.makedirs(output_dir)

    # --- 2. 相機與 ArUco 初始化 (使用 OpenCV 4.13.0 新語法) ---
    cap = cv2.VideoCapture(CONFIG["camera_id"], cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CONFIG["frame_width"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CONFIG["frame_height"])

    # 4.13.0 新式偵測器建立方式
    aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
    parameters = aruco.DetectorParameters()
    detector = aruco.ArucoDetector(aruco_dict, parameters)

    W, H = CONFIG["dish_width"], CONFIG["dish_height"]
    dst_pts = np.array([[0,0], [W-1,0], [W-1,H-1], [0,H-1]], dtype=np.float32)

    last_capture_time = 0
    interval_sec = CONFIG["interval_minutes"] * 60
    
    print_ui_instructions()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[錯誤] 無法讀取相機，請檢查 V4K 硬體連線")
                break

            current_time = time.time()
            display_frame = frame.copy()
            
            # 4.13.0 新式偵測語法
            corners, ids, rejected = detector.detectMarkers(frame)
            
            ready_to_save = {}
            status_list = []

            if ids is not None:
                # 建立標記中心索引
                marker_centers = {int(mid[0]): np.mean(c[0], axis=0) for c, mid in zip(corners, ids)}
                
                # 畫出偵測點 (方便除錯)
                aruco.drawDetectedMarkers(display_frame, corners, ids)

                for name, cfg in CONFIG["dishes"].items():
                    target_ids = cfg['ids']
                    color = cfg['color']
                    
                    if all(tid in marker_centers for tid in target_ids):
                        src_pts = np.array([marker_centers[tid] for tid in target_ids], dtype=np.float32)
                        
                        # 繪製主畫面框線
                        pts_display = src_pts.astype(np.int32).reshape((-1, 1, 2))
                        cv2.polylines(display_frame, [pts_display], True, color, 3)
                        cv2.putText(display_frame, f"{name} OK", (int(src_pts[0][0]), int(src_pts[0][1]-15)), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                        
                        # 透視校正
                        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
                        ready_to_save[name] = cv2.warpPerspective(frame, M, (W, H))
                        status_list.append(f"{name}:OK")
                    else:
                        status_list.append(f"{name}:LOSS")
            else:
                for name in CONFIG["dishes"]: status_list.append(f"{name}:NO_MARK")

            # 定時抓圖邏輯
            elapsed = current_time - last_capture_time
            if elapsed >= interval_sec:
                if ready_to_save:
                    ts = time.strftime("%Y%m%d_%H%M%S")
                    for name, img in ready_to_save.items():
                        cv2.imwrite(os.path.join(output_dir, f"{ts}_{name}.jpg"), img)
                    
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 自動存檔 | {' | '.join(status_list)}")
                    last_capture_time = current_time

            # 顯示預覽
            preview = cv2.resize(display_frame, (1024, 768))
            countdown = int(max(0, interval_sec - elapsed))
            cv2.putText(preview, f"Next Save: {countdown}s", (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.imshow('Auto Monitor System (v4.13.0)', preview)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                if ready_to_save:
                    ts = time.strftime("%Y%m%d_%H%M%S")
                    for name, img in ready_to_save.items():
                        cv2.imwrite(os.path.join(output_dir, f"{ts}_{name}.jpg"), img)
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 手動存檔成功")

    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    run_auto_monitor()
