import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
import json
from requests.auth import HTTPBasicAuth
from config import AIRFLOW_USERNAME, AIRFLOW_PASSWORD, AIRFLOW_HOST

AIRFLOW__API__AUTH_BACKEND: "airflow.api.auth.backend.basic_auth"

# Function to get the time of the next offer
def get_next_offer_time():
    # Replace this with code to read the time from your database or file
    path = Path(__file__).with_name("todays_ids.json")
    path.touch()

    try:
        TODAYS_IDS: dict = json.loads(path.read_text().strip() or "{}")
    except UnicodeDecodeError:
        with open(path, encoding = "ISO-8859-1") as file:
            TODAYS_IDS: dict = json.loads(file.read().strip())
    # we add 2 minutes to be sure the content of the page is updated
    # and remove 1 hour for UTC to CET
    return datetime.strptime(TODAYS_IDS['Brack / daydeal.ch Tagesangebot']['next_sale_at'],
                             '%m/%d/%Y, %H:%M:%S') + timedelta(minutes=2) - timedelta(hours=1)

# Function to trigger the Airflow DAG
def trigger_dag():
    response = requests.post(
        f'http://{AIRFLOW_HOST}/api/v1/dags/brack/dagRuns',
        auth=HTTPBasicAuth(AIRFLOW_USERNAME, AIRFLOW_PASSWORD),
        json={
            'conf': {}  # Optional configuration for the DAG run
        },
    )
    response.raise_for_status()  # Raise an exception if the request failed

while True:
    time.sleep(300)  # Wait for 5 minutes so that today's ids is updated
    next_offer_time = get_next_offer_time()
    wait_time = (next_offer_time - datetime.now()).total_seconds()
    time.sleep(max(wait_time, 0))  # Wait until the next offer time
    trigger_dag()  # Trigger the DAG
