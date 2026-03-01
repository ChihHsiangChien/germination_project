suppressPackageStartupMessages(library(survival))
suppressPackageStartupMessages(library(ggplot2))
suppressPackageStartupMessages(library(showtext))
suppressPackageStartupMessages(library(survminer))
suppressPackageStartupMessages(library(readxl))

# ==========================================================
# [ 1. 跨平台路徑與環境設定 ]
# ==========================================================

# A. 自動判定專案根目錄
get_proj_root <- function() {
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("--file=", args, value = TRUE)
  
  if (length(file_arg) > 0) {
    # 透過 Rscript 執行
    script_path <- normalizePath(sub("--file=", "", file_arg))
    return(dirname(dirname(script_path)))
  } else {
    # 透過 RStudio 或互動式執行
    if (requireNamespace("rstudioapi", quietly = TRUE) && rstudioapi::isAvailable()) {
      p <- rstudioapi::getSourceEditorContext()$path
      if (nchar(p) > 0) return(dirname(dirname(normalizePath(p))))
    }
    # 若在 scripts 目錄下執行
    curr_wd <- getwd()
    if (basename(curr_wd) == "scripts") return(dirname(curr_wd))
    return(curr_wd)
  }
}

proj_root <- get_proj_root()
input_file <- file.path(proj_root, "temp_data", "data.xlsx")
output_dir <- file.path(proj_root, "temp_data", "exp1_dish", "analysis_results")

cat(sprintf("[系統] 偵測專案根目錄: %s\n", proj_root))
# 嘗試找出存在的 Excel 檔案 (優先讀取 .xls)
input_file_candidate <- file.path(proj_root, "temp_data", "data.xlsx")

if (!file.exists(input_file_candidate)) {
    stop(sprintf("錯誤: 找不到資料檔案資料檔案 (data.xls 或 data.xlsx) 於 %s", dirname(input_file_candidate)))
}
input_file <- input_file_candidate

# B. 設定中文字體
load_chinese_font <- function() {
  sys_name <- Sys.info()[["sysname"]]
  font_name <- "noto"
  
  if (sys_name == "Windows") {
    paths <- c("C:/Windows/Fonts/msjh.ttc", "C:/Windows/Fonts/msjhbd.ttc", "C:/Windows/Fonts/simhei.ttf")
  } else {
    paths <- c(
      "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
      "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
      "/usr/share/fonts/truetype/arphic/uming.ttc"
    )
  }
  
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
    warning("未找到中文字體，圖表可能無法正常顯示中文。")
    return("sans")
  }
}

MY_FONT <- load_chinese_font()

# C. 使用者定義之 Theme 與 視覺樣式
TARGET_FIG_WIDTH <- 6.3
TARGET_FIG_HEIGHT <- TARGET_FIG_WIDTH * (2 / 3) # 3:2 Ratio

my_theme <- theme_light() +
  theme(
    text = element_text(family = MY_FONT),
    plot.title = element_text(size = 12, hjust = 0.5, margin = margin(b = 15), face = "bold"),
    axis.title = element_text(size = 12),
    axis.text = element_text(size = 10),
    strip.text = element_text(size = 12, face = "bold", color = "white", margin = margin(5, 5, 5, 5)),
    strip.background = element_rect(fill = "grey40"),
    legend.title = element_text(size = 12),
    legend.text = element_text(size = 10),
    legend.position = "bottom",
    panel.grid.major = element_line(linewidth = 0.4, color = "grey90"),
    panel.grid.minor = element_blank()
  )

BW_COLORS <- c("#2D104E", "#21908C", "#FDE725") 

mini_theme <- theme_light() +
  theme(
    text = element_text(size = 15),
    axis.title = element_text(size = 18),
    axis.text = element_text(size = 14),
    legend.text = element_text(size = 14),
    legend.title = element_text(size = 15),
    legend.position = "bottom",
    plot.margin = unit(c(0.2, 0.2, 0.2, 0.2), "cm")
  )

