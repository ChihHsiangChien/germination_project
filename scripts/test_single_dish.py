import cv2
import cv2.aruco as aruco
import numpy as np
import os
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

def run_calibrated_test():
    cfg_data = load_config()
    
    # --- 1. 初始化路徑 ---
    project_root = os.path.dirname(SCRIPT_DIR)
    temp_data_dir = os.path.join(project_root, "temp_data")
    if not os.path.exists(temp_data_dir): os.makedirs(temp_data_dir)

    # --- 2. 相機設定 ---
    v4k_path = cfg_data["camera_id"]
    cap = cv2.VideoCapture(v4k_path, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg_data["frame_width"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg_data["frame_height"])

    # --- 3. ArUco 偵測器設定 (OpenCV 4.13.0+) ---
    aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
    parameters = aruco.DetectorParameters()
    detector = aruco.ArucoDetector(aruco_dict, parameters)

    print("--- 單盤校正測試模式 (新版 OpenCV 語法) ---")
    print("本工具會顯示設定檔中『第一個』找到的完整盤子，並顯示校正結果。")
    print("按 's' 儲存校正影像，按 'q' 退出")

    while True:
        ret, frame = cap.read()
        if not ret: 
            print("無法讀取相機影像，請檢查 camera_id 是否正確")
            break

        # 偵測標記
        corners, ids, rejected = detector.detectMarkers(frame)
        
        display_frame = frame.copy()
        warped_dish = None
        found_dish_name = ""

        if ids is not None:
            # 建立 ID 中心索引
            marker_centers = {int(mid[0]): np.mean(c[0], axis=0) for c, mid in zip(corners, ids)}
            aruco.drawDetectedMarkers(display_frame, corners, ids)

            for name, cfg in cfg_data["dishes"].items():
                target_ids = cfg['ids']
                color = cfg['color']
                
                if all(tid in marker_centers for tid in target_ids):
                    src_pts = np.array([marker_centers[tid] for tid in target_ids], dtype=np.float32)
                    
                    # 取得該盤子應有的尺寸
                    W = cfg.get("width", cfg_data["dish_width"])
                    H = cfg.get("height", cfg_data["dish_height"])
                    dst_pts = np.array([[0,0], [W-1,0], [W-1,H-1], [0,H-1]], dtype=np.float32)

                    # 繪製框線
                    pts_display = src_pts.astype(np.int32).reshape((-1, 1, 2))
                    cv2.polylines(display_frame, [pts_display], True, color, 3)
                    
                    # 執行透視校正
                    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
                    warped_dish = cv2.warpPerspective(frame, M, (W, H))
                    found_dish_name = name
                    
                    # 僅顯示第一個找到的盤子
                    break

        if warped_dish is not None:
            cv2.imshow(f'Test View: {found_dish_name}', warped_dish)
            cv2.putText(display_frame, f"Testing: {found_dish_name}", (30, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        else:
            cv2.putText(display_frame, "Searching for dishes in config...", (30, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        # 顯示全景預覽
        preview = cv2.resize(display_frame, (800, 600))
        cv2.imshow('Main Camera Feed', preview)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s') and warped_dish is not None:
            save_path = os.path.join(temp_data_dir, f"test_calibration_{found_dish_name}.jpg")
            cv2.imwrite(save_path, warped_dish)
            print(f"校正影像已儲存：{save_path}")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_calibrated_test()
