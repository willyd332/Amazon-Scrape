# Main Script
  # From: CSV full of product urls
  # T


# libraries
library(openxlsx)
library(magrittr)
library(stringr)
library(purrr)
library(dplyr)

# Sources
source("./extract-reviews.R")

# Extract arguments
args <- commandArgs(trailingOnly=TRUE)
url_to_csv <- args[1]

url_to_csv <- "./urls.csv"

# Extract data from csv
urls_df <- read.csv(url_to_csv)

raw_urls <- urls_df$urls[urls_df$urls != ""]
product_urls <- unlist(lapply(raw_urls, clean_product_url))
product_titles <- unlist(lapply(product_urls, get_product_title))
review_urls <- unlist(lapply(product_urls, get_reviews_url))

urls_df <- data.frame(url = raw_urls, product_title = product_titles, review_url = review_urls)

# Extract requested reviews
review_df_holder <- list()

for(i in 1:length(product_urls)){
  review_df <- extract_reviews(review_urls[i])
  review_df_holder[[i]] <- review_df
}

# Output
output_location <- "./output_folder/output.xlsx"

# Define Styles
header_style <- createStyle(border="bottom", 
                            borderColour = "black", 
                            borderStyle = "thin", 
                            halign = "center",
                            valign = "center",
                            textDecoration = "bold")

date_style <- createStyle(numFmt = "mmmm dd, yyyy")

# Build Output
excel_output <- createWorkbook()  %T>%
  addWorksheet("URLs") %T>%
  writeData("URLs", urls_df) %T>%
  addStyle("URLs", header_style, rows = 1:1, cols = 1:100)

for(x in 1:length(product_urls)){
  temp <- excel_output %T>%
  addWorksheet(str_trunc(paste(toString(x), product_titles[[x]], sep = "-"), 30)) %T>%
  writeData(str_trunc(paste(toString(x), product_titles[[x]], sep = "-"), 30), review_df_holder[[x]]) %T>%
  addStyle(str_trunc(paste(toString(x), product_titles[[x]], sep = "-"), 30), date_style, rows = 1:100000, cols = 4:4) %T>%
  addStyle(str_trunc(paste(toString(x), product_titles[[x]], sep = "-"), 30), header_style, rows = 1:1, cols = 1:100)
}

activeSheet(excel_output) <- "URLs"

saveWorkbook(excel_output, output_location, overwrite = TRUE)