# ==========================================================
# [ 2. 資料處理 ]
# ==========================================================
df <- read_excel(input_file, sheet = "germination")

# 核心轉換函數：處理 Excel 讀入的數值格式 (如 223 -> 0223)
parse_excel_dt <- function(d_col, t_col) {
  # 確保為數值型以後補零
  d <- as.numeric(d_col)
  t <- as.numeric(t_col)
  valid <- !is.na(d) & !is.na(t)
  res <- rep(as.POSIXct(NA), length(d))
  if (any(valid)) {
    # 格式化為 MMDDHHMM (8位數字)
    dt_str <- sprintf("%04d%04d", d[valid], t[valid])
    res[valid] <- as.POSIXct(dt_str, format = "%m%d%H%M")
  }
  return(res)
}

# 時間解析
df$start_dt <- parse_excel_dt(df$start_date, df$start_time)
df$germ_dt <- parse_excel_dt(df$germination_date, df$germination_time)

# 狀態與時間計算
df$status <- ifelse(is.na(df$germ_dt), 0, 1)

# 設限點 (End time)：
# 如果有發芽資料，取最後發芽時間 + 24小時；
# 如果完全沒人發芽，取實驗開始時間 + 168小時 (7天) 作為暫時顯示點
if (any(!is.na(df$germ_dt))) {
  end_dt <- max(df$germ_dt, na.rm = TRUE) + (24 * 3600)
} else {
  # 若無發芽，以開始時間的第一筆為基準
  base_start <- min(df$start_dt, na.rm = TRUE)
  end_dt <- base_start + (168 * 3600) 
}

df$time_hr <- as.numeric(difftime(ifelse(is.na(df$germ_dt), end_dt, df$germ_dt), df$start_dt, units = "hours"))

# ==========================================================
# [ 3. 統計分析 ]
# ==========================================================
surv_obj <- Surv(time = df$time_hr, event = df$status)
fit_km <- survfit(surv_obj ~ treatment, data = df)
log_rank <- survdiff(surv_obj ~ treatment, data = df)
p_val <- 1 - pchisq(log_rank$chisq, length(log_rank$n) - 1)
fit_cox <- coxph(surv_obj ~ treatment + strata(dish), data = df)
cox_sum <- summary(fit_cox)

# 各項進階指標計算
calculate_metrics <- function(sub_df) {
  germinated <- sub_df[sub_df$status == 1, ]
  if(nrow(germinated) == 0) return(list(gri=0, mgt=NA))
  
  # GRI = sum(1/ti)
  gri <- sum(1 / germinated$time_hr) * 100
  
  # MGT = sum(ni*ti) / sum(ni) -> 平均發芽時間 (僅計已發芽者)
  mgt <- mean(germinated$time_hr)
  
  return(list(gri=gri, mgt=mgt))
}

metric_treated <- calculate_metrics(df[df$treatment == "Treated", ])
metric_untreated <- calculate_metrics(df[df$treatment == "Untreated", ])

# 邏輯斯迴歸 (GLM) - 分析最終發芽率與處理、盤子的關係
fit_glm <- glm(status ~ treatment + dish, family = binomial(link = "logit"), data = df)
glm_sum <- summary(fit_glm)

# ==========================================================
# [ 4. 繪圖與報表 ]
# ==========================================================
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

# 1. 發芽曲線
p1 <- ggsurvplot(
  fit_km, data = df, fun = "event", conf.int = TRUE,
  palette = BW_COLORS[1:2], linetype = "strata",
  title = "種子發芽動力學 (Kaplan-Meier 曲線)",
  xlab = "時間 (小時)", ylab = "累積發芽機率",
  legend.title = "處理組別",
  legend.labs = c("去芒", "未去芒"),
  ggtheme = my_theme
)
ggsave(file.path(output_dir, "germination_plots.png"), plot = p1$plot, 
       width = TARGET_FIG_WIDTH, height = TARGET_FIG_HEIGHT, dpi = 300)

