# Scrape the reviews from a given Review Page URL



# 1 URL to 1 CSV

# Branch off Lambda
  # Get it to the point where an end point works first
# Link to amazon page
# Create csv
  # Consider how long it takes to scrape
  # Perhaps the Chrome Estension more throttleing (don't burn through GPT-3 and Good Marketing)
  # Consider how long it takes to analyze
# Save in S3
  # /get_presigned_url
# Return S3 Link
# Endpoint on Lambda


# libraries
library(httr)
library(purrr)
library(rvest)
library(dplyr)
library(tidyverse)
library(jsonlite)

# Sources
source("./helper-functions.R")

# Extract reviews into a DF
extract_reviews <- function(review_page_url){
  print(review_page_url)
  # Get the HTML
  html <- GET(review_page_url) %>%
    check_error() %>%
    content()
  print(html)
  # Get the total number of reviews
  total_number_reviews <- html %>%
    html_nodes(xpath = '//*[@id="filter-info-section"]/div') %>%
    html_text(trim = T)
  print(total_number_reviews)
  total_number_reviews <- gsub(",","", strsplit(total_number_reviews, " ", fixed = TRUE)[[1]][4]) %>%
    as.numeric()
  # Total number of pages
  total_pages <- ceiling(total_number_reviews / 10)
  # Scrape the reviews
  review_holder <- list()
  for (i in 1:(total_pages-1)){
    if (i == 1){
      print(paste0("Extracting Reviews... Page: ", toString(i), "/", toString(total_pages)))
    } else {
      if (i%%10 == 0){
        print(paste0("Extracting Reviews... Page: ", toString(i), "/", toString(total_pages)))
      }
      # Get new page URL
      html <- paste(review_page_url, "?pageNumber=", toString(i), sep = "") %>%
        GET() %>%
        check_error(isPrint=FALSE) %>%
        content()
    }
    reviews_html <- html %>%
      html_nodes(xpath = "//div[@class = 'a-section review aok-relative']") %>%
      html_nodes(xpath = "//div[@class = 'a-section celwidget']") %>%
      map_df(~{
        Customer_Name = html_nodes(.x, xpath = "./div[position() = 1]//span[@class = 'a-profile-name']") %>%
          html_text()
        Number_Of_Stars = html_nodes(.x, xpath = "./div[position() = 2]/a[position() = 1]") %>%
          html_attr('title')
        Number_Of_Stars = strsplit(Number_Of_Stars, split = " ")[[1]][1]
        Review_Headline = html_nodes(.x, xpath = "./div[position() = 2]/a[position() = 2]//span") %>%
          html_text(trim = T)
        Date_Reviewed = html_nodes(.x, xpath = "./span[@data-hook = 'review-date']") %>%
          html_text()
        # Extract Date
        Split_Date_Reviewed = strsplit(Date_Reviewed, split = " ")
        len_Date = length(Split_Date_Reviewed[[1]])
        Date_Reviewed = paste(Split_Date_Reviewed[[1]][len_Date-2], Split_Date_Reviewed[[1]][len_Date-1], Split_Date_Reviewed[[1]][len_Date])
        Verification = html_nodes(.x, xpath = "./div[position() = 3]//span") %>%
          html_text()
        # Check Verified
        a <- character(0)
        if (identical(a, Verification)){
          Verification <- "Unverified"
        }
        Review = html_nodes(.x, xpath = "./div[position() = 4]//span[@data-hook = 'review-body']//span") %>%
          html_text(trim = T)
        # helpfulRating = html_nodes(.x, xpath = "./div[position() = 5]//span[@data-hook = 'helpful-vote-statement']") %>%
        #   html_text()
        # print(helpfulRating)
        # Make DF
        # review_holder[i] <- data.frame(Customer_Name, Number_Of_Stars, Review_Headline, Date_Reviewed, Verification, review, helpfulRating)
        
        length_list <- c(length(Customer_Name), length(Number_Of_Stars), length(Review_Headline), length(Date_Reviewed), length(Verification), length(Review))
        max_length <- max(length_list)
        length(Customer_Name) <- max_length
        length(Number_Of_Stars) <- max_length
        length(Review_Headline) <- max_length
        length(Date_Reviewed) <- max_length
        length(Verification) <- max_length
        length(Review) <- max_length
        data.frame(Customer_Name, Number_Of_Stars, Review_Headline, Date_Reviewed, Verification, Review)
      })
    review_holder[[i]] <- reviews_html
  }
  # Combine reviews into a single Data Frame
  reviews_df <- bind_rows(review_holder)
  return(reviews_df)
}
 