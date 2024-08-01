import requests
import os
import json
import pandas as pd
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from IPython.display import display, HTML
from pymongo import MongoClient

# Your Strava API client ID and secret
client_id =
client_secret = ''
initial_refresh_token = ''  # Replace with your initial refresh token

# Club ID
club_id = #you club id cleck on share button at club in the chrome then club id shown in the embedded url

# MongoDB connection
mongo_client = MongoClient('your mongodb data url with id pasasword', serverSelectionTimeoutMS=60000)
db = mongo_client['strava_data']
collection = db['activities']

from streamlit_autorefresh import st_autorefresh

# Set the refresh interval in milliseconds (e.g., 60000 for 1 minute)
refresh_interval = 120000  # 60 seconds

# This function will refresh the app
st_autorefresh(interval=refresh_interval, key="dataframerefresh")

# Function to load tokens from MongoDB
def load_tokens():
    tokens = collection.find_one({'type': 'tokens'})
    if tokens:
        return tokens['tokens']
    return None

# Function to save tokens to MongoDB
def save_tokens(tokens):
    collection.update_one({'type': 'tokens'}, {'$set': {'tokens': tokens}}, upsert=True)

# Function to refresh access token
def refresh_access_token():
    tokens = load_tokens()
    if tokens is None:
        tokens = {
            'refresh_token': initial_refresh_token,
            'expires_at': 0
        }

    if datetime.now().timestamp() > tokens['expires_at']:
        response = requests.post(
            'https://www.strava.com/api/v3/oauth/token',
            data={
                'client_id': client_id,
                'client_secret': client_secret,
                'grant_type': 'refresh_token',
                'refresh_token': tokens['refresh_token']
            }
        )

        if response.status_code != 200:
            print(f"Failed to refresh token: {response.status_code} - {response.text}")
            return None

        new_tokens = response.json()
        if 'access_token' not in new_tokens or 'refresh_token' not in new_tokens or 'expires_at' not in new_tokens:
            print(f"Invalid response from token refresh: {new_tokens}")
            return None

        tokens['access_token'] = new_tokens['access_token']
        tokens['refresh_token'] = new_tokens['refresh_token']
        tokens['expires_at'] = new_tokens['expires_at']
        save_tokens(tokens)

    return tokens['access_token']

# Function to convert meters to kilometers
def meters_to_kilometers(meters):
    return meters / 1000

