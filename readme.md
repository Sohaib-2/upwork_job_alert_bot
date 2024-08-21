# Job Alerts Upwork Bot

This project is a Python-based automation system designed to scrape job postings from Upwork based on specific keywords, save the job details in a MongoDB database, and send email alerts for new job postings.

## Features

- **Web Scraping**: Uses `cloudscraper` and `BeautifulSoup` to scrape job listings from Upwork.
- **MongoDB Integration**: Stores job details and keywords in MongoDB.
- **Email Notifications**: Sends email alerts for new job postings.
- **Logging**: Logs activity for monitoring and debugging purposes.
- **Scheduling**: Runs periodically to scrape and process job listings.

## Prerequisites

Before running the script, ensure that the following dependencies are installed:

### Python Packages

- `smtplib`
- `email.mime`
- `cloudscraper`
- `bs4` (BeautifulSoup)
- `schedule`
- `pymongo`
- `pytz`
- `logging`

You can install the required packages using pip:

```bash
pip install cloudscraper beautifulsoup4 schedule pymongo pytz
```

### MongoDB

Ensure MongoDB is installed and running on your local machine or a remote server. The script is configured to connect to a local MongoDB instance running on the default port `27017`.

### Gmail Setup

For sending email alerts, you need to set up a Gmail account with an App Password (if 2-Step Verification is enabled). Replace the placeholder in the script with your actual credentials.

```python
GMAIL_USERNAME = "your_email@gmail.com"
GMAIL_PASSWORD = "your_app_password"
```

## Configuration

### Keywords

Keywords are pre-defined in the script and stored in the MongoDB `keywords` collection. Each keyword will be used to search for jobs on Upwork.

### MongoDB Collections

- `keywords`: Stores keywords and their processing status.
- `jobs`: Stores details of the scraped jobs.

### SMTP Settings

The script uses Gmail's SMTP server to send email alerts. Ensure the SMTP credentials are correctly configured.

## Usage

1. **Insert Keywords (One-time Setup)**: The keywords are automatically inserted into the MongoDB collection during the first run.

2. **Initial Processing**: The script performs an initial scraping and job processing task. This ensures that any existing job listings are processed without sending alerts.

3. **Scheduler**: The script runs a scheduler that scrapes jobs for each keyword every 20 minutes and sends alerts for new jobs.

4. **Run the Script**:

   To start the job alerts system, simply run the script:

   ```bash
   python bot.py
   ```

5. **Logs**: All activities are logged in the `job_alerts.log` file for monitoring.

## Example Email Alert

Here’s an example of what an email alert might look like:

- **Subject**: New Job Alert: API Development Needed
- **Body**: The email contains details such as the job title, link, description, posted date, category, required skills, price type, and value.

## Scheduling Details

The job scraping and processing tasks are scheduled to run every 20 minutes. This interval can be adjusted as needed by modifying the scheduling configuration:

```python
schedule.every(20).minutes.do(process_keywords)
```
