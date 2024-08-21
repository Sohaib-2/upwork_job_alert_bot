import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import cloudscraper
from bs4 import BeautifulSoup
import schedule
import time
from pymongo import MongoClient
from datetime import datetime, timedelta
import pytz
import re
import random
import logging

# Set up logging
logging.basicConfig(filename='job_alerts.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Set up MongoDB
client = MongoClient('localhost', 27017)
db = client['job_alerts']
keywords_collection = db['keywords']
jobs_collection = db['jobs']

# Insert Keywords into MongoDB (One-time setup)
keywords = ["web scraping", "API development", "mobile automation", "django", "fastapi", "flask", "adb automation", "selenium", "streamlit", "chatbot", "bot development", "discord bot", "web automation"]
for keyword in keywords:
    keywords_collection.update_one(
        {"keyword": keyword},
        {"$setOnInsert": {"status": False}},
        upsert=True
    )

# Flag to track the first run
first_run = True

# Gmail SMTP server setup
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
GMAIL_USERNAME = "youremail@gmail.com"
GMAIL_PASSWORD = " "  # App Password if 2-Step Verification is enabled

def send_email(subject, body, to_email):
    # Set up the MIME
    message = MIMEMultipart()
    message['From'] = GMAIL_USERNAME
    message['To'] = to_email
    message['Subject'] = subject

    # Attach the body with the msg instance (as HTML)
    message.attach(MIMEText(body, 'html'))

    # Create SMTP session for sending the mail
    session = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)  # Use Gmail with port
    session.starttls()  # Enable security
    session.login(GMAIL_USERNAME, GMAIL_PASSWORD)  # Login with your Gmail credentials

    # Convert the message to a string and send it
    text = message.as_string()
    session.sendmail(GMAIL_USERNAME, to_email, text)

    session.quit()
    logging.info(f"Mail sent to {to_email}")

def get_exact_time(posted_date_str):
    """
    Parse the 'Posted X minutes/hours ago' string and return the exact posting time.
    """
    now = datetime.now(pytz.utc)
    
    # Regular expressions to match minutes and hours
    minutes_match = re.search(r'(\d+)\s+minutes\s+ago', posted_date_str)
    hours_match = re.search(r'(\d+)\s+hours\s+ago', posted_date_str)
    
    if minutes_match:
        minutes_ago = int(minutes_match.group(1))
        return now - timedelta(minutes=minutes_ago)
    
    if hours_match:
        hours_ago = int(hours_match.group(1))
        return now - timedelta(hours=hours_ago)
    
    # Default to now if the pattern is not matched
    return now

# Function to scrape jobs for a given keyword using CloudScraper
def scrape_jobs(keyword):
    url = "https://www.upwork.com/nx/search/jobs/"
    params = {
        "q": f"({keyword.replace(' ', ' AND ')})",
        "sort": "recency",
        "page": "1"
    }

    # Create a CloudScraper instance
    scraper = cloudscraper.create_scraper()

    # Make the request
    response = scraper.get(url, params=params)
    logging.info(f"Fetching jobs from {url}... Status Code: {response.status_code}")

    # Decode the response content without decompression
    response_text = response.content.decode('utf-8', errors='replace')

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response_text, 'lxml')

    # Initialize a list to store the job data
    jobs_data = []

    # Find all job articles
    job_articles = soup.find_all('article', class_='job-tile')

    # Loop through each job article and extract relevant details
    for job in job_articles:
        job_data = {}
        
        # Extract the job title
        job_title = job.find('h2', class_='job-tile-title').get_text(strip=True)
        job_data['title'] = job_title
        
        # Extract the job URL
        job_url = job.find('a', class_='up-n-link')['href']
        job_data['url'] = f"https://www.upwork.com{job_url}"
        
        # Extract the posted date
        posted_date = job.find('small', {'data-test': 'job-pubilshed-date'}).get_text(strip=True)
        job_data['posted_date'] = posted_date
        
        # Extract the payment information
        payment_info = job.find('li', {'data-test': 'job-type-label'}).get_text(strip=True)
        job_data['payment_info'] = payment_info
        
        # Extract the experience level
        experience_level = job.find('li', {'data-test': 'experience-level'}).get_text(strip=True)
        job_data['experience_level'] = experience_level
        
        # Extract the duration and time commitment
        duration_info = job.find('li', {'data-test': 'duration-label'})
        if duration_info:
            job_data['duration_info'] = duration_info.get_text(strip=True)
        else:
            # For fixed-price jobs, budget instead of duration might be provided
            budget_info = job.find('li', {'data-test': 'is-fixed-price'})
            if budget_info:
                job_data['budget_info'] = budget_info.get_text(strip=True)
        
        # Extract the job description
        description = job.find('div', class_='air3-line-clamp').get_text(strip=True)
        job_data['description'] = description
        
        # Extract the required skills or tags
        skills = [skill.get_text(strip=True) for skill in job.find_all('span', {'data-test': 'token'})]
        job_data['skills'] = skills
        
        # Append the job data to the list
        jobs_data.append(job_data)

    return jobs_data

