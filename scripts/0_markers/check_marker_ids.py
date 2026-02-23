import cv2
import cv2.aruco as aruco

def run_test():
    # 1. 初始化相機
    cap = cv2.VideoCapture(0)
    # 建議解析度調高一點，測試 20 個 Marker 的細節
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1600)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1200)

    # 2. 設定 ArUco 偵測器
    # 我們使用的是 4X4 50 字典
    aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
    parameters = aruco.DetectorParameters()
    detector = aruco.ArucoDetector(aruco_dict, parameters)

    print("--- ID 偵測測試中 ---")
    print("請將螢幕顯示的 png 圖檔對準 P2V 相機")
    print("按 's' 截圖存檔，按 'q' 退出")

    while True:
        ret, frame = cap.read()
        if not ret: break

        # 3. 偵測標記
        corners, ids, rejected = detector.detectMarkers(frame)

        # 4. 繪製結果
        if ids is not None:
            # 畫出框框與 ID
            aruco.drawDetectedMarkers(frame, corners, ids)
            
            # 在視窗標題顯示抓到的數量
            count = len(ids)
            display_text = f"Detected: {count}/20 IDs"
        else:
            display_text = "No markers detected"

        # 畫一個提示文字在左上角
        cv2.putText(frame, display_text, (50, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow('Marker ID Check', frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            cv2.imwrite('../temp_data/marker_check_capture.jpg', frame)
            print("已截圖存至 temp_data")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_test()
