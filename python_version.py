# Imports
from lxml import html
import requests
import re
import math
import pandas as pd
import time
import logging
import random
import json
import scrapy
from scrapy.crawler import CrawlerProcess
from api.modules.s3_upload import upload_file_to_s3
from api.modules.s3_config import bucket_name, bucket_name_cluster
bucket_name = bucket_name_cluster

# ----------------------------------------
# Helper Functions
# ----------------------------------------

# GLOBAL VARIABLES
MAX_RUNTIME = 50 # +/- 3 Seconds

# Mimic browser to avoid CAPATCH
def generate_request_header():
  '''
  No input
  Generate headers to mimic a browser while randomly cycling between common use agents
  Return a header object to use for requests
  '''
  # Created July 25, 2022
  user_agent_list = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.5 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.74 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:102.0) Gecko/20100101 Firefox/102.0"
  ]
  this_user_agent = random.choice(user_agent_list)
  headers = {
    "User-Agent": this_user_agent,
    "Accept-Encoding": "gzip, deflate", 
    "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", 
    "DNT":"1",
    "Connection":"close", 
    "Upgrade-Insecure-Requests":"1"
  }
  return headers

def generate_request_proxy():
  # Call 3rd party API to get proxy
      # https://member.proxyrack.com/access/member
      # sifron
      # Fn4$MXvatzC!87CX
  # Add to dictionary
  # Return
  proxies = {

  }
  return proxies

# Clean a product URL
def clean_product_url(product_url):
  '''
  Takes in a product url as a string
  Cleans the string to this: https://www.amazon.com/*PRODUCT_NAME*/dp/*PRODUCT_CODE*
  Returns the clean url
  '''
  split_url = product_url.split("/")
  clean_url = split_url[0] +  "/" + split_url[1] +  "/" + split_url[2] +  "/" + split_url[3] +  "/" + split_url[4] +  "/" + split_url[5]
  return(clean_url) # https://www.amazon.com/*PRODUCT_NAME*/dp/*PRODUCT_CODE*

# Get reviews url from product URL
def get_reviews_url(product_url):
  '''
  Takes in a product url as a string
  Generates a link to the reviews page: https://www.amazon.com/*PRODUCT_NAME*/product-reviews/*PRODUCT_CODE*
  Returns the review page url
  '''
  split_url = product_url.split("/")
  clean_url = split_url[0] +  "/" + split_url[1] +  "/" + split_url[2] +  "/" + split_url[3] +  "/" + "product-reviews" +  "/" + split_url[5] + "?reviewerType=all_reviews"
  return(clean_url) # https://www.amazon.com/*PRODUCT_NAME*/product-reviews/*PRODUCT_CODE*


# Get The Product Title From URL
def get_product_title(url):
  '''
  Takes in amazon product url
  Returns the name of the product
  '''
  product_title = url.split("/")[3]
  return(product_title)

def throttle_reviews(number_of_pages, max_time):

  # UPDATED -- ABOUT 300 SECONDS FOR 983 PAGES OF REVIEWS

  '''
  Takes in the total number of pages and the maximum time allowed (in seconds)
  Calculates the maximum allowed pages (roughly 3.2 pages per second or .3 seconds per page)
  Returns the min of that and number_of_pages
  '''
  max_pages = math.ceil(max_time / 0.3)
  return min(max_pages, number_of_pages)

