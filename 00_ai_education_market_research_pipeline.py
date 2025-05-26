# dependencies for EDA
import pandas as pd
import numpy as np
from pandas_settings import configure_pandas_display

# dependencies for scrapping emails from websites
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse

# dependencies for sending emails
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

configure_pandas_display()  # importing func that ensures df isn't truncated

df = pd.read_csv("~/PycharmProjects/new_ai_project/edubasealldata20250224.csv", encoding='Windows-1252', low_memory=False)

# Viewing every type of PhaseOfEducation
(df["PhaseOfEducation (name)"]).value_counts()

# The below code cell shows the large majority of "Not Applicable" schools for "PhaseOfEducation" are below secondary
# education. This is because the large majority of schools in "Not Applicable" category have students with minimum age
# of below 11, so for now we'll leave "Not Applicable" schools out.
filtered_df = df.loc[
    (df["PhaseOfEducation (name)"] == "Not applicable") &
    (df["StatutoryLowAge"] > 10)
]
count = len(filtered_df)

# this shows a massive amount of schools closed or are due to close, so we can disregard them in below function.
df["EstablishmentStatus (name)"].value_counts()

## STEP 1: Creating Python script to filter target audience (secondary pupils and above)

def filter_schools(dataframe):
    # function below deletes everything included inside parenthesis, and leaves other values remaining in dataframe.
    return dataframe[
        ~dataframe["PhaseOfEducation (name)"].isin(["Primary", "Not applicable", "Nursery", "Middle deemed primary"]) &
        ~dataframe["EstablishmentStatus (name)"].isin(["Closed", "Open, but proposed to close"])]

revised_df = filter_schools(df)

revised_df["PhaseOfEducation (name)"].value_counts()

# As a result of our filtering, we have 3,717 schools that we can definitely market our product to.

## # Step 2: Build Python tool to find emails for target schools, digging to depth of 5 on their websites

# this shows 127 schools missing email, but vast majority do have email address
revised_df["SchoolWebsite"].isna().sum()

# dropping the 127 rows with missing school website
new_df = revised_df.dropna(subset=["SchoolWebsite"])

new_df["SchoolWebsite"].isna().sum()  # should print 0

# because this could take a long time, we first want to test our method with the first 20 websites.
# therefore, we'll take first 20 schools to scrape.
first_20_schools_df = new_df[:20].copy() # USING .copy() is important to avoid error after executing code below.
first_20_schools_df.shape # ensuring right dimensions for our small copy of new_df

# This lambda expression reformats emails that don't have 'https://' at start, so that BeautifulSoup can successfully
# land on website to search for email address.
first_20_schools_df["SchoolWebsite"] = first_20_schools_df["SchoolWebsite"].apply(
    lambda url: f"https://{url}" if not url.startswith(("http://", "https://")) else url)
# from my research, I've learnt even if the website starts with 'http', 'https' should redirect to the website!

# ------------------------ SCRAPPING EMAILS --------------------------

# initialise a set to track visited URLs to prevent revisiting
visited_urls = set()

def extract_email_from_url(url, depth=1, max_depth=5):
    if depth > max_depth:
        return None

    try:
        # send a GET request to the URL
        response = requests.get(url)
        if response.status_code == 200:
            # parse the HTML content
            soup = BeautifulSoup(response.text, 'html.parser')

            # search for email addresses using a regex pattern
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            emails = re.findall(email_pattern, soup.get_text())

            # if an email is found, return the first one
            if emails:
                return emails[0]

            # if no email found, try to find links to crawl (recursive)
            links = soup.find_all('a', href=True)
            for link in links:
                link_url = urljoin(url, link['href'])  # join relative URL with base URL
                if link_url not in visited_urls and urlparse(link_url).netloc == urlparse(url).netloc:  # same domain
                    visited_urls.add(link_url)
                    result = extract_email_from_url(link_url, depth + 1, max_depth)
                    if result:  # if email is found in one of the links, return it
                        return result
        else:
            return None
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None


# apply the function to the DataFrame, ensuring the URL is a string
first_20_schools_df['SchoolEmail'] = first_20_schools_df['SchoolWebsite'].apply(
    lambda x: extract_email_from_url(x, depth=1, max_depth=8) if isinstance(x, str) else None
)
# enhancing max_depth to 5, as shown above, led us to attain more emails successfully. This is because,
# max_depth params expands our search beyond website homepage, to 5 webpages deep inside the website!

# check the DataFrame to see the results
print(first_20_schools_df[['SchoolWebsite', 'SchoolEmail']])

## # STEP 3: Contacting the schools we've managed to attain email addresses for

# create dummy dataset
dummy_email_df = {'SchoolName': ['Hampstead School', "Islington Academy", "Camden Secondary School"],
        'ContactName': ['Nielsen Reaveley', "John Adams", "David Read"],
        'SchoolEmail': ['nareaveley@gmail.com', "john.adams@hotmail.com", "nareaveley@hotmail.com"]}

dummy_email_df = pd.DataFrame(dummy_email_df)

# ------------------------ SENDING EMAILS --------------------------

# define your email credentials
sender_email = "nareaveley@gmail.com"
sender_password = "hlbz vrrt xnyt vxmz"  # password generated from google 'app passwords' page.

# email list (ensure this is a list of email addresses, not a DataFrame column)
email_list = dummy_email_df["SchoolEmail"].tolist()  # convert to list if needed

# set up the server (Gmail in this example)
server = smtplib.SMTP("smtp.gmail.com", 587)
server.starttls()

# log in to your email account
server.login(sender_email, sender_password)

# send the email to each recipient in the list
for recipient_email in email_list:
    try:
        # gets the school name from the DataFrame
        school_name = dummy_email_df.loc[dummy_email_df["SchoolEmail"] == recipient_email, "SchoolName"].values[0]

        # set up the MIME
        subject = "Introducing EddyAI"
        body = f"""
        Dear {school_name}, 

        We hope this email finds you well. We would like to introduce you to EddyAI, a solution designed to help schools like {school_name} optimise their operations.
        We believe EddyAI could be a great fit for your needs and would love to discuss the technology further with you.

        Best regards,
        Nielsen 
        EddyAI Team
        """

        # create the email message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = recipient_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        # send the email
        server.sendmail(sender_email, recipient_email, message.as_string())
        print(f"Email sent to {recipient_email}")

    except Exception as e:
        print(f"Error sending email to {recipient_email}: {e}")

# close the server connection
server.quit()
