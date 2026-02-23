import cv2
import cv2.aruco as aruco
import numpy as np
import os

def run_calibrated_test():
    # --- 1. 初始化與路徑設定 ---
    script_path = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(script_path))
    temp_data_dir = os.path.join(project_root, "temp_data")
    if not os.path.exists(temp_data_dir): os.makedirs(temp_data_dir)

    # 使用你測試成功的設定
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1600)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1200)

    # --- 2. ArUco 偵測器設定 ---
    aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
    parameters = aruco.DetectorParameters()
    detector = aruco.ArucoDetector(aruco_dict, parameters)

    # --- 3. 輸出尺寸設定 (16cm : 11.5cm 比例) ---
    # 設定 1cm = 50px，得出 800x575
    OUTPUT_W = 800
    OUTPUT_H = 575
    dst_pts = np.array([
        [0, 0],                        # 左上
        [OUTPUT_W - 1, 0],             # 右上
        [OUTPUT_W - 1, OUTPUT_H - 1],  # 右下
        [0, OUTPUT_H - 1]              # 左下
    ], dtype=np.float32)

    print("--- 盤子校正測試模式 ---")
    print("請確保 ID 0-3 依順時針貼好：左上(0), 右上(1), 右下(2), 左下(3)")
    print("按 's' 儲存校正影像，按 'q' 退出")

    while True:
        ret, frame = cap.read()
        if not ret: break

        corners, ids, rejected = detector.detectMarkers(frame)

        if ids is not None:
            # 畫出所有偵測到的 Marker
            aruco.drawDetectedMarkers(frame, corners, ids)
            
            # 建立 ID 中心字典
            marker_centers = {}
            for i, marker_id in enumerate(ids):
                marker_id_val = marker_id[0]
                c = corners[i][0]
                cx, cy = int(np.mean(c[:, 0])), int(np.mean(c[:, 1]))
                marker_centers[marker_id_val] = (cx, cy)

            # 檢查是否集齊 ID 0, 1, 2, 3 (一盤所需的四角)
            target_ids = [0, 1, 2, 3]
            if all(id_val in marker_centers for id_val in target_ids):
                src_pts = np.array([
                    marker_centers[0], 
                    marker_centers[1], 
                    marker_centers[2], 
                    marker_centers[3]
                ], dtype=np.float32)

                # 計算透視變換
                M = cv2.getPerspectiveTransform(src_pts, dst_pts)
                warped_dish = cv2.warpPerspective(frame, M, (OUTPUT_W, OUTPUT_H))
                
                # 顯示校正後的盤子 (獨立視窗)
                cv2.imshow('Calibrated Dish (16x11.5)', warped_dish)
                
                # 在主畫面上畫出盤子輪廓線
                pts = src_pts.astype(np.int32).reshape((-1, 1, 2))
                cv2.polylines(frame, [pts], True, (0, 0, 255), 3)
                display_text = "Dish A Ready"
            else:
                display_text = f"Searching for IDs {target_ids}..."
        else:
            display_text = "No markers detected"

        cv2.putText(frame, display_text, (30, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        cv2.imshow('Marker Calibration Feed', frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s') and 'warped_dish' in locals():
            save_path = os.path.join(temp_data_dir, "test_rect_dish_A.jpg")
            cv2.imwrite(save_path, warped_dish)
            print(f"校正影像已儲存：{save_path}")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_calibrated_test()