def get_number_of_pages(review_page_url):
  '''
  Input the url to a review page
  Scrape the number of reviews from that page with a simple request
  Return the number of review pages for that product
  '''
  # Try Each Request 3 Times
  for i in range(3):
    try:
      # Get the HTML
      html_response = requests.get(review_page_url, headers=generate_request_header())
    except requests.exceptions.Timeout:
      logging.debug("Request Timed Out, Waiting 3 Seconds Before Retrying")
      time.sleep(3)
      continue
    except requests.exceptions.RequestException as e:
      print("Server Error - Response: " + str(html_response.status_code))
      html_response.raise_for_status()
    # Print Status Code
    print("Status Code: " + str(html_response.status_code))
    break

  # Create HTML Object
  html_text = html_response.text
  html_object = html.fromstring(html_text)

  # Get the total number of reviews
  try:
    total_number_reviews_text = html_object.xpath("//div[@data-hook = 'cr-filter-info-review-rating-count']/text()")[0].strip()
  except IndexError as e:
    print(html_text)
    print("--------")
    print("Extraction Failed... likely due to Captcha -- SEE HTML ABOVE & ERROR BELOW")
    print("--------")
    print(e)

  # Get review number
  total_number_reviews = int(re.sub(",","", total_number_reviews_text.split(" ")[3]))
  # Total number of pages
  total_pages = math.ceil(total_number_reviews / 10)
  return total_pages

def generate_url_list(review_page_url, numb_of_pages):
  '''
  Input the seed url for a review page and the number of pages
  Generate a list of urls to scrape
  Return list of urls
  '''
  # https://www.amazon.com/*PRODUCT_NAME*/product-reviews/*PRODUCT_CODE*
  # "?ie=UTF8&reviewerType=all_reviews&pageNumber="
  seed_url = review_page_url + "?ie=UTF8&reviewerType=all_reviews&pageNumber="
  pages_list = range(1, numb_of_pages)
  starting_urls = [seed_url + str(num) for num in pages_list]
  return starting_urls

# ----------------------------------------
# Extract Reviews (RUNTIME IS ABOUT 40 SECONDS PER 1000 REVIEWS... OR 25 pages of reviews every 10 seconds)
# ----------------------------------------

