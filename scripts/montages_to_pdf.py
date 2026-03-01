import os
import glob
from PIL import Image

# ==========================================================
# [ 設定參數 ]
# ==========================================================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_BASE_DIR = os.path.join(PROJECT_ROOT, "temp_data", "exp1_dish", "daily_montages")
OUTPUT_PDF_DIR = os.path.join(PROJECT_ROOT, "temp_data", "exp1_dish", "reports_pdf")

def generate_dish_pdf(dish_name):
    dish_path = os.path.join(INPUT_BASE_DIR, dish_name)
    if not os.path.exists(dish_path):
        print(f"[跳過] 找不到 Dish 目錄: {dish_path}")
        return

    # 取得所有種子目錄並排序 (seed_01, seed_02...)
    seeds = sorted([s for s in os.listdir(dish_path) if os.path.isdir(os.path.join(dish_path, s))])
    
    all_pages = []
    
    print(f"\n[處理] 正在編譯 {dish_name} 的 PDF 報告...")
    
    for seed in seeds:
        seed_path = os.path.join(dish_path, seed)
        # 取得該種子的所有大圖並按日期排序
        montages = sorted(glob.glob(os.path.join(seed_path, "*_montage.jpg")))
        
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
    output_filename = os.path.join(OUTPUT_PDF_DIR, f"{dish_name}_Germination_Report.pdf")
    
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
    print("      咸豐草實驗：Dish 成長紀錄 PDF 合成器")
    print("="*60)
    
    if not os.path.exists(INPUT_BASE_DIR):
        print(f"[錯誤] 找不到輸入目錄，請先執行 daily_seed_montage_generator.py")
        return

    # 掃描 Dish 資料夾
    dishes = sorted([d for d in os.listdir(INPUT_BASE_DIR) if os.path.isdir(os.path.join(INPUT_BASE_DIR, d))])
    
    for dish in dishes:
        generate_dish_pdf(dish)

if __name__ == "__main__":
    run_pdf_generator()
    print("\n[系統] 所有 PDF 報告處理完畢。")