# 2. 時間分佈
p2 <- ggplot(df[df$status == 1, ], aes(x = treatment, y = time_hr, fill = treatment)) +
  geom_boxplot(alpha = 0.7) +
  geom_jitter(width = 0.1, alpha = 0.5) +
  scale_fill_manual(values = BW_COLORS[1:2]) +
  scale_x_discrete(labels = c("Treated" = "去芒", "Untreated" = "未去芒")) +
  labs(title = "發芽時間分佈圖 (僅計已發芽種子)", x = "組別", y = "發芽所需時間 (小時)") +
  coord_flip() +
  my_theme +
  theme(legend.position = "none")
ggsave(file.path(output_dir, "time_distribution.png"), plot = p2, 
       width = TARGET_FIG_WIDTH, height = TARGET_FIG_HEIGHT, dpi = 300)

# 3. 綜合報告
sink(file.path(output_dir, "comprehensive_report.txt"))
cat("============================================================\n")
cat("      咸豐草瘦果發芽實驗：全方位統計分析報表\n")
cat("============================================================\n\n")

cat("[一] 描述性統計 (最終發芽率)\n")
germ_summary <- aggregate(status ~ treatment, data = df, function(x) {
  c(count = sum(x), total = length(x), percent = round(sum(x)/length(x)*100, 2))
})
print(do.call(data.frame, germ_summary))

cat("\n[二] 發芽動力學關鍵指標\n")
cat("1. 百分位發芽時間 (小時):\n")
# 計算 T25, T50
quantiles <- quantile(fit_km, probs = c(0.25, 0.5))
print(quantiles)
cat("   * 若為 NA 代表該組發芽率尚未達到該百分比。\n\n")

cat("2. 平均指標 (僅計已發芽者):\n")
cat("   A. 發芽速率指數 (GRI, 1/hr x100):\n")
cat("      - 去芒:", round(metric_treated$gri, 4), "\n")
cat("      - 未去芒:", round(metric_untreated$gri, 4), "\n")
cat("   B. 平均發芽時間 (MGT, 小時):\n")
cat("      - 去芒:", ifelse(is.na(metric_treated$mgt), "NA", round(metric_treated$mgt, 2)), "\n")
cat("      - 未去芒:", ifelse(is.na(metric_untreated$mgt), "NA", round(metric_untreated$mgt, 2)), "\n\n")

cat("[三] 顯著性檢定與模型分析\n")
cat("1. 最終發芽率差異 (GLM 邏輯斯迴歸):\n")
# 提取處理組的 P 值
# 檢查是否存在該參數 (有時 R 會自動命名為 treatmentUntreated 或 treatmentTreated)
p_idx <- grep("treatment", rownames(glm_sum$coefficients))
if(length(p_idx) > 0) {
  p_glm <- glm_sum$coefficients[p_idx[1], "Pr(>|z|)"]
  cat("   - 處理參數 P 值:", format.pval(p_glm), "\n")
  cat("   - 判定:", ifelse(p_glm < 0.05, "去芒對「最終發芽率」有顯著影響", "去芒對「最終發芽率」無顯著影響"), "\n\n")
}

cat("2. 發芽速度差異 (Log-rank Test):\n")
cat("   - 檢定 P 值: P =", format.pval(p_val), "\n")
cat("   - 結論:", ifelse(p_val < 0.05, ">>> 具有顯著差異 (發芽曲線顯著不同) <<<", ">>> 無顯著差異 (發芽曲線無明顯區別) <<<"), "\n\n")

cat("3. 競爭風險分析 (Cox Hazard Ratio):\n")
cat("   - 風險比 (Hazard Ratio):", round(cox_sum$conf.int[1], 4), "\n")
cat(sprintf("   - 解讀: 去芒發芽勝算約為未去芒的 %.2f 倍\n", 1/cox_sum$conf.int[1]))
sink()

cat(sprintf("\n[系統] 分析完成！報表位於: %s\n", output_dir))