# Extract reviews into a DF
def extract_reviews(review_page_url):
  '''
  Input the URL to an amazon review page
  Scrape the page to extract customer names, stars, headlines, verification, dates, and review body
  Output a Pandas DF that containes all of the review information
  '''

  # Try Each Request 3 Times
  for i in range(3):
    try:
      # Get the HTML
      html_response = requests.get(review_page_url, headers=generate_request_header())
    except requests.exceptions.Timeout:
      logging.debug("Request Timed Out, Waiting 3 Seconds Before Retrying")
      time.sleep(3)
      continue
    except requests.exceptions.RequestException as e:
      print("Server Error - Response: " + str(html_response.status_code))
      html_response.raise_for_status()
    # Print Status Code
    print("Status Code: " + str(html_response.status_code))
    break

  # Create HTML Object
  html_text = html_response.text
  html_object = html.fromstring(html_text)

  # Get the total number of reviews
  try:
    total_number_reviews_text = html_object.xpath("//div[@data-hook = 'cr-filter-info-review-rating-count']/text()")[0].strip()
  except IndexError as e:
    print(html_text)
    print("--------")
    print("Extraction Failed... likely due to Captcha -- SEE HTML ABOVE & ERROR BELOW")
    print("--------")
    print(e)


  total_number_reviews = int(re.sub(",","", total_number_reviews_text.split(" ")[3]))
  # Total number of pages
  total_pages = math.ceil(total_number_reviews / 10)
  throttled_pages = throttle_reviews(total_pages, MAX_RUNTIME)
  # Scrape the reviews
  review_holder = []
  for i in range(throttled_pages):
    if i == 0:
      print(f'Extracting Reviews... Page: {str(i)}/{str(throttled_pages)}')
    else:
      if i % 10 == 0:
        print(f'Extracting Reviews... Page: {str(i)}/{str(throttled_pages)}')
      # Get new page URL
      new_url = review_page_url + "&pageNumber=" + str(i)
      # Try Each Request 3 Times
      for i in range(3):
        try:
          # Get the HTML
          html_response = requests.get(new_url, headers=generate_request_header())
        except requests.exceptions.Timeout:
          logging.debug("Request Timed Out, Waiting 3 Seconds Before Retrying")
          time.sleep(3)
          continue
        except requests.exceptions.RequestException as e:
          print("Server Error - Response: " + str(html_response.status_code))
          html_response.raise_for_status()
        # Print Status Code
        break
      html_text = html_response.text
      html_object = html.fromstring(html_text)
    reviews_html = html_object.xpath("//div[@class = 'a-section review aok-relative']//div[@class = 'a-section celwidget']") 
    # Generate Series For DF
    try:
      # Get Names Of Customer
      Customer_Name_list = [review.xpath("./div[position() = 1]//span[@class = 'a-profile-name']/text()")[0].strip() for review in reviews_html]
      # Get number of stars
      Number_Of_Stars_list = [review.xpath("./div[position() = 2]/a[position() = 1]")[0].attrib['title'] for review in reviews_html]
      Number_Of_Stars_list = [float(stars.split(" ")[0]) for stars in Number_Of_Stars_list]
      # Get review headline
      Review_Headline_list = [review.xpath("./div[position() = 2]/a[position() = 2]/span/text()")[0].strip() for review in reviews_html]
      # Get date reviewed
      Date_Reviewed_list = [review.xpath("./span[@data-hook = 'review-date']/text()")[0].strip() for review in reviews_html]
      # Get purchase varification
      Verification_list = [review.xpath("./div[position() = 3]//span[@data-hook = 'avp-badge']/text()")[0].strip() 
                          if (len(review.xpath("./div[position() = 3]//span[@data-hook = 'avp-badge']/text()")) > 0) 
                          else "Unverified Purchase" for review in reviews_html]
      # Get the body of the review
      Review_list = [review.xpath("./div[position() = 4]//span[@data-hook = 'review-body']/span/text()")[0].strip()
                    if (len(review.xpath("./div[position() = 4]/span[@data-hook = 'review-body']//span/text()")) > 0)
                    else "" for review in reviews_html]
      # Get the number of people who found the review helpful
      Helpful_List = [review.xpath("./div//span[@data-hook =  'helpful-vote-statement']/text()")[0].strip().split()[0]
                      if (len(review.xpath("./div//span[@data-hook =  'helpful-vote-statement']/text()")) > 0) 
                      else "" for review in reviews_html] 
      Helpful_List = [1 if helpful == "One" else helpful for helpful in Helpful_List]
      # Get any Metadata (e.g. Size, Color, Flavor)
      Meta_Data_List = [review.xpath("./div[position() = 3]//a[@data-hook = 'format-strip']/text()")
                        if (len(review.xpath("./div[position() = 3]//a[@data-hook = 'format-strip']/text()")) > 0) 
                        else 0 for review in reviews_html] 


    except:
      print(f"Unable to retrieve reviews for page: {i}")
    
    # Build and push the DF
    this_review_page_df = pd.DataFrame({
      "Customer Name": Customer_Name_list,
      "Number Of Stars": Number_Of_Stars_list,
      "Review Headline": Review_Headline_list,
      "Date Reviewed": Date_Reviewed_list,
      "Verified Customer": Verification_list,
      "Review Body": Review_list,
      "Found Helpful": Helpful_List,
      "Metadata": Meta_Data_List
    })
    review_holder.append(this_review_page_df)
  # Combine reviews into a single Data Frame
  reviews_df = pd.concat(review_holder)
  return(reviews_df)


# ----------------------------------------
# Scrapy Class
# ----------------------------------------

