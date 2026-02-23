import cv2
import cv2.aruco as aruco
import numpy as np
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
import os

# --- 路徑設定 ---
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
output_dir = os.path.join(project_root, "markers")
if not os.path.exists(output_dir): 
    os.makedirs(output_dir)

# 暫存圖檔與最終 PDF 路徑
temp_img_path = os.path.join(output_dir, "temp_full_sheet.png")
output_pdf = os.path.join(output_dir, "ibon_markers_v4_final.pdf")

def create_perfect_png():
    # 建立 300 DPI 的 A4 畫布 (2480x3508)
    h, w = 3508, 2480
    img = np.ones((h, w), dtype=np.uint8) * 255
    dictionary = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
    
    # 規格: 2cm Marker (300 DPI 下約為 236 像素)
    m_size = 236
    
    # 排版參數：稍微調緊湊一點，確保不報錯
    # 第一組起點 250, 第二組起點 1850
    starts_y = [250, 1850] 
    margin_x = 300
    col_gap = 500
    row_gap = 300 # 縮小一點，留出更多垂直空間

    for sy in starts_y:
        cv2.putText(img, "ArUco SET ID 0-19", (margin_x, sy - 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, 0, 3)
        for i in range(20):
            row, col = divmod(i, 4)
            marker = aruco.generateImageMarker(dictionary, i, m_size)
            
            y = sy + row * row_gap
            x = margin_x + col * col_gap
            
            # 安全檢查：確保座標不會超出 3508x2480
            if y + m_size < h and x + m_size < w:
                img[y:y+m_size, x:x+m_size] = marker
                # ID 文字標籤
                cv2.putText(img, f"ID:{i}", (x, y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 0, 2)
            
    cv2.imwrite(temp_img_path, img)
    return temp_img_path

def convert_to_pdf(png_path):
    # PDF 原點在左下角，但 drawImage 會幫我們處理
    c = canvas.Canvas(output_pdf, pagesize=A4)
    # A4 是 21.0cm x 29.7cm
    c.drawImage(png_path, 0, 0, width=21.0*cm, height=29.7*cm)
    c.save()
    # 移除暫存圖檔
    if os.path.exists(png_path):
        os.remove(png_path)

if __name__ == "__main__":
    print("正在生成影像並轉換為 PDF...")
    try:
        tmp = create_perfect_png()
        convert_to_pdf(tmp)
        print(f"成功！檔案已儲存至：{output_pdf}")
    except Exception as e:
        print(f"發生錯誤：{e}")
