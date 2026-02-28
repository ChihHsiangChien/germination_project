suppressPackageStartupMessages(library(survival))
suppressPackageStartupMessages(library(ggplot2))
suppressPackageStartupMessages(library(showtext))
suppressPackageStartupMessages(library(survminer))

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
input_file <- file.path(proj_root, "temp_data", "germination_data.csv")
output_dir <- file.path(proj_root, "temp_data", "analysis_results")

cat(sprintf("[系統] 偵測專案根目錄: %s\n", proj_root))
if (!file.exists(input_file)) {
    stop(sprintf("錯誤: 找不到輸入檔案 %s", input_file))
}

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
df <- read.csv(input_file, colClasses = "character")

# 時間解析
df$start_dt <- as.POSIXct(paste0(df$start_date, df$start_time), format="%Y%m%d%H%M")
df$germ_dt <- as.POSIXct(paste0(df$germination_date, df$germination_time), format="%Y%m%d%H%M")

# 狀態與時間計算
df$status <- ifelse(is.na(df$germ_dt), 0, 1)
# 設限點：最後發芽時間 + 24小時
end_dt <- max(df$germ_dt, na.rm = TRUE) + (24 * 3600)
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

# GRI 計算
calculate_gri <- function(sub_df) {
  germinated <- sub_df[sub_df$status == 1, ]
  if(nrow(germinated) == 0) return(0)
  sum(1 / germinated$time_hr) * 100
}
gri_treated <- calculate_gri(df[df$treatment == "Treated", ])
gri_untreated <- calculate_gri(df[df$treatment == "Untreated", ])

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
  legend.labs = c("處理組 (Treated)", "對照組 (Untreated)"),
  ggtheme = my_theme
)
ggsave(file.path(output_dir, "germination_plots.png"), plot = p1$plot, 
       width = TARGET_FIG_WIDTH, height = TARGET_FIG_HEIGHT, dpi = 300)

# 2. 時間分佈
p2 <- ggplot(df[df$status == 1, ], aes(x = treatment, y = time_hr, fill = treatment)) +
  geom_boxplot(alpha = 0.7) +
  geom_jitter(width = 0.1, alpha = 0.5) +
  scale_fill_manual(values = BW_COLORS[1:2]) +
  scale_x_discrete(labels = c("Treated" = "處理組", "Untreated" = "對照組")) +
  labs(title = "發芽時間分佈圖 (僅計已發芽種子)", x = "組別", y = "發芽所需時間 (小時)") +
  coord_flip() +
  my_theme
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
cat("1. 50% 發芽時間 (T50):\n")
print(quantile(fit_km, probs = 0.5))
cat("\n2. 發芽速率指數 (GRI, 1/hr x100):\n")
cat("   - 處理組:", round(gri_treated, 4), "\n")
cat("   - 對照組:", round(gri_untreated, 4), "\n")

cat("\n[三] 顯著性檢定與風險模型\n")
cat("1. Log-rank Test (曲線差異): P =", format.pval(p_val), "\n")
cat("   結論:", ifelse(p_val < 0.05, ">>> 具有顯著差異 (處理確實有影響) <<<", ">>> 無顯著差異 (處理影響不明顯) <<<"), "\n\n")

cat("2. Cox Hazard Ratio (風險比):", round(cox_sum$conf.int[1], 4), "\n")
cat(sprintf("   (處理組發芽勝算約為對照組的 %.2f 倍)\n", 1/cox_sum$conf.int[1]))
sink()

cat(sprintf("\n[系統] 分析完成！報表位於: %s\n", output_dir))
