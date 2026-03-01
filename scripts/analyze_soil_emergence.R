suppressPackageStartupMessages(library(survival))
suppressPackageStartupMessages(library(ggplot2))
suppressPackageStartupMessages(library(showtext))
suppressPackageStartupMessages(library(survminer))
suppressPackageStartupMessages(library(readxl))

# ==========================================================
# [ 1. 跨平台路徑與環境設定 ]
# ==========================================================

get_proj_root <- function() {
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("--file=", args, value = TRUE)
  
  if (length(file_arg) > 0) {
    script_path <- normalizePath(sub("--file=", "", file_arg))
    return(dirname(dirname(script_path)))
  } else {
    curr_wd <- getwd()
    if (basename(curr_wd) == "scripts") return(dirname(curr_wd))
    return(curr_wd)
  }
}

proj_root <- get_proj_root()
input_file <- file.path(proj_root, "temp_data", "data.xlsx")
output_dir <- file.path(proj_root, "temp_data", "exp2_soil_tray", "analysis_results")

cat(sprintf("[系統] 偵測專案根目錄: %s\n", proj_root))

if (!file.exists(input_file)) {
    stop(sprintf("錯誤: 找不到資料檔案 %s", input_file))
}

# 載入字體
load_chinese_font <- function() {
  sys_name <- Sys.info()[["sysname"]]
  font_name <- "noto"
  
  paths <- c(
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "C:/Windows/Fonts/msjh.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc"
  )
  
  found <- FALSE
  for (f in paths) {
    if (file.exists(f)) {
      font_add(font_name, f)
      found <- TRUE
      break
    }
  }
  
  if (found) {
    showtext_auto()
    showtext_opts(dpi = 300)
    return(font_name)
  } else {
    return("sans")
  }
}

MY_FONT <- load_chinese_font()

# 繪圖樣式設定
TARGET_FIG_WIDTH <- 6.3
TARGET_FIG_HEIGHT <- TARGET_FIG_WIDTH * (2 / 3)

my_theme <- theme_light() +
  theme(
    text = element_text(family = MY_FONT),
    plot.title = element_text(size = 12, hjust = 0.5, margin = margin(b = 15), face = "bold"),
    axis.title = element_text(size = 12),
    axis.text = element_text(size = 10),
    legend.title = element_text(size = 12),
    legend.text = element_text(size = 10),
    legend.position = "bottom",
    panel.grid.major = element_line(linewidth = 0.4, color = "grey90"),
    panel.grid.minor = element_blank()
  )

BW_COLORS <- c("#D55E00", "#0072B2") # 橘藍對比色，適合出苗分析

# ==========================================================
# [ 2. 資料處理 ]
# ==========================================================
cat(sprintf("[系統] 正在讀取 soil_emergence 分頁...\n"))
df <- read_excel(input_file, sheet = "soil_emergence")

# 轉換時間格式 MMdd HHmm -> POSIXct
parse_excel_dt <- function(d_col, t_col) {
  d <- as.numeric(d_col)
  t <- as.numeric(t_col)
  valid <- !is.na(d) & !is.na(t)
  res <- rep(as.POSIXct(NA), length(d))
  if (any(valid)) {
    dt_str <- sprintf("%04d%04d", d[valid], t[valid])
    # 加上當前年份方便計算
    dt_str <- paste0(format(Sys.Date(), "%Y"), dt_str)
    res[valid] <- as.POSIXct(dt_str, format = "%Y%m%d%H%M")
  }
  return(res)
}

df$start_dt <- parse_excel_dt(df$start_date, df$start_time)
df$germ_dt <- parse_excel_dt(df$germination_date, df$germination_time)

# 出土狀態: 有登記日期=1 (Event), NA=0 (Censored)
df$status <- ifelse(is.na(df$germ_dt), 0, 1)

# 設限點 (End time) 統一計算
if (any(!is.na(df$germ_dt))) {
  end_dt <- max(df$germ_dt, na.rm = TRUE) + (24 * 3600)
} else {
  base_start <- min(df$start_dt, na.rm = TRUE)
  end_dt <- base_start + (14 * 24 * 3600) # 預設14天
}

df$time_hr <- as.numeric(difftime(
  ifelse(is.na(df$germ_dt), end_dt, df$germ_dt), 
  df$start_dt, units = "hours"
))

# ==========================================================
# [ 3. 統計分析 ]
# ==========================================================
# 存活分析核心 (以 time_hr 作為時間, status 作為事件發生指標)
surv_obj <- Surv(time = df$time_hr, event = df$status)

# 建立 Kaplan-Meier 曲線模型
fit_km <- survfit(surv_obj ~ treatment, data = df)

# Log-rank Test 檢定兩組出土曲線是否有顯著差異
log_rank <- survdiff(surv_obj ~ treatment, data = df)
p_val <- 1 - pchisq(log_rank$chisq, length(log_rank$n) - 1)

# Cox 迴歸 (考慮 dish 差異的隨機效應)
fit_cox <- coxph(surv_obj ~ treatment + strata(dish), data = df)
cox_sum <- summary(fit_cox)

# GLM: 分析最終破土率 (Final Emergence Percentage)
fit_glm <- glm(status ~ treatment + dish, family = binomial(link = "logit"), data = df)
glm_sum <- summary(fit_glm)

