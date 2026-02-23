import numpy as np
import pandas as pd
import cv2
import os

def generate_dish_layout_bw(dish_id):
    # 畫布大小對應校正後的 800x575
    W, H = 800, 575
    # 生成純白底圖
    img = np.ones((H, W), dtype=np.uint8) * 255
    
    # 1. 定義交錯座標 (4 Rows: 8, 7, 8, 7)
    points = []
    y_starts = [100, 220, 340, 460] 
    for r, y in enumerate(y_starts):
        num_seeds = 8 if r % 2 == 0 else 7
        # 偶數列位移以達成交錯排列
        offset_x = 0 if r % 2 == 0 else 50 
        x_positions = np.linspace(80 + offset_x, 720 - offset_x, num_seeds)
        for x in x_positions:
            points.append((int(x), int(y)))
            
    # 2. 隨機分配處理 (15 Treated: 黑實心, 15 Untreated: 黑空心)
    treatments = ['Treated'] * 15 + ['Untreated'] * 15
    np.random.shuffle(treatments)
    
    data = []
    for i, (pt, treat) in enumerate(zip(points, treatments)):
        if treat == 'Treated':
            # 去芒組：黑實心圓
            cv2.circle(img, pt, 20, 0, -1)
            # 白色編號
            cv2.putText(img, str(i+1), (pt[0]-10, pt[1]+7), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 255, 1)
        else:
            # 未處理組：黑空心圓 (線條寬度 2)
            cv2.circle(img, pt, 20, 0, 2)
            # 黑色編號
            cv2.putText(img, str(i+1), (pt[0]-10, pt[1]+7), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 0, 1)
            
        data.append({'Seed_ID': i+1, 'x': pt[0], 'y': pt[1], 'Treatment': treat})
        
    # 加入標題與說明
    cv2.putText(img, f"DISH {dish_id} - Black:Awnless, Circle:Normal", (40, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, 0, 2)
    
    return img, pd.DataFrame(data)

# 執行生成
output_dir = "temp_data/layouts_bw"
if not os.path.exists(output_dir): os.makedirs(output_dir)

for d in ['A', 'B', 'C', 'D', 'E']:
    layout_img, df = generate_dish_layout_bw(d)
    cv2.imwrite(f"{output_dir}/layout_dish_{d}_bw.png", layout_img)
    df.to_csv(f"{output_dir}/map_dish_{d}.csv", index=False)
    print(f"已生成盤子 {d} 的黑白隨機配置圖。")
