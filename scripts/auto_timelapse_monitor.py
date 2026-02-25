import cv2
import cv2.aruco as aruco
import numpy as np
import os
import time
import json
import sys
from datetime import datetime

# ==========================================================
# [ 腳本路徑與設定讀取 ]
# ==========================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def load_config():
    # 預設設定檔路徑
    default_config = os.path.join(SCRIPT_DIR, "configs", "exp_default_16x11.json")
    
    # 檢查是否有命令列參數指定設定檔
    config_path = sys.argv[1] if len(sys.argv) > 1 else default_config
    
    if not os.path.isabs(config_path):
        config_path = os.path.join(SCRIPT_DIR, config_path)

    if not os.path.exists(config_path):
        print(f"[錯誤] 找不到設定檔: {config_path}")
        sys.exit(1)

    with open(config_path, 'r', encoding='utf-8') as f:
        conf = json.load(f)
    
    print(f"[系統] 已載入實驗設定: {conf.get('experiment_name', '未命名實驗')}")
    print(f"[系統] 設定檔來源: {config_path}")
    return conf

CONFIG = load_config()

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
