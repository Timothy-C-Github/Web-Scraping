# -*- coding: utf-8 -*-
"""
Created on Thu Feb 13 18:10:32 2025

@author: tacco
"""

import requests
from bs4 import BeautifulSoup
import csv
import os
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def get_profile_url(input_text):
    """
    Convert username to profile URL if needed, or validate existing URL.
    
    Args:
        input_text (str): Username or profile URL
        
    Returns:
        str: Full Steam profile URL or None if not found
    """
    if "steamcommunity.com" in input_text:
        return input_text
    else:
        logging.warning("Searching for profile is not implemented. Please provide a full Steam profile URL.")
        return None

def extract_basic_profile_info(soup):
    """
    Extract basic profile information from the BeautifulSoup object.
    
    Args:
        soup (BeautifulSoup): Parsed HTML content
        
    Returns:
        dict: Dictionary containing basic profile information
    """
    profile_data = {
        "name": None,
        "level": None,
        "location": None,
        "status": None,
        "avatar_url": None,
        "background_url": None,
        "number_of_badges": None,
        "total_games": None,
        "recent_activity": None,
        "profile_description": None,
    }

    # Extract profile name
    name_element = soup.find("span", class_="actual_persona_name")
    if name_element:
        profile_data["name"] = name_element.text.strip()

    # Extract profile level
    level_badge = soup.find("span", class_="friendPlayerLevelNum")
    if level_badge:
        try:
            profile_data["level"] = int(level_badge.text.strip())
        except ValueError:
            logging.warning("Failed to parse profile level.")

    # Extract country
    location_img = soup.find("img", class_="profile_flag")
    if location_img and location_img.next_sibling:
        profile_data["location"] = location_img.next_sibling.strip()

    # Extract online status
    status_div = soup.find("div", class_="profile_in_game_header")
    if status_div:
        profile_data["status"] = status_div.text.strip()

    # Extract avatar URL
    avatar_container = soup.find("div", class_="playerAvatarAutoSizeInner")
    if avatar_container:
        avatar_img = avatar_container.find("img")
        if avatar_img:
            profile_data["avatar_url"] = avatar_img.get("src")

    # Extract background URL
    bg_container = soup.find("div", class_="profile_animated_background")
    if bg_container:
        bg_video = bg_container.find("video")
        if bg_video:
            source = bg_video.find("source")
            if source:
                profile_data["background_url"] = source.get("src")
    
    # Extract total number of badges
    badge_container = soup.find("div", class_="profile_badges").find("span", class_="profile_count_link_total").text.strip()
    if badge_container:
        profile_data["number_of_badges"] = badge_container

    # Extract total number of games
    # First method: from individual games tab.
    games_tab = soup.find("div", class_="profile_item_links").find("a", href=lambda x: x and 'games/?tab=all' in x)
    if games_tab:
        tot_games = games_tab.find("span", class_="profile_count_link_total").text.strip()
        profile_data["total_games"] = tot_games
    # Second method: from badges
    badge_games = soup.find('div', class_='profile_badges').find("div", class_="profile_count_link_preview").find_all("div", class_="profile_badges_badge")
    for badge in badge_games:
        tooltip = badge.get('data-tooltip-html', '')
        if "games owned" in tooltip:
            games_badge = re.sub('\D', '', str(tooltip))
            profile_data["total_games"] = games_badge
            break  # Stop after finding the correct badge
    
    # Extract recent activity
    recent_activity = soup.find("div", class_="recentgame_quicklinks recentgame_recentplaytime")
    if recent_activity:
        profile_data["recent_activity"] = recent_activity.text.strip("\n")
    if profile_data["recent_activity"] == None:
        profile_data["recent_activity"] = "N/A"
        
    # Extract profile description
    profile_description = soup.find("div", class_="profile_summary")
    if profile_description:
        profile_data["profile_description"] = profile_description.text.strip()
    if profile_data["profile_description"] == None:
        profile_data["profile_description"] = "N/A"
    
    
    
    return profile_data

def extract_games_and_playtime(soup):
    """
    Extract games and total playtime information from the BeautifulSoup object.
    
    Args:
        soup (BeautifulSoup): Parsed HTML content
        
    Returns:
        tuple: (list of games, total playtime hours)
    """
    games = []
    total_playtime_hours_on_recent_games = 0

    games_list = soup.find_all("div", class_="recent_game")
    for game in games_list:
        game_name_div = game.find("div", class_="game_name")
        if not game_name_div:
            continue

        game_name = game_name_div.text.strip()
        hours_div = game.find("div", class_="game_info_details")
        hours_played = None

        if hours_div:
            try:
                hours = hours_div.text.split(" hrs")[0].strip()
                hours_played = float(hours)
                total_playtime_hours_on_recent_games += hours_played
            except (ValueError, IndexError):
                logging.warning(f"Failed to parse playtime for game: {game_name}")

        games.append({"name": game_name, "hours_played": hours_played})

    return games, total_playtime_hours_on_recent_games

