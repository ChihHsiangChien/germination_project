import cv2
import cv2.aruco as aruco
import numpy as np
import os
import time

def run_multi_dish_monitor():
    # --- 1. 路徑與資料夾初始化 ---
    script_path = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(script_path))
    output_base_dir = os.path.join(project_root, "temp_data", "extracted_dishes")
    if not os.path.exists(output_base_dir): os.makedirs(output_base_dir)

    # --- 2. 相機設定 (使用你測試成功的參數) ---
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1600)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1200)

    # --- 3. ArUco 偵測器設定 ---
    aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
    detector = aruco.ArucoDetector(aruco_dict, aruco.DetectorParameters())

    # 輸出規格 (16cm : 11.5cm)
    W, H = 800, 575
    dst_pts = np.array([[0,0], [W-1,0], [W-1,H-1], [0,H-1]], dtype=np.float32)

    # 定義 5 個盤子的 ID 與顯示顏色 (BGR)
    dish_configs = {
        'Dish_A': {'ids': [0, 1, 2, 3],    'color': (0, 255, 0)},   # 綠
        'Dish_B': {'ids': [4, 5, 6, 7],    'color': (255, 255, 0)}, # 青
        'Dish_C': {'ids': [8, 9, 10, 11],  'color': (255, 0, 255)}, # 紫
        'Dish_D': {'ids': [12, 13, 14, 15], 'color': (0, 165, 255)}, # 橘
        'Dish_E': {'ids': [16, 17, 18, 19], 'color': (0, 0, 255)}    # 紅
    }

    print("--- 咸豐草五盤主畫面監測模式 ---")
    print("按 's' 儲存當下所有可見盤子，按 'q' 退出")

    while True:
        ret, frame = cap.read()
        if not ret: break

        # 偵測 ArUco
        corners, ids, rejected = detector.detectMarkers(frame)
        
        # 建立當前的切割清單
        ready_to_save = {}

        if ids is not None:
            # 建立 ID 中心座標索引
            marker_centers = {int(mid[0]): np.mean(c[0], axis=0) for c, mid in zip(corners, ids)}
            
            # 遍歷各盤子設定
            for name, cfg in dish_configs.items():
                target_ids = cfg['ids']
                color = cfg['color']
                
                # 檢查該盤子的 4 個標記是否都在畫面中
                if all(tid in marker_centers for tid in target_ids):
                    # 取得四角座標
                    src_pts = np.array([marker_centers[tid] for tid in target_ids], dtype=np.float32)
                    
                    # 在主畫面上畫出該盤子的四邊形
                    pts_display = src_pts.astype(np.int32).reshape((-1, 1, 2))
                    cv2.polylines(frame, [pts_display], True, color, 3)
                    
                    # 標註盤子名稱
                    cv2.putText(frame, f"{name} OK", (int(src_pts[0][0]), int(src_pts[0][1]-15)), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                    
                    # 預備切割數據 (透視變換)
                    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
                    warped = cv2.warpPerspective(frame, M, (W, H))
                    ready_to_save[name] = warped
                else:
                    # 如果不完整，顯示缺少的 ID 提示 (選配)
                    missing = [tid for tid in target_ids if tid not in marker_centers]
                    # 如果有偵測到該盤子的任一 Marker，才顯示缺漏訊息
                    if any(tid in marker_centers for tid in target_ids):
                        first_found = next(tid for tid in target_ids if tid in marker_centers)
                        fx, fy = marker_centers[first_found]
                        cv2.putText(frame, f"{name} Missing: {missing}", (int(fx), int(fy+20)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        # 顯示結果主畫面
        cv2.imshow('Main Monitor (Multi-Dish Trace)', frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            if ready_to_save:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                for name, img in ready_to_save.items():
                    fname = f"{timestamp}_{name}.jpg"
                    cv2.imwrite(os.path.join(output_base_dir, fname), img)
                print(f"[{timestamp}] 已儲存 {len(ready_to_save)} 個盤子影像")
            else:
                print("警告：畫面上沒有任何完整的盤子可供切割。")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_multi_dish_monitor()
