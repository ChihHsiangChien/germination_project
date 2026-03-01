import os
import glob
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import math

# ==========================================================
# [ 篩選與路徑設定 ]
# ==========================================================
# 您可以在這裡指定要生成的日期時間範圍
# 格式規範: "YYYYMMDD_HHMMSS" (必須為 15 字元字串或 None)
# ----------------------------------------------------------
# 範例 1: 只要 2月24日 早上 8 點 到 2月26日 晚上 8 點
# FILTER_CONFIG = {
#     "start": "20260224_080000",
#     "end":   "20260226_200000"
# }
# 範例 2: 全部提取
# FILTER_CONFIG = { "start": None, "end": None }
# ----------------------------------------------------------
FILTER_CONFIG = {
    "start": None,  # 請依範例修改，例如 "20260224_000000"
    "end":   None   # 請依範例修改，例如 "20260228_235959"
}

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_BASE_DIR = os.path.join(PROJECT_ROOT, "temp_data", "exp1_dish", "time_series_crops")
OUTPUT_BASE_DIR = os.path.join(PROJECT_ROOT, "temp_data", "exp1_dish", "lifecycle_montages")

# 字型路徑 (Linux 普通路徑)
FONT_PATHS = ["/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]

def get_font(size):
    for path in FONT_PATHS:
        if os.path.exists(path): return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def create_lifecycle_montage(dish, seed, filtered_images):
    """
    將單一粒種子的照片序列合成為一張橫式生命週期大圖
    """
    n = len(filtered_images)
    if n == 0: return

    # 佈局參數
    cell_w, cell_h = 64, 64
    padding_x, padding_y = 6, 12 # 垂直間距加大以容納日期文字
    text_height = 20
    header_height = 100
    margin_x, margin_y = 40, 40
    
    cw = cell_w + padding_x
    ch = cell_h + padding_y + text_height
    
    # 計算最佳佈局 (目標寬度約為 18~24 欄，呈現橫式)
    cols = 20 if n > 20 else n
    if n > 100: cols = 24
    if n > 300: cols = 30
    
    rows = math.ceil(n / cols)
    
    canvas_w = cols * cw + margin_x * 2
    canvas_h = rows * ch + margin_y * 2 + header_height
    
    # 建立畫布
    canvas = Image.new('RGB', (canvas_w, canvas_h), (20, 20, 20))
    draw = ImageDraw.Draw(canvas)
    
    # 標題
    time_range_str = f"{FILTER_CONFIG['start'] or 'Full'} to {FILTER_CONFIG['end'] or 'Present'}"
    font_header = get_font(34)
    draw.text((margin_x, margin_y), f"Seed Lifecycle: {dish} - {seed}", font=font_header, fill=(255, 255, 255))
    draw.text((margin_x, margin_y + 45), f"Interval: {time_range_str} | Total Samples: {n}", font=get_font(20), fill=(200, 200, 200))

    last_date = ""
    font_cell = get_font(12)
    font_date_change = get_font(12)

    for i, img_path in enumerate(filtered_images):
        r, c = i // cols, i % cols
        x = margin_x + c * cw
        y = margin_y + header_height + r * ch
        
        # 處理日期與時間
        fname = os.path.basename(img_path) # YYYYMMDD_HHMMSS.jpg
        date_part = fname[4:8] # MMDD
        time_part = f"{fname[9:11]}:{fname[11:13]}" # HH:MM
        
        # 繪製照片
        try:
            with Image.open(img_path) as img:
                canvas.paste(img.resize((cell_w, cell_h)), (x, y))
        except:
            draw.rectangle([x, y, x+cell_w, y+cell_h], fill=(50, 0, 0))

        # 繪製文字標籤 (若日期更換則顯示月日)
        label = time_part
        fill_color = (150, 150, 150)
        if date_part != last_date:
            label = f"{fname[4:6]}/{fname[6:8]} {time_part}"
            fill_color = (0, 255, 255) # 日期更換點用青色標記
            last_date = date_part
        
        draw.text((x + 2, y + cell_h + 4), label, font=font_cell, fill=fill_color)

    # 儲存
    output_dir = os.path.join(OUTPUT_BASE_DIR, dish)
    os.makedirs(output_dir, exist_ok=True)
    save_path = os.path.join(output_dir, f"{seed}_lifecycle.jpg")
    canvas.save(save_path, quality=85)
    print(f"  > 已生成生命週期圖: {save_path}")

def run_lifecycle_generator():
    print("="*60)
    print("      咸豐草實驗：單一種子全生命週期大圖生成器")
    print("="*60)
    
    dishes = sorted([d for d in os.listdir(INPUT_BASE_DIR) if os.path.isdir(os.path.join(INPUT_BASE_DIR, d))])
    
    for dish in dishes:
        if dish not in ["Dish_A", "Dish_B", "Dish_C", "Dish_D"]: continue
        
        dish_path = os.path.join(INPUT_BASE_DIR, dish)
        seeds = sorted([s for s in os.listdir(dish_path) if os.path.isdir(os.path.join(dish_path, s))])
        
        print(f"\n[處理] {dish}...")
        for seed in seeds:
            all_imgs = sorted(glob.glob(os.path.join(dish_path, seed, "*.jpg")))
            
            # 過濾時間
            filtered = []
            for img_p in all_imgs:
                ts = os.path.basename(img_p).split('.')[0] # YYYYMMDD_HHMMSS
                if FILTER_CONFIG["start"] and ts < FILTER_CONFIG["start"]: continue
                if FILTER_CONFIG["end"] and ts > FILTER_CONFIG["end"]: continue
                filtered.append(img_p)
            
            if filtered:
                create_lifecycle_montage(dish, seed, filtered)

if __name__ == "__main__":
    run_lifecycle_generator()
