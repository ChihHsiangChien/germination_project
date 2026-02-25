import cv2
import os

def find_cameras():
    print("\n" + "="*50)
    print("      咸豐草實驗：相機設備偵測工具")
    print("="*50)
    print(" [ Linux/Pi 建議 ]")
    print(" 請在終端機執行: ls /dev/v4l/by-id/")
    print(" 取得長路徑後貼入 JSON 的 camera_id 中。")
    print("\n [ 視窗操作 ]")
    print(" 1. 程式將逐一開啟相機 index (0-5)。")
    print(" 2. 看到 V4K 畫面後，確認該 Index 編號。")
    print(" 3. 按 'q' 鍵切換到下一個設備。")
    print("="*50 + "\n")

    for i in range(6):  # 掃描 index 0 到 5
        cap = cv2.VideoCapture(i)
        if not cap.isOpened():
            continue
        
        # 嘗試設定高解析度以確認是否為 V4K
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1600)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1200)
        
        print(f"[偵測] 發現設備 Index: {i}")
        
        while True:
            ret, frame = cap.read()
            if not ret: 
                print(f"      (Index {i} 無法讀取影像串流)")
                break
            
            # 在畫面上顯示當前 Index
            cv2.putText(frame, f"Current Camera Index: {i}", (50, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, "Press 'q' to next camera", (50, 100), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            cv2.imshow(f"Camera Detector - Index {i}", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
    
    print("\n[完成] 相機掃描結束。")

if __name__ == "__main__":
    find_cameras()