class AmazonReviewsSpider(scrapy.Spider):
    name = "AmazonReviews"
    allowed_domains = ['amazon.com']

    custom_settings = { # https://docs.scrapy.org/en/latest/topics/settings.html?highlight=custom_settings#topics-settings-ref
        'CONCURRENT_REQUESTS': 25,
        'DOWNLOAD_DELAY': 0.25
    }

    headers = generate_request_header()

    temporary_storage = []

    def start_requests(self):
      urls = self.urls
      for url in urls:
          yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
      # Start with Reviews HTML
      html_text = response.text
      html_object = html.fromstring(html_text)
      reviews_html = html_object.xpath("//div[@class = 'a-section review aok-relative']//div[@class = 'a-section celwidget']") 
      # Get Names Of Customer
      Customer_Name_list = [review.xpath("./div[position() = 1]//span[@class = 'a-profile-name']/text()")[0].strip() for review in reviews_html]
      # Get number of stars
      Number_Of_Stars_list = [review.xpath("./div[position() = 2]/a[position() = 1]")[0].attrib['title'] for review in reviews_html]
      Number_Of_Stars_list = [float(stars.split(" ")[0]) for stars in Number_Of_Stars_list]
      # Get review headline
      Review_Headline_list = [review.xpath("./div[position() = 2]/a[position() = 2]/span/text()")[0].strip() for review in reviews_html]
      # Get date reviewed
      Date_Reviewed_list = [review.xpath("./span[@data-hook = 'review-date']/text()")[0].strip() for review in reviews_html]
      # Get purchase varification
      Verification_list = [review.xpath("./div[position() = 3]//span[@data-hook = 'avp-badge']/text()")[0].strip() 
                          if (len(review.xpath("./div[position() = 3]//span[@data-hook = 'avp-badge']/text()")) > 0) 
                          else "Unverified Purchase" for review in reviews_html]
      # Get the body of the review
      Review_list = [review.xpath("./div[position() = 4]//span[@data-hook = 'review-body']/span/text()")[0].strip()
                    if (len(review.xpath("./div[position() = 4]/span[@data-hook = 'review-body']//span/text()")) > 0)
                    else "" for review in reviews_html]
      # Get the number of people who found the review helpful
      Helpful_List = [review.xpath("./div//span[@data-hook =  'helpful-vote-statement']/text()")[0].strip().split()[0]
                      if (len(review.xpath("./div//span[@data-hook =  'helpful-vote-statement']/text()")) > 0) 
                      else 0 for review in reviews_html] 
      Helpful_List = [1 if helpful == "One" else helpful for helpful in Helpful_List]
      # Get any Metadata (e.g. Size, Color, Flavor)
      Meta_Data_List = [review.xpath("./div[position() = 3]//a[@data-hook = 'format-strip']/text()")
                        if (len(review.xpath("./div[position() = 3]//a[@data-hook = 'format-strip']/text()")) > 0) 
                        else "" for review in reviews_html] 
      # Create DF to store the data for this page
      this_review_page_df = pd.DataFrame({
        "Customer Name": Customer_Name_list,
        "Number Of Stars": Number_Of_Stars_list,
        "Review Headline": Review_Headline_list,
        "Date Reviewed": Date_Reviewed_list,
        "Verified Customer": Verification_list,
        "Review Body": Review_list,
        "Found Helpful": Helpful_List,
        "Metadata": Meta_Data_List
      })
      # Save DF to temporary storage
      self.temporary_storage.append(this_review_page_df)



# ----------------------------------------
# Main (Product Url -> S3 Url to CSV File)
# ----------------------------------------

def get_amazon_reviews(user_id, product_url):
  '''
  Take in a amazon product url
  Returns url to csv of amazon products stored in S3
  '''
  # Get the starting urls
  clean_url = clean_product_url(product_url)
  reviews_url = get_reviews_url(clean_url)
  product_title = get_product_title(clean_url)
  num_pages = get_number_of_pages(reviews_url)
  # Throttle Reveiws So it's not too much time
  num_pages = throttle_reviews(num_pages)

  starting_urls = generate_url_list(reviews_url, num_pages)
  
  # Run Scrapy
  process = CrawlerProcess()
  process.crawl(AmazonReviewsSpider, urls = starting_urls)
  process.start()

  # Output DF to S3
  combined_df = pd.concat(AmazonReviewsSpider.temporary_storage)
  object_name = f"{product_title}.csv"
  combined_df.to_csv('/tmp/result_amazon.csv', index=False)
  url = upload_file_to_s3(
    file_name='/tmp/result_amazon.csv', 
    user_id=user_id, 
    bucket=bucket_name, 
    folder_name = 'csv', 
    object_name=object_name, 
    type = 'csv'
  )
  return {"url": url}



# scrapy.Request(url=url, callback=self.parse_data, meta={"proxy": self.settings.get("PROXY_HOST")})