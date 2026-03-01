import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

def generate_soil_emergence_mock_data():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_path = os.path.join(project_root, "temp_data", "data.xlsx")
    
    # 基本實驗參數
    dishes = ["Dish_A", "Dish_B", "Dish_C", "Dish_D", "Dish_E"]
    cells_per_dish = 12
    seeds_per_cell = 4
    total_seeds = len(dishes) * cells_per_dish * seeds_per_cell
    
    # 實驗開始時間統一 (假設為今天早上 8 點)
    start_dt = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    
    data = []
    
    # T50 假設 (小時): 去芒出苗較快 (~72hr)，未去芒較慢 (~96hr)
    # 取機率: 去芒 85% 出苗, 未去芒 65% 出苗
    treated_mean_h, treated_std = 72, 15
    untreated_mean_h, untreated_std = 96, 20
    
    for dish in dishes:
        for cell_id in range(1, cells_per_dish + 1):
            cell_name = f"cell_{cell_id:02d}"
            
            # 定義這個 cell 裡 4 顆種子的處理方式 (隨機分配: Treated 或 Untreated)
            treatments = np.random.choice(["Treated", "Untreated"], size=seeds_per_cell)
            
            for seed_idx, treatment in enumerate(treatments):
                seed_name = f"seed_{seed_idx+1}"
                
                # 判斷是否發芽(出苗)
                prob_emergence = 0.85 if treatment == "Treated" else 0.65
                is_emerged = np.random.rand() < prob_emergence
                
                germ_date_str = ""
                germ_time_str = ""
                
                if is_emerged:
                    # 依常態分佈抽樣出苗所需時間 (小時)
                    hours_to_emerge = np.random.normal(
                        treated_mean_h if treatment == "Treated" else untreated_mean_h,
                        treated_std if treatment == "Treated" else untreated_std
                    )
                    hours_to_emerge = max(24, hours_to_emerge) # 最快 24 小時出苗
                    
                    emergence_dt = start_dt + timedelta(hours=hours_to_emerge)
                    germ_date_str = emergence_dt.strftime("%m%d")
                    germ_time_str = emergence_dt.strftime("%H%M")
                
                # 寫入列資料
                data.append({
                    "dish": dish,
                    "cell": cell_name,
                    "seed": seed_name,
                    "treatment": treatment,
                    "soil_depth": "1cm", # 控制變因
                    "start_date": start_dt.strftime("%m%d"),
                    "start_time": start_dt.strftime("%H%M"),
                    "germination_date": germ_date_str,
                    "germination_time": germ_time_str
                })

    df = pd.DataFrame(data)
    
    # 若檔案不存在或沒有其他資料，直接新建
    if not os.path.exists(output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with pd.ExcelWriter(output_path) as writer:
            df.to_excel(writer, sheet_name="soil_emergence", index=False)
    else:
        # 如果有舊的 data.xlsx，則使用 openpyxl 模式打開並添加新 sheet
        with pd.ExcelWriter(output_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            df.to_excel(writer, sheet_name="soil_emergence", index=False)
            
    print(f"[成功] Mock Data (共 {total_seeds} 筆種子) 已生或更新至: {output_path} (分頁: soil_emergence)")

if __name__ == "__main__":
    generate_soil_emergence_mock_data()
