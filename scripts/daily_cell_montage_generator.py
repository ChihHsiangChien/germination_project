import os
import glob
from PIL import Image, ImageDraw, ImageFont
import math

# ==========================================================
# [ 設定參數 ]
# ==========================================================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_BASE_DIR = os.path.join(PROJECT_ROOT, "temp_data", "exp2_soil_tray", "time_series_crops")
OUTPUT_BASE_DIR = os.path.join(PROJECT_ROOT, "temp_data", "exp2_soil_tray", "daily_montages")

# 字型路徑 (Linux 常見路徑)
FONT_PATHS = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
]

def get_font(size):
    for path in FONT_PATHS:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def create_half_daily_cell_montage(dish, cell_name, date, am_pm, image_list):
    """
    為特定的 Dish、Cell 和 日期(上午/下午) 建立縮時大圖 (10分鐘一格，12小時一張，一列6格，共12列)
    """
    slot_interval = 10
    cols = 12
    rows = 6
    # 共有 72 個位置 (12小時)
    
    cell_w, cell_h = 189, 189 # 維持切割原始大小 (約 189x189) 以利看清細節
    padding_x, padding_y = 6, 8
    text_height = 14
    header_height = 80
    margin_x, margin_y = 30, 30
    
    cw = cell_w + padding_x
    ch = cell_h + padding_y + text_height
    
    canvas_w = cols * cw + margin_x * 2
    canvas_h = rows * ch + margin_y * 2 + header_height
    
    # 將影像放入對應的 Time-Slot
    slots = [None] * (cols * rows)
    offset_hours = 0 if am_pm == "AM" else 12
    has_image = False
    
    for img_path in image_list:
        filename = os.path.basename(img_path)
        try:
            time_part = filename.split('_')[1]
            h = int(time_part[0:2])
            m = int(time_part[2:4])
            
            # 過濾 AM 或是 PM 的照片
            if am_pm == "AM" and h >= 12: continue
            if am_pm == "PM" and h < 12: continue
            
            total_minutes = (h - offset_hours) * 60 + m
            slot_idx = total_minutes // slot_interval
            
            if 0 <= slot_idx < len(slots):
                if slots[slot_idx] is None:
                    slots[slot_idx] = img_path
                    has_image = True
        except:
            continue
            
    if not has_image:
        return # 如果這個半天沒有任何照片，就不產生空圖

    # 建立畫布
    bg_color = (15, 15, 15)
    canvas = Image.new('RGB', (canvas_w, canvas_h), bg_color)
    draw = ImageDraw.Draw(canvas)
    
    # 讀取字型
    font_header = get_font(30)
    font_cell = get_font(12)
    
    # 繪製標題
    header_text_main = f"Soil Emergence | Date: {date} ({am_pm})"
    header_text_sub = f"Location: {dish} - {cell_name} | Interval: {slot_interval} min grid"
    
    draw.text((margin_x, margin_y), header_text_main, font=font_header, fill=(255, 255, 255))
    draw.text((margin_x, margin_y + 40), header_text_sub, font=get_font(20), fill=(250, 180, 50))
    
    # 按順序繪製 72 個位置
    for i in range(cols * rows):
        r = i // cols
        c = i % cols
        
        x = margin_x + c * cw
        y = margin_y + header_height + r * ch
        
        # 計算此位置代表的時間
        target_total_min = i * slot_interval
        th = (target_total_min // 60) + offset_hours
        tm = target_total_min % 60
        formatted_time = f"{th:02d}:{tm:02d}"
        
        img_path = slots[i]
        
        if img_path:
            try:
                with Image.open(img_path) as img:
                    img_resized = img.resize((cell_w, cell_h), Image.Resampling.LANCZOS)
                    canvas.paste(img_resized, (x, y))
            except:
                pass
        else:
            # 沒圖的位置畫一個淡灰色框框示意
            draw.rectangle([x, y, x + cell_w, y + cell_h], outline=(40, 40, 40), width=1)
            
        # 繪製時間文字
        text_x = x + cell_w // 2 - 14
        text_y = y + cell_h + 2
        draw.text((text_x, text_y), formatted_time, font=font_cell, fill=(100, 100, 100))
            
    # 儲存結果
    output_dir = os.path.join(OUTPUT_BASE_DIR, dish, cell_name)
    os.makedirs(output_dir, exist_ok=True)
    save_path = os.path.join(output_dir, f"{date}_{am_pm}_montage.jpg")
    canvas.save(save_path, quality=90)
    print(f"  > 已生成大圖: {save_path}")

def run_montage_generator():
    print("="*60)
    print("      咸豐草實驗：覆土出苗 (Cell) 每日大圖生成器 (12H一圖)")
    print("="*60)
    
    if not os.path.exists(INPUT_BASE_DIR):
        print(f"[錯誤] 找不到輸入目錄: {INPUT_BASE_DIR}")
        return

    # 取得所有 Dish 資料夾 (Dish_A, Dish_B, ...)
    dishes = [d for d in os.listdir(INPUT_BASE_DIR) if os.path.isdir(os.path.join(INPUT_BASE_DIR, d))]
    dishes = sorted(dishes)
    
    for dish in dishes:
        dish_path = os.path.join(INPUT_BASE_DIR, dish)
        cells = sorted([c for c in os.listdir(dish_path) if os.path.isdir(os.path.join(dish_path, c))])
        
        print(f"\n[處理] 正在掃描 {dish} ({len(cells)} 個穴孔)...")
        
        for cell in cells:
            cell_path = os.path.join(dish_path, cell)
            jpg_files = sorted(glob.glob(os.path.join(cell_path, "*.jpg")))
            
            if not jpg_files:
                continue
            
            # 根據日期分組 (YYYYMMDD)
            daily_groups = {}
            for img_path in jpg_files:
                date_str = os.path.basename(img_path).split('_')[0]
                if date_str not in daily_groups:
                    daily_groups[date_str] = []
                daily_groups[date_str].append(img_path)
            
            # 為每個日期生成 兩張大圖 (AM 與 PM)
            for date_str, images in sorted(daily_groups.items()):
                create_half_daily_cell_montage(dish, cell, date_str, "AM", images)
                create_half_daily_cell_montage(dish, cell, date_str, "PM", images)

if __name__ == "__main__":
    run_montage_generator()
    print("\n[系統] 所有任務處理完畢。")