# 計算 T50 等生理指標
calculate_metrics <- function(sub_df) {
  emerged <- sub_df[sub_df$status == 1, ]
  if(nrow(emerged) == 0) return(list(eri=0, met=NA))
  
  # 出土速率指數 (Emergence Rate Index, ERI) = sum(1/ti)
  eri <- sum(1 / emerged$time_hr) * 100
  
  # 平均出土時間 (Mean Emergence Time, MET)
  met <- mean(emerged$time_hr)
  
  return(list(eri=eri, met=met))
}
metric_treated <- calculate_metrics(df[df$treatment == "Treated", ])
metric_untreated <- calculate_metrics(df[df$treatment == "Untreated", ])

# ==========================================================
# [ 4. 繪圖與報表匯出 ]
# ==========================================================
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

# 圖表 1: 破土曲線 (Emergence Curve)
p1 <- ggsurvplot(
  fit_km, data = df, fun = "event", conf.int = TRUE,
  palette = BW_COLORS, linetype = "strata",
  title = "咸豐草覆土 1cm 出苗動力學 (Kaplan-Meier)",
  xlab = "經過時間 (小時)", ylab = "累積出土機率",
  legend.title = "瘦果處理方式",
  legend.labs = c("去芒 (Treated)", "未去芒 (Untreated)"),
  ggtheme = my_theme
)
ggsave(file.path(output_dir, "emergence_curve.png"), plot = p1$plot, 
       width = TARGET_FIG_WIDTH, height = TARGET_FIG_HEIGHT, dpi = 300)

# 圖表 2: 獨立出土時間分佈箱型圖
p2 <- ggplot(df[df$status == 1, ], aes(x = treatment, y = time_hr, fill = treatment)) +
  geom_boxplot(alpha = 0.7, outlier.shape = NA) +
  geom_jitter(width = 0.15, alpha = 0.5, size=2) +
  scale_fill_manual(values = BW_COLORS) +
  scale_x_discrete(labels = c("Treated" = "去芒", "Untreated" = "未去芒")) +
  labs(title = "剛出土幼苗所需時間分佈圖", x = "處理組別", y = "破土所需時間 (小時)") +
  coord_flip() +
  my_theme +
  theme(legend.position = "none")
ggsave(file.path(output_dir, "emergence_time_distribution.png"), plot = p2, 
       width = TARGET_FIG_WIDTH, height = TARGET_FIG_HEIGHT, dpi = 300)


# 生成綜合報表
sink(file.path(output_dir, "soil_emergence_report.txt"))
cat("============================================================\n")
cat("      咸豐草 1cm 覆土出苗實驗：全方位統計分析報表\n")
cat("============================================================\n\n")

cat("[一] 描述性統計 (最終出土率 FEP)\n")
emergence_summary <- aggregate(status ~ treatment, data = df, function(x) {
  c(count = sum(x), total = length(x), percent = round(sum(x)/length(x)*100, 2))
})
print(do.call(data.frame, emergence_summary))

cat("\n[二] 出苗動力學關鍵指標\n")
cat("1. 百分位出土時間 (小時):\n")
quantiles <- quantile(fit_km, probs = c(0.25, 0.5))
print(quantiles)
cat("   * T50 (0.5百分位) 即代表該組達到 50% 出苗率所需的時間。\n\n")

cat("2. 平均指標 (僅計已成功出苗者):\n")
cat("   A. 平均出苗時間 (MET, 小時):\n")
cat("      - 去芒:", ifelse(is.na(metric_treated$met), "NA", round(metric_treated$met, 2)), "小時\n")
cat("      - 未去芒:", ifelse(is.na(metric_untreated$met), "NA", round(metric_untreated$met, 2)), "小時\n")

cat("   B. 出苗速率指數 (ERI, 1/hr x100):\n")
cat("      - 去芒:", round(metric_treated$eri, 4), "\n")
cat("      - 未去芒:", round(metric_untreated$eri, 4), "\n\n")

cat("[三] 推論統計與顯著性檢定\n")
cat("1. 最終出土率差異 (GLM 邏輯斯迴歸):\n")
p_idx <- grep("treatment", rownames(glm_sum$coefficients))
if(length(p_idx) > 0) {
  p_glm <- glm_sum$coefficients[p_idx[1], "Pr(>|z|)"]
  cat("   - 處理參數 P 值:", format.pval(p_glm), "\n")
  cat("   - 結論:", ifelse(p_glm < 0.05, ">>> 去芒處理對「最終出苗率」具有顯著影響", ">>> 去芒處理對「最終出苗率」無顯著差異"), "\n\n")
}

cat("2. 出土速度趨勢差異 (Log-rank Test):\n")
cat("   - 檢定 P 值: P =", format.pval(p_val), "\n")
cat("   - 結論:", ifelse(p_val < 0.05, ">>> 具有顯著差異 (兩組的破土動力學曲線顯著不同)", ">>> 無顯著差異 (兩組的破土時間分佈雷同)"), "\n\n")

cat("3. 相對出土優勢 (Cox Hazard Ratio):\n")
# 依據 R 迴歸編碼，通常 Untreated 會是 Baseline
hr_val <- cox_sum$conf.int[1]
cat("   - 競爭風險比 (Hazard Ratio):", round(hr_val, 4), "\n")
cat(sprintf("   - 解讀: %s\n", 
    ifelse(hr_val > 1, 
           sprintf("去芒的出苗勝算 (Hazard) 約為未去芒的 %.2f 倍", hr_val),
           sprintf("去芒的出苗勝算 (Hazard) 僅為未去芒的 %.2f 倍", hr_val))))
sink()

cat(sprintf("\n[系統] 分析完成！圖表與報表已存入: %s\n", output_dir))
