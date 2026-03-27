#!/usr/bin/env Rscript

suppressWarnings(suppressMessages({
  args <- commandArgs(trailingOnly = TRUE)
}))

if (length(args) < 1) {
  stop("Usage: omega_sovereign_stats.R <csv-path>", call. = FALSE)
}

input_path <- args[[1]]
if (!file.exists(input_path)) {
  stop(sprintf("Input CSV not found: %s", input_path), call. = FALSE)
}

json_escape <- function(value) {
  value <- gsub("\\\\", "\\\\\\\\", value, fixed = FALSE)
  value <- gsub("\"", "\\\\\"", value, fixed = FALSE)
  value <- gsub("\n", "\\\\n", value, fixed = TRUE)
  value <- gsub("\r", "\\\\r", value, fixed = TRUE)
  value
}

as_json_string <- function(value) {
  sprintf("\"%s\"", json_escape(as.character(value)))
}

as_json_number <- function(value) {
  if (is.na(value) || is.nan(value) || is.infinite(value)) {
    return("null")
  }
  format(value, scientific = FALSE, trim = TRUE, digits = 12)
}

rows <- read.csv(input_path, stringsAsFactors = FALSE, check.names = FALSE)
if (!all(c("step", "status", "latency_ms") %in% names(rows))) {
  stop("CSV must include step, status, and latency_ms columns", call. = FALSE)
}

total_steps <- nrow(rows)
passed_steps <- sum(rows$status == "pass", na.rm = TRUE)
failed_steps <- sum(rows$status == "fail", na.rm = TRUE)
skipped_steps <- sum(rows$status == "skip", na.rm = TRUE)
success_rate <- if (total_steps > 0) passed_steps / total_steps else 0

latencies <- suppressWarnings(as.numeric(rows$latency_ms))
valid_latencies <- latencies[!is.na(latencies)]
mean_latency <- if (length(valid_latencies) > 0) mean(valid_latencies) else NA_real_
median_latency <- if (length(valid_latencies) > 0) median(valid_latencies) else NA_real_
max_latency <- if (length(valid_latencies) > 0) max(valid_latencies) else NA_real_
min_latency <- if (length(valid_latencies) > 0) min(valid_latencies) else NA_real_

cohesion_score <- round(success_rate * 100, 2)

status_counts <- c(
  pass = passed_steps,
  fail = failed_steps,
  skip = skipped_steps
)

status_json <- paste0(
  "{",
  paste(
    vapply(
      names(status_counts),
      function(name) sprintf("%s:%s", as_json_string(name), as_json_number(status_counts[[name]])),
      character(1)
    ),
    collapse = ","
  ),
  "}"
)

output <- paste0(
  "{",
  sprintf("%s:%s,", as_json_string("input_file"), as_json_string(input_path)),
  sprintf("%s:%s,", as_json_string("total_steps"), as_json_number(total_steps)),
  sprintf("%s:%s,", as_json_string("passed_steps"), as_json_number(passed_steps)),
  sprintf("%s:%s,", as_json_string("failed_steps"), as_json_number(failed_steps)),
  sprintf("%s:%s,", as_json_string("skipped_steps"), as_json_number(skipped_steps)),
  sprintf("%s:%s,", as_json_string("success_rate"), as_json_number(round(success_rate, 4))),
  sprintf("%s:%s,", as_json_string("cohesion_score"), as_json_number(cohesion_score)),
  sprintf("%s:%s,", as_json_string("latency_mean_ms"), as_json_number(round(mean_latency, 2))),
  sprintf("%s:%s,", as_json_string("latency_median_ms"), as_json_number(round(median_latency, 2))),
  sprintf("%s:%s,", as_json_string("latency_min_ms"), as_json_number(round(min_latency, 2))),
  sprintf("%s:%s,", as_json_string("latency_max_ms"), as_json_number(round(max_latency, 2))),
  sprintf("%s:%s", as_json_string("status_counts"), status_json),
  "}"
)

cat(output)
