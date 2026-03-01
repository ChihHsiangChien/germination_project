suppressPackageStartupMessages(library(survival))
suppressPackageStartupMessages(library(ggplot2))
suppressPackageStartupMessages(library(showtext))
suppressPackageStartupMessages(library(survminer))
suppressPackageStartupMessages(library(readxl))
suppressPackageStartupMessages(library(dplyr))

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
output_dir <- file.path(proj_root, "temp_data", "cross_analysis")

cat(sprintf("[系統] 偵測專案根目錄: %s\n", proj_root))

if (!file.exists(input_file)) {
    stop(sprintf("錯誤: 找不到資料檔案 %s", input_file))
}

# 載入字體
load_chinese_font <- function() {
  font_name <- "noto"
  paths <- c(
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "C:/Windows/Fonts/msjh.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc"
  )
  
  for (f in paths) {
    if (file.exists(f)) {
      font_add(font_name, f)
      showtext_auto()
      showtext_opts(dpi = 300)
      return(font_name)
    }
  }
  return("sans")
}
MY_FONT <- load_chinese_font()

# 繪圖樣式
TARGET_FIG_WIDTH <- 8
TARGET_FIG_HEIGHT <- 5

my_theme <- theme_minimal() +
  theme(
    text = element_text(family = MY_FONT),
    plot.title = element_text(size = 14, hjust = 0.5, face = "bold"),
    plot.subtitle = element_text(size = 10, hjust = 0.5, color = "grey40", margin = margin(b=15)),
    axis.title = element_text(size = 12),
    axis.text = element_text(size = 10),
    legend.title = element_text(size = 11, face="bold"),
    legend.text = element_text(size = 10),
    legend.position = "right",
    panel.grid.major = element_line(linewidth = 0.4, color = "grey85"),
    panel.grid.minor = element_blank(),
    panel.border = element_rect(color = "grey80", fill=NA, linewidth=1)
  )

# ==========================================================
# [ 2. 資料處理 ]
# ==========================================================

# 通用時間處理函數 (支援從 Excel 讀入的數值)
parse_start_date <- function(d_col, t_col) {
  d <- as.numeric(d_col)
  t <- as.numeric(t_col)
  valid <- !is.na(d) & !is.na(t)
  res <- rep(as.POSIXct(NA), length(d))
  if (any(valid)) {
    dt_str <- paste0(format(Sys.Date(), "%Y"), sprintf("%04d%04d", d[valid], t[valid]))
    res[valid] <- as.POSIXct(dt_str, format = "%Y%m%d%H%M")
  }
  return(res)
}

process_sheet <- function(sheet_name, exp_label) {
  df <- read_excel(input_file, sheet = sheet_name)
  
  df$start_dt <- parse_start_date(df$start_date, df$start_time)
  df$germ_dt <- parse_start_date(df$germination_date, df$germination_time)
  
  df$status <- ifelse(is.na(df$germ_dt), 0, 1)
  
  if (any(!is.na(df$germ_dt))) {
    end_dt <- max(df$germ_dt, na.rm = TRUE) + (24 * 3600)
  } else {
    base_start <- min(df$start_dt, na.rm = TRUE)
    end_dt <- base_start + (14 * 24 * 3600)
  }
  
  df$time_hr <- as.numeric(difftime(
    ifelse(is.na(df$germ_dt), end_dt, df$germ_dt), 
    df$start_dt, units = "hours"
  ))
  
  df$Experiment <- exp_label
  # 統一標準化 Treatment 命名，避免大小寫不一致
  df$Treatment <- ifelse(tolower(df$treatment) == "treated", "Treated (去芒)", "Untreated (未去芒)")
  
  return(df[, c("time_hr", "status", "Experiment", "Treatment")])
}

cat("[系統] 正在讀取並合併兩個實驗的資料...\n")
df_exp1 <- tryCatch(process_sheet("germination", "Exp 1: 紙巾 (無阻力發芽)"), error=function(e) NULL)
df_exp2 <- tryCatch(process_sheet("soil_emergence", "Exp 2: 覆土 1cm (破土出苗)"), error=function(e) NULL)