def extract_friends(soup):
    """
    Extract friends information from the BeautifulSoup object.
    
    Args:
        soup (BeautifulSoup): Parsed HTML content
        
    Returns:
        tuple: (list of friends, total friends count)
    """
    friends_names = []
    friends_links = []
    friends_status = []
    friends_in_game = []
    total_friends = (soup.find("div", class_="profile_friend_links profile_count_link_preview_ctn responsive_groupfriends_element").find("span", class_="profile_count_link_total")).text.strip()

    friends_list = soup.find("div", class_="profile_topfriends profile_count_link_preview")
    friends_list = friends_list.select("div[class^='friendBlock persona']")
    for friend in friends_list:
        friend_content = friend.find("a")
        friends_links.append(friend_content["href"])
        friend_name = friend.find("div", class_="friendBlockContent").text.strip().split("\n")
        friends_names.append(friend_name[0])
        
        
        if "In-Game" in friend_name[2].strip():
            in_game = friend_name[2].strip()
            friends_status.append("In-Game")
            friends_in_game.append(re.split(r"In-Game", in_game, maxsplit=1)[1])
        elif "In-Game" not in friend_name[2].strip():
            friends_status.append(friend_name[2].strip())
            friends_in_game.append(None)
    
    return total_friends, friends_names, friends_links, friends_status, friends_in_game

def extract_years_of_service(soup):
    """
    Extract the account creation date from the Years of Service badge.
    
    Args:
        soup (BeautifulSoup): Parsed HTML content
        
    Returns:
        str: Account creation date or None if not found
    """
    years_badge = soup.find("div", attrs={"data-tooltip-html": lambda x: x and "Years of Service" in x})
    if years_badge:
        tooltip_html = years_badge["data-tooltip-html"]
        return tooltip_html.split("Member since ")[1].split(".")[0]
    return None

def scrape_steam_profile(input_text):
    """
    Scrapes a Steam profile and returns relevant information.
    
    Args:
        input_text (str): Username or URL of the Steam profile to scrape
        
    Returns:
        dict: Dictionary containing profile information
    """
    profile_url = get_profile_url(input_text)
    if not profile_url:
        return {"error": "Could not find profile"}

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }

    try:
        response = requests.get(profile_url, headers=headers)
        if response.status_code != 200:
            return {"error": f"Failed to access profile. Status code: {response.status_code}"}

        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract basic profile info
        profile_data = extract_basic_profile_info(soup)

        # Extract games and playtime
        games, total_playtime_hours_on_recent_games = extract_games_and_playtime(soup)
        profile_data["games"] = games
        if total_playtime_hours_on_recent_games == 0:
            total_playtime_hours_on_recent_games = "N/A"
        profile_data["total_playtime_hours_on_recent_games"] = total_playtime_hours_on_recent_games

        # Extract friends
        total_friends, friends_names, friends_links, friends_status, friends_in_game = extract_friends(soup)
        profile_data["total_friends"] = total_friends
        profile_data["friends_names"] = friends_names
        profile_data["friends_links"] = friends_links
        profile_data["friends_status"] = friends_status
        profile_data["friends_in_game"] = friends_in_game
        

        # Extract Years of Service badge
        profile_data["date_of_creation"] = extract_years_of_service(soup)

        return profile_data

    except Exception as e:
        logging.error(f"Error parsing profile data: {e}")
        return {"error": f"Error parsing profile data: {str(e)}"}

def save_to_csv(profile_data, filename="steam_profiles.csv"):
    """
    Save profile data to CSV file.
    
    Args:
        profile_data (dict): Profile information dictionary
        filename (str): Name of CSV file to save to
    """
    try:
        file_exists = os.path.exists(filename)

        with open(filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            if not file_exists:
                writer.writerow(['Name', 'Level', 'Location', 'Status', 'Total Games', 'Total Badges', 'Total Friends',
                               'Avatar URL', 'Background URL', 'Total Playtime Hours on Recent Games', 'Date of Creation', 'Recent Activity', 'Profile Description', 'Top Friends Names', 'Top Friends Profile Links', 'Top Friends Online Status', 'Top Friends Current Game Playing (if any)'])

            writer.writerow([
                profile_data.get('name'),
                profile_data.get('level'),
                profile_data.get('location'),
                profile_data.get('status'),
                profile_data.get('total_games'),
                profile_data.get('number_of_badges'),
                profile_data.get('total_friends'),
                profile_data.get('avatar_url'),
                profile_data.get('background_url'),
                profile_data.get('total_playtime_hours_on_recent_games'),
                profile_data.get('date_of_creation'),
                profile_data.get('recent_activity'),
                profile_data.get('profile_description'),
                profile_data.get('friends_names'),
                profile_data.get('friends_links'),
                profile_data.get('friends_status'),
                profile_data.get('friends_in_game'),
            ])
    except Exception as e:
        logging.error(f"Error saving to CSV: {e}")

if __name__ == "__main__":
    input_text = input("Enter Steam username or profile URL: ")
    profile_data = scrape_steam_profile(input_text)

    if profile_data and 'error' not in profile_data:
        print("\nProfile data retrieved successfully!")
        save_to_csv(profile_data)
        print(f"Data saved to steam_profiles.csv")

        print("\nProfile Summary:")
        for key, value in profile_data.items():
            if key not in ['games', 'friends']:
                print(f"{key}: {value}")
    else:
        print(f"Error: {profile_data.get('error', 'Unknown error occurred')}")