# Function to save new jobs to MongoDB and log details
def save_new_jobs(jobs, keyword, send_alerts=True):
    for job in jobs:
        job_id = job['url']
        if not jobs_collection.find_one({"_id": job_id}):
            # Calculate the exact publication time
            pub_date_utc = get_exact_time(job['posted_date'])
            pub_date_pst = pub_date_utc.astimezone(pytz.timezone('Asia/Karachi'))
            formatted_date = pub_date_pst.strftime('%Y-%m-%d %I:%M %p')

            job_data = {
                "_id": job_id,
                "title": job['title'],
                "link": job['url'],
                "description": job['description'],
                "pubDate": formatted_date,
                "category": job.get('experience_level', "N/A"),
                "skills": job.get('skills', ["N/A"]),
                "price_type": job.get('payment_info', "N/A"),
                "price_value": job.get('duration_info', job.get('budget_info', "N/A")),
                "keyword": keyword
            }
            
            jobs_collection.insert_one(job_data)

            # Send alerts only if it's not the first run
            if send_alerts:
                # Prepare the email content
                email_subject = f"New Job Alert: {job_data['title']}"
                
                email_body = f"""
                <html>
                    <body>
                        <table>
                            <tr>
                                <td><h2>New Job Alert: {job_data['title']}</h2></td>
                            </tr>
                            <tr>
                                <td><strong>Title:</strong> {job_data['title']}</td>
                            </tr>
                            <tr>
                                <td><strong>Link:</strong> <a href="{job_data['link']}">{job_data['link']}</a></td>
                            </tr>
                            <tr>
                                <td><strong>Description:</strong> {job_data['description']}</td>
                            </tr>
                            <tr>
                                <td><strong>Posted On:</strong> {job_data['pubDate']} (PST)</td>
                            </tr>
                            <tr>
                                <td><strong>Category:</strong> {job_data['category']}</td>
                            </tr>
                            <tr>
                                <td><strong>Skills:</strong> {', '.join(job_data['skills'])}</td>
                            </tr>
                            <tr>
                                <td><strong>Price Type:</strong> {job_data['price_type']}</td>
                            </tr>
                            <tr>
                                <td><strong>Price Value:</strong> {job_data['price_value']}</td>
                            </tr>
                            <tr>
                                <td><strong>Keyword:</strong> {job_data['keyword']}</td>
                            </tr>
                        </table>
                    </body>
                </html>
                """

                # Send the email
                send_email(email_subject, email_body, "recipient@gmail.com")

def process_keywords():
    global first_run
    keywords = list(keywords_collection.find({"status": False}))
    # Shuffle the list of keywords to process them in random order
    random.shuffle(keywords)
    for keyword in keywords:
        keyword_str = keyword['keyword']
        jobs = scrape_jobs(keyword_str)
        save_new_jobs(jobs, keyword_str, send_alerts=not first_run)
        keywords_collection.update_one({"_id": keyword['_id']}, {"$set": {"status": True}})
        time.sleep(random.uniform(20, 40))
    
    # Reset all statuses to False once all keywords are processed
    if keywords_collection.count_documents({"status": False}) == 0:
        keywords_collection.update_many({}, {"$set": {"status": False}})
        logging.info("All keywords processed. Resetting statuses.")

    # After the first run, set first_run to False
    first_run = False

# Set up the scheduler
schedule.every(20).minutes.do(process_keywords)

# Run initial processing
process_keywords()
# Run the scheduler
while True:
    schedule.run_pending()
    time.sleep(random.uniform(100, 300))
