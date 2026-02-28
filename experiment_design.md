# 咸豐草發芽實驗設計與統計分析 (Experiment Design & Statistical Analysis)

本文件詳述「咸豐草瘦果發芽自動化監測」實驗的統計設計、數據指標、以及後續建議使用的進階分析模型。

---

## 🧪 實驗設計：隨機區集設計 (RCBD)

本實驗採用 **隨機區集設計 (Randomized Complete Block Design, RCBD)**，以確保環境變異（如不同盤子的微氣候差異）能被統計模型抵銷。

### 1. 統計術語對照
*   **因子 (Factor)**：瘦果的處理方式。
*   **處理 (Treatments)**：共有 2 組。
    *   **剪芒組 (Clipped)**：去除冠芒的瘦果。
    *   **未處理組 (Natural)**：保有冠芒的瘦果（對照組）。
*   **區集 (Block)**：4 個培養皿（Dish A, B, C, D）。每個盤子視為一個區集，內部皆包含所有處理。
*   **重複 (Replicates)**：共 4 個區集，代表實驗重複 4 次。
*   **樣本數 (Sample Size)**：
    *   每個處理在單一盤子中有 15 顆種子。
    *   總樣本數 $N = 120$ ($30 \text{ 顆} \times 4 \text{ 盤}$)。

---

## 📊 關鍵數據指標

利用自動化影像監測獲得的高頻率數據，可計算以下指標：

1.  **最終發芽率 (Final Germination Percentage)**
    $$\frac{\text{最終發芽種子數}}{\text{總種子數}} \times 100\%$$
2.  **中位發芽時間 (Median Germination Time, $T_{50}$)**
    剛好 50% 種子發芽所需的精確分鐘數。這是衡量發芽速度最公平的指標。
3.  **發芽速率指數 (Germination Rate Index)**
    衡量單位時間內發芽數量的動態指標。
4.  **自由度 (Degrees of Freedom)**
    *   處理自由度 ($df_{treatment}$) = $2 - 1 = 1$
    *   區集自由度 ($df_{block}$) = $4 - 1 = 3$
    *   誤差自由度 ($df_{error}$) = $(2-1) \times (4-1) = 3$

---

## 🔬 進階統計模型建議

由於監測頻率高達 **每 5 分鐘一次**，數據解析度極高，建議採用以下模型：

### 1. 邏輯斯迴歸 (Logistic Regression / GLM)
適用於分析「最終發芽與否」。
*   **隨機成分**：二項分佈 (Binomial)。
*   **連結函數**：Logit。
*   **優點**：確保預測值介於 0 與 1 之間，並可算出**勝算比 (Odds Ratio)**。
*   **公式**：$\ln\left(\frac{p}{1-p}\right) = \beta_0 + \beta_1 X_{treatment} + \beta_2 X_{tray}$

### 2. 生存分析 (Survival Analysis)
這是本實驗最推薦的方法，因為它能處理隨時間變化的「發芽機率」。

#### A. 卡普蘭-梅爾估計 (Kaplan-Meier Estimate)
*   **用途**：繪製累積發芽曲線（階梯函數）。
*   **優點**：能處理「設限數據 (Censoring)」，即實驗結束時仍未發芽的種子資訊。
*   **對數秩檢定 (Log-rank Test)**：用 P 值判定兩組發芽曲線是否具有顯著差異。

#### B. Cox 比例風險模型 (Cox Proportional Hazards Model)
*   **用途**：計算**風險比 (Hazard Ratio, HR)**。
*   **範例**：若 $HR = 1.5$，代表在任何時間點，剪芒組發芽的可能性是未剪組的 1.5 倍。

---

## 💻 R 語言分析範例

### 數據準備格式 (Tidy Data)
| Seed_ID | Tray | Treatment | Status (1=發芽, 0=未發) | Time (分鐘) |
| :------ | :--- | :-------- | :---------------------- | :---------- |
| 001     | 1    | Clipped   | 1                       | 4325        |
| 002     | 1    | Natural   | 0                       | 20160       |

### 分析程式碼
```R
library(survival)
library(survminer)

# 1. 進行廣義線性模型 (GLM) 分析最終發芽率
logit_model <- glm(Status ~ Treatment + Tray, family = binomial(link = "logit"), data = df)
summary(logit_model)

# 2. 建立生存物件並繪製 Kaplan-Meier 曲線
surv_obj <- Surv(time = df$Time, event = df$Status)
fit_km <- survfit(surv_obj ~ Treatment, data = df)

ggsurvplot(fit_km, fun = "event", risk.table = TRUE, 
           title = "Cumulative Germination Curves",
           xlab = "Time (Minutes)", ylab = "Probability")

# 3. 進行 Cox 回歸分析 (考慮盤子效應)
fit_cox <- coxph(surv_obj ~ Treatment + strata(Tray), data = df)
summary(fit_cox)
```

---

## 💡 為什麼高頻率監測 (5 min/frame) 很重要？
*   **斜率分析**：能觀察發芽的「爆發期」斜率。
*   **生理效率**：精準捕捉 $T_{50}$ 的差異，而非僅是「天」級的粗略觀測。
*   **動態過程**：能證明處理是否導致了發芽時間的「提前」或「同步化」。