# Function to format seconds to hh:mm:ss
def format_seconds_to_hhmmss(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

# Function to fetch club activities
def fetch_club_activities(club_id, page, per_page):
    url = f"https://www.strava.com/api/v3/clubs/{club_id}/activities"
    access_token = refresh_access_token()

    if access_token is None:
        return None

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    params = {
        'page': page,
        'per_page': per_page
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        fetch_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        activities = response.json()
        for activity in activities:
            activity['inferred_start_time'] = fetch_time
        return activities
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Strava API: {e}")
        return None

# Function to convert meters to kilometers
def meters_to_kilometers(meters):
    return meters / 1000

# Function to format seconds to hh:mm:ss
def format_seconds_to_hhmmss(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

# Function to fetch club activities
def fetch_club_activities(club_id, page, per_page):
    url = f"https://www.strava.com/api/v3/clubs/{club_id}/activities"
    access_token = refresh_access_token()

    if access_token is None:
        return None

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    params = {
        'page': page,
        'per_page': per_page
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        fetch_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        activities = response.json()
        for activity in activities:
            activity['inferred_start_time'] = fetch_time
        return activities
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Strava API: {e}")
        return None

# Notebook display setup
def display_activities(activities):
    if activities:
        print("Daily Performance:")
        data = []
        for activity in activities:
            athlete_name = f"{activity['athlete']['firstname']} {activity['athlete']['lastname']}"
            moving_time = activity['moving_time']
            moving_time_only = moving_time.split(' ')[1]  # Extract only the time part
            type = activity['type']
            data.append({
                'Athlete': athlete_name,
                'type': type,
                'Moving Time (hh:mm:ss)': moving_time_only
            })
        display(pd.DataFrame(data))
    else:
        print("No activities fetched.")


# Function to fetch and parse Strava activities from iframe URL
def fetch_and_parse_activities(iframe_url):
    # Function to convert seconds to hh:mm:ss format
    def format_seconds_to_hhmmss(seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

    # Function to parse time string to seconds
    def parse_time_to_seconds(time_str):
        # Assuming time_str is in format hh:mm:ss or mm:ss
        parts = time_str.split(':')
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
        elif len(parts) == 2:
            hours = 0
            minutes = int(parts[0])
            seconds = int(parts[1])
        else:
            return 0  # Return 0 if time format is not recognized

        total_seconds = hours * 3600 + minutes * 60 + seconds
        return total_seconds

    # Fetch HTML content of the iframe URL
    response = requests.get(iframe_url)
    html_content = response.text

    # Parse the HTML using BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    activities = soup.find_all('li')

    parsed_activities = []

    for activity in activities:
        athlete_name_elem = activity.find('p', class_='athlete-name')
        if athlete_name_elem:
            athlete_name = athlete_name_elem.get_text(strip=True)
        else:
            continue  # Skip this activity if athlete name is not found

        activity_name_elem = activity.find('strong').find('a') if activity.find('strong') else None
        if activity_name_elem:
            activity_name = activity_name_elem.get_text(strip=True)
        else:
            activity_name = "Activity name not found"

        stats_elem = activity.find('ul', class_='stats')
        if stats_elem:
            stats_items = stats_elem.find_all('li')
            if len(stats_items) >= 3:
                distance = stats_items[0].get_text(strip=True)
                moving_time_seconds = parse_time_to_seconds(stats_items[1].get_text(strip=True))  # Convert time to seconds
                moving_time = format_seconds_to_hhmmss(moving_time_seconds)  # Format time to hh:mm:ss
                elevation_gain = stats_items[2].get_text(strip=True)
            else:
                distance = "Distance not found"
                moving_time = "Moving time not found"
                elevation_gain = "Elevation gain not found"
        else:
            distance = "Stats not found"
            moving_time = "Stats not found"
            elevation_gain = "Stats not found"

        timestamp_elem = activity.find('p', class_='timestamp')
        if timestamp_elem:
            Date = timestamp_elem.get_text(strip=True)
        else:
            Date = "Timestamp not found"

        # Append parsed data to the list
        parsed_activities.append({
            'athlete_name': athlete_name,
            'distance_': distance,
            'moving__time': moving_time,
            'elevation_gain': elevation_gain,
            'Date': Date
        })

    return parsed_activities

# URL from the iframe src attribute
iframe_url = 'https://www.strava.com/clubs/1272495/latest-rides/a9ebd92db8660ca5181352d5365a54abe9a534db?show_rides=true'

# Fetch and parse activities
parsed_activities = fetch_and_parse_activities(iframe_url)
activities = fetch_club_activities(club_id, page=1, per_page=5)

# Convert lists to DataFrames
parsed_activities_df = pd.DataFrame(parsed_activities)
activities_df = pd.DataFrame(activities)

# Merge or concatenate based on athlete names
merged_data = pd.concat([parsed_activities_df, activities_df], axis=1)
columns_to_drop=['moving_time', 'distance','resource_state','athlete','name','elapsed_time','total_elevation_gain','workout_type','sport_type','inferred_start_time']
merged_data = merged_data.drop(columns=columns_to_drop)
def check_and_insert_data(new_data):
    for item in new_data:
        if not collection.find_one(item):
            collection.insert_one(item)
    print("Data inserted into MongoDB!")

# Convert merged data to dictionary records
merged_data_records = merged_data.to_dict('records')

# Insert new data into MongoDB
check_and_insert_data(merged_data_records)



# Insert data into MongoDB
# collection.insert_many(merged_data.to_dict('records'))



# Load data from MongoDB
import streamlit as st
import pandas as pd
from pymongo import MongoClient

# MongoDB connection


# Load data from MongoDB
def load_data():
    data = collection.find()
    df = pd.DataFrame(list(data))

    cc=['_id','tokens']
    df = df.drop('_id', axis=1)  # Remove _id column
    return df

# Create a Streamlit app
st.title("Mansoon Masti")

# Create a selectbox to choose the page
page = st.selectbox("Select a page", ["Leaderboard", "Daily Activities"])



if page == "Daily Activities":
    # Show the daily activities page
    st.header("Daily Activities")
    st.write("Showing newest activities first")
    df = load_data()
    df['Date'] = pd.to_datetime(df['Date'])
    st.dataframe(df.iloc[::-1])
elif page == "Leaderboard":
    # Show the leaderboard page
    st.header("Leaderboard")
    st.write("Showing total distance by athlete")
    start_date = st.date_input("Start date", value=pd.to_datetime("2024-07-20"))
    end_date = st.date_input("End date")

    # Convert start_date and end_date to datetime type
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    # Load data from MongoDB
    df = load_data()
    df['Date'] = pd.to_datetime(df['Date'])

    # Filter the data based on the selected filters
    df_filtered = df
    df_filtered = df_filtered[(df_filtered['Date'] >= start_date) & (df_filtered['Date'] <= end_date)]

    # Convert distance_ column to numeric values
    df_filtered['distance_'] = pd.to_numeric(df_filtered['distance_'].str.replace(' km', ''))

    # Create new columns 'ride' and 'run'
    df_filtered['ride'] = df_filtered['distance_'].where(df_filtered['type'] == 'Ride')
    df_filtered['run'] = df_filtered['distance_'].where(df_filtered['type'] == 'Run')

    # Group the data by athlete and calculate the total distance
    leaderboard = df_filtered.groupby('athlete_name')[['ride', 'run']].sum().reset_index()
    leaderboard['run_points'] = leaderboard['run'].apply(lambda x: f"{x} x 3 = {round(x*3, 2)}" if x > 0 else '')

    # Calculate the total distance
    leaderboard['total_distance'] = leaderboard['ride'] + leaderboard['run']*3

    # Add a ranking column
    leaderboard['Rank'] = leaderboard['total_distance'].rank(ascending=False).astype(int)

    # Show the leaderboard
    st.dataframe(leaderboard.sort_values(by='total_distance', ascending=False), width=1000, height=800)