if (is.null(df_exp1) || is.null(df_exp2)) {
  stop("錯誤: data.xlsx 必須同時包含 'germination' 與 'soil_emergence' 分頁。")
}

# 合併資料
df_combined <- bind_rows(df_exp1, df_exp2)

# ==========================================================
# [ 3. 統計與合併繪圖 ]
# ==========================================================
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

# 為了實現精確的透明度與線條控制，我們使用 survfit 然後用 ggplot 手動刻繪
fit <- survfit(Surv(time_hr, status) ~ Experiment + Treatment, data = df_combined)
surv_data <- surv_summary(fit, data = df_combined)

# survminer 預設會把原始分組變數當作新欄位加回 surv_data 裡，無需手動解析 strata
# 計算「累積發生率 (Cumulative Incidence)」: 100% - 存活率(surv)
surv_data$cum_inc <- 1 - surv_data$surv

# 自訂美學映射:
# 顏色: 代表去芒 vs 未去芒
# 線型: 實線 vs 虛線 代表 實驗二 vs 實驗一
# 透明度: 實驗一使用略微透明，實驗二保持實心不透明

cross_plot <- ggplot(surv_data, aes(x = time, y = cum_inc, color = Treatment, linetype = Experiment, alpha = Experiment)) +
  geom_step(linewidth = 1.2) +
  scale_color_manual(
    values = c("Treated (去芒)" = "#D55E00", "Untreated (未去芒)" = "#0072B2"),
    name = "瘦果處理 (Treatment)"
  ) +
  scale_linetype_manual(
    values = c("Exp 1: 紙巾 (無阻力發芽)" = "twodash", "Exp 2: 覆土 1cm (破土出苗)" = "solid"),
    name = "實驗環境 (Environment)"
  ) +
  scale_alpha_manual(
    values = c("Exp 1: 紙巾 (無阻力發芽)" = 0.5, "Exp 2: 覆土 1cm (破土出苗)" = 1.0),
    name = "實驗環境 (Environment)"
  ) +
  scale_y_continuous(labels = scales::percent, limits = c(0, 1)) +
  labs(
    title = "咸豐草瘦果：發芽潛力 vs 破土出苗 累積成功率比較",
    subtitle = "觀察虛線(紙巾)與實線(土壤)之間的水平落差(出土延遲)與垂直落差(未能出土之比例)",
    x = "經過時間 (小時)",
    y = "累積成功率 (發芽/出土) (%)"
  ) +
  my_theme

ggsave(file.path(output_dir, "cross_experiment_overlay.png"), plot = cross_plot, 
       width = TARGET_FIG_WIDTH, height = TARGET_FIG_HEIGHT, dpi = 300)

# ==========================================================
# [ 4. 生成交叉比對數據報告 ]
# ==========================================================
# 計算相關數據 (成功率 FEP 與 平均成功時間 MET)
calc_stats <- function(df_sub) {
  success_df <- df_sub[df_sub$status == 1, ]
  if(nrow(df_sub) == 0) return(c(fep = NA, met = NA))
  fep <- nrow(success_df) / nrow(df_sub) * 100
  met <- if(nrow(success_df) > 0) mean(success_df$time_hr) else NA
  return(c(fep = fep, met = met))
}

st_e1_t <- calc_stats(df_combined[df_combined$Experiment == "Exp 1: 紙巾 (無阻力發芽)" & df_combined$Treatment == "Treated (去芒)", ])
st_e1_u <- calc_stats(df_combined[df_combined$Experiment == "Exp 1: 紙巾 (無阻力發芽)" & df_combined$Treatment == "Untreated (未去芒)", ])
st_e2_t <- calc_stats(df_combined[df_combined$Experiment == "Exp 2: 覆土 1cm (破土出苗)" & df_combined$Treatment == "Treated (去芒)", ])
st_e2_u <- calc_stats(df_combined[df_combined$Experiment == "Exp 2: 覆土 1cm (破土出苗)" & df_combined$Treatment == "Untreated (未去芒)", ])

