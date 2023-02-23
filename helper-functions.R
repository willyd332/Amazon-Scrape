# Helper Functions
# Scrape a single product
# libraries
library(httr)
library(purrr)
library(rvest)
library(dplyr)
library(tidyverse)
library(jsonlite)
library(glue)

# Check for error after a request
check_error <- function(JSON_response, isPrint = TRUE){
  if (http_error(JSON_response)){
    stop(paste0("Server Error - Response: ", toString(status_code(JSON_response))))
  } else {
    if (isPrint){
      print(paste0("Status Code: ", toString(status_code(JSON_response)))) 
    }
    return(JSON_response) 
  }
}

# Clean a product URL
clean_product_url <- function(product_url){
  split_url = strsplit(product_url, "/")[[1]]
  clean_url = paste(split_url[1], split_url[2], split_url[3], split_url[4], split_url[5], split_url[6], sep="/")
  return(clean_url) # https://www.amazon.com/*PRODUCT_NAME*/dp/*PRODUCT_CODE*
}

# Get reviews url from product URL
get_reviews_url <- function(product_url){
  split_url = strsplit(product_url, "/")[[1]]
  clean_url = paste(split_url[1], split_url[2], split_url[3], split_url[4], "product-reviews", split_url[6], sep="/")
  return(clean_url) # https://www.amazon.com/*PRODUCT_NAME*/product-reviews/*PRODUCT_CODE*
}

# Get The Product Title From URL
get_product_title <- function(url){
  product_title <- strsplit(url, "/")[[1]][4]
  return(product_title)
}