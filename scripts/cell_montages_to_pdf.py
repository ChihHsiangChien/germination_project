import os
import glob
from PIL import Image

# ==========================================================
# [ 設定參數 ]
# ==========================================================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_BASE_DIR = os.path.join(PROJECT_ROOT, "temp_data", "exp2_soil_tray", "daily_montages")
OUTPUT_PDF_DIR = os.path.join(PROJECT_ROOT, "temp_data", "exp2_soil_tray", "reports_pdf")

def generate_dish_pdf(dish_name):
    dish_path = os.path.join(INPUT_BASE_DIR, dish_name)
    if not os.path.exists(dish_path):
        return

    # 取得所有細胞目錄並排序 (cell_01, cell_02...)
    cells = sorted([c for c in os.listdir(dish_path) if os.path.isdir(os.path.join(dish_path, c))])
    
    all_pages = []
    
    print(f"\n[處理] 正在編譯 {dish_name} 的 PDF 報告...")
    
    for cell in cells:
        cell_path = os.path.join(dish_path, cell)
        # 取得該穴孔的所有單日大圖並按特定順序排序 (確保 AM 在 PM 前面)
        # 檔名格式: YYYYMMDD_AM_montage.jpg 或 YYYYMMDD_PM_montage.jpg
        montages = glob.glob(os.path.join(cell_path, "*_montage.jpg"))
        
        def sort_key(filepath):
            filename = os.path.basename(filepath)
            parts = filename.split('_')
            date_str = parts[0]
            # 自訂排序權重：AM=0, PM=1，確保同日期 AM 一定在 PM 之前
            am_pm_val = 0 if parts[1] == "AM" else 1 
            return (date_str, am_pm_val)
            
        montages = sorted(montages, key=sort_key)
        
        if not montages:
            continue
            
        for img_path in montages:
            try:
                img = Image.open(img_path).convert('RGB')
                all_pages.append(img)
            except Exception as e:
                print(f"  ! 無法開啟影像 {img_path}: {e}")

    if not all_pages:
        print(f"  ! {dish_name} 沒有可用的影像。")
        return

    # 儲存為 PDF
    os.makedirs(OUTPUT_PDF_DIR, exist_ok=True)
    output_filename = os.path.join(OUTPUT_PDF_DIR, f"{dish_name}_Soil_Emergence_Report.pdf")
    
    # 第一張作為主體，其餘用 append_images 傳入
    all_pages[0].save(
        output_filename, 
        save_all=True, 
        append_images=all_pages[1:], 
        quality=85
    )
    
    print(f"  > [成功] PDF 已生成: {output_filename} (共 {len(all_pages)} 頁)")

def run_pdf_generator():
    print("="*60)
    print("      咸豐草實驗：覆土出苗 (Cell) PDF 報告合成器")
    print("="*60)
    
    if not os.path.exists(INPUT_BASE_DIR):
        print(f"[錯誤] 找不到輸入目錄，請先執行 daily_cell_montage_generator.py")
        return

    # 掃描 Dish 資料夾
    dishes = sorted([d for d in os.listdir(INPUT_BASE_DIR) if os.path.isdir(os.path.join(INPUT_BASE_DIR, d))])
    
    for dish in dishes:
        generate_dish_pdf(dish)

if __name__ == "__main__":
    run_pdf_generator()
    print("\n[系統] 所有 PDF 報告處理完畢。")