sink(file.path(output_dir, "cross_experiment_report.txt"))
cat("============================================================\n")
cat("      咸豐草實驗：發芽潛力 vs 破土出苗 (交叉分析報表)\n")
cat("============================================================\n\n")

cat("[一] 垂直落差：未能出土之比例 (Lethal Soil Zone / Vigor Loss)\n")
cat("  * 定義：種子在無阻力下能發芽，但在覆土中未能破土的比例。\n")
cat("  * 計算公式：(實驗一發芽率) - (實驗二出土率)\n\n")

cat("  【Treated (去芒) 組】\n")
cat(sprintf("    - 理論發芽潛力 (實驗一): %.1f %%\n", st_e1_t["fep"]))
cat(sprintf("    - 實際破土出苗 (實驗二): %.1f %%\n", st_e2_t["fep"]))
cat(sprintf("    => 覆土致死折損率: %.1f %%\n\n", st_e1_t["fep"] - st_e2_t["fep"]))

cat("  【Untreated (未去芒) 組】\n")
cat(sprintf("    - 理論發芽潛力 (實驗一): %.1f %%\n", st_e1_u["fep"]))
cat(sprintf("    - 實際破土出苗 (實驗二): %.1f %%\n", st_e2_u["fep"]))
cat(sprintf("    => 覆土致死折損率: %.1f %%\n\n", st_e1_u["fep"] - st_e2_u["fep"]))

diff_loss <- (st_e1_u["fep"] - st_e2_u["fep"]) - (st_e1_t["fep"] - st_e2_t["fep"])
if(diff_loss > 0) {
    cat(sprintf("  >> 結論：去芒組在土壤中折損較少！(未去芒組多死了 %.1f %%)\n\n", diff_loss))
} else {
    cat(sprintf("  >> 結論：去芒組在土壤中折損較多！(去芒組多死了 %.1f %%)\n\n", abs(diff_loss)))
}


cat("[二] 水平落差：出土延遲時間 (Emergence Delay)\n")
cat("  * 定義：種子突破土壤阻力所額外耗費的生长时间。\n")
cat("  * 計算公式：(實驗二平均破土時間 MET) - (實驗一平均發芽時間 MGT)\n\n")

cat("  【Treated (去芒) 組】\n")
cat(sprintf("    - 零阻力發芽時間 (實驗一): %.1f 小時\n", st_e1_t["met"]))
cat(sprintf("    - 覆土突破時間 (實驗二): %.1f 小時\n", st_e2_t["met"]))
cat(sprintf("    => 平均出土延遲: +%.1f 小時\n\n", st_e2_t["met"] - st_e1_t["met"]))

cat("  【Untreated (未去芒) 組】\n")
cat(sprintf("    - 零阻力發芽時間 (實驗一): %.1f 小時\n", st_e1_u["met"]))
cat(sprintf("    - 覆土突破時間 (實驗二): %.1f 小時\n", st_e2_u["met"]))
cat(sprintf("    => 平均出土延遲: +%.1f 小時\n\n", st_e2_u["met"] - st_e1_u["met"]))

diff_delay <- (st_e2_u["met"] - st_e1_u["met"]) - (st_e2_t["met"] - st_e1_t["met"])
if(diff_delay > 0) {
    cat(sprintf("  >> 結論：去芒組鑽土速度受阻礙較小！(未去芒組多花了 %.1f 小時才出土)\n", diff_delay))
} else {
    cat(sprintf("  >> 結論：去芒組鑽土速度受阻礙較大！(去芒組多花了 %.1f 小時才出土)\n", abs(diff_delay)))
}

sink()

cat(sprintf("[成功] R 已經成功繪製交叉比對圖表及純文字報告，並且存入: %s\n", output_dir))
