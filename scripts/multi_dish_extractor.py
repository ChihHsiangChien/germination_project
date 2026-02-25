import cv2
import cv2.aruco as aruco
import numpy as np
import os
import time
import json
import sys

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

def run_multi_dish_monitor():
    cfg_data = load_config()
    
    # --- 1. 路徑與資料夾初始化 ---
    project_root = os.path.dirname(SCRIPT_DIR)
    output_base_dir = os.path.join(project_root, cfg_data["output_folder"])
    if not os.path.exists(output_base_dir): os.makedirs(output_base_dir)

    # --- 2. 相機設定 (使用設定檔中的參數) ---
    v4k_path = cfg_data["camera_id"]
    cap = cv2.VideoCapture(v4k_path, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg_data["frame_width"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg_data["frame_height"])

    # --- 3. ArUco 偵測器設定 ---
    aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
    parameters = aruco.DetectorParameters()
    detector = aruco.ArucoDetector(aruco_dict, parameters)

    # 輸出規格 (從設定檔讀取)
    W, H = cfg_data["dish_width"], cfg_data["dish_height"]
    dst_pts = np.array([[0,0], [W-1,0], [W-1,H-1], [0,H-1]], dtype=np.float32)

    # 盤子配置
    dish_configs = cfg_data["dishes"]

    print("--- 咸豐草五盤主畫面監測模式 (OpenCV 4.13.0 新版) ---")
    print(f"相機路徑: {v4k_path}")
    print("按 's' 儲存當下所有可見盤子，按 'q' 退出")

    while True:
        ret, frame = cap.read()
        if not ret: 
            print("錯誤：無法讀取影像，請檢查 V4K 是否正確連接")
            break

        # 使用新版 detector 偵測標記
        corners, ids, rejected = detector.detectMarkers(frame)
        
        ready_to_save = {}

        if ids is not None:
            # 建立 ID 中心座標索引
            marker_centers = {int(mid[0]): np.mean(c[0], axis=0) for c, mid in zip(corners, ids)}
            
            # 繪製偵測到的標記 (選配)
            aruco.drawDetectedMarkers(frame, corners, ids)

            for name, cfg in dish_configs.items():
                target_ids = cfg['ids']
                color = cfg['color']
                
                if all(tid in marker_centers for tid in target_ids):
                    src_pts = np.array([marker_centers[tid] for tid in target_ids], dtype=np.float32)
                    
                    # 繪製盤子邊框
                    pts_display = src_pts.astype(np.int32).reshape((-1, 1, 2))
                    cv2.polylines(frame, [pts_display], True, color, 3)
                    cv2.putText(frame, f"{name} OK", (int(src_pts[0][0]), int(src_pts[0][1]-15)), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                    
                    # 執行透視校正
                    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
                    warped = cv2.warpPerspective(frame, M, (W, H))
                    ready_to_save[name] = warped
                else:
                    # 顯示缺漏提示
                    missing = [tid for tid in target_ids if tid not in marker_centers]
                    if any(tid in marker_centers for tid in target_ids):
                        first_found = next(tid for tid in target_ids if tid in marker_centers)
                        fx, fy = marker_centers[first_found]
                        cv2.putText(frame, f"{name} Missing:{missing}", (int(fx), int(fy+30)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        # 顯示縮放後的預覽畫面
        preview = cv2.resize(frame, (1024, 768))
        cv2.imshow('Main Monitor (Multi-Dish Trace)', preview)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            if ready_to_save:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                for name, img in ready_to_save.items():
                    fname = f"{timestamp}_{name}.jpg"
                    cv2.imwrite(os.path.join(output_base_dir, fname), img)
                print(f"[{timestamp}] 手動儲存完成: {list(ready_to_save.keys())}")
            else:
                print("未偵測到完整盤子，無法儲存。")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_multi_dish_monitor()
