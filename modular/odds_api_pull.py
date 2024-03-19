import requests
import pandas as pd
import datetime
import json
#********************odds api pull EXAMPLE********************************
# This is an example of how to use the odds API to fetch odds data for a specific market for a specific game to get columns as needed
# Define your API key and base URL
# api_key = ''
# Access your secret
# api_key = st.secrets["api_key"]
# base_url = 'https://api.the-odds-api.com/v4/sports/basketball_nba/events'

# # Set up parameters for the API call
# games_params = {
#     'apiKey': api_key,
#     'regions': 'us'
# }

# # Make the API call to fetch games
# games_response = requests.get(base_url, params=games_params)
# games_data = games_response.json()

# # Assuming you have games to work with, take the first game's ID
# if games_data:
#     game_id = games_data[0]['id']

#     # Now fetch odds for a specific market for this game
#     market = 'player_points'  # Example market
#     odds_url = f"{base_url}/{game_id}/odds"
#     odds_params = {
#         'apiKey': api_key,
#         'markets': market,
#         'regions': 'us'
#     }
#     odds_response = requests.get(odds_url, params=odds_params)
#     odds_data = odds_response.json()

#     # Print a formatted sample of the odds data
#     print(json.dumps(odds_data, indent=4))

#     # Now you can visually inspect the structure of the odds data
#     # and determine where the player names are located


#********************odds api pull EXAMPLE********************************


# Load the combined player data for today's date
df_combined = pd.read_csv('data/combined_data.csv')
df_combined['GAME_DATE'] = pd.to_datetime(df_combined['GAME_DATE']).dt.date
today = datetime.datetime.now().date()
df_filtered_combined = df_combined[df_combined['GAME_DATE'] == today]
players_today = df_filtered_combined['PLAYER_NAME'].unique()

#example for players_today
#players_today = ['Brandon Miller', 'Miles Bridges']

# Your API key
api_key = ''

# Define the base URL for The Odds API
base_url = 'https://api.the-odds-api.com/v4/sports'

# Example of the target markets
#nba_player_prop_markets = ['player_points']  # Simplified for demonstration
# Define the target markets
nba_player_prop_markets = [
    'player_points', 'player_rebounds', 'player_assists',
    'player_threes', 'player_blocks', 'player_steals',
    'player_blocks_steals', 'player_turnovers',
    'player_points_rebounds_assists', 'player_points_rebounds',
    'player_points_assists', 'player_rebounds_assists',
    'player_first_basket', 'player_double_double',
    'player_triple_double', 'player_points_alternate',
    'player_rebounds_alternate', 'player_assists_alternate',
    'player_blocks_alternate', 'player_steals_alternate',
    'player_threes_alternate', 'player_points_assists_alternate',
    'player_points_rebounds_alternate', 'player_rebounds_assists_alternate',
    'player_points_rebounds_assists_alternate'
]

# Initialize a list to store data for today's players across all games
betting_data_list = []

# Fetch the list of NBA games for today
games_url = f"{base_url}/basketball_nba/events"
games_params = {'apiKey': api_key, 'regions': 'us'}
games_response = requests.get(games_url, params=games_params)

if games_response.status_code == 200:
    games_data = games_response.json()

    # Loop through each game
    for game in games_data:
        game_id = game['id']
        commence_time = game['commence_time']
        
        # Loop through the target markets for each game
        for market in nba_player_prop_markets:
            odds_url = f"{base_url}/basketball_nba/events/{game_id}/odds"
            odds_params = {'apiKey': api_key, 'markets': market, 'regions': 'us'}
            odds_response = requests.get(odds_url, params=odds_params)

            if odds_response.status_code == 200:
                odds_data = odds_response.json()
                
                # Loop through each bookmaker's markets
                for bookmaker in odds_data.get('bookmakers', []):
                    for market_data in bookmaker.get('markets', []):
                        # Filter outcomes for players playing today
                        for outcome in market_data.get('outcomes', []):
                            if outcome.get('description') in players_today:
                                betting_data_list.append({
                                    'GAME_ID': game_id,
                                    'COMMENCE_TIME': pd.to_datetime(commence_time),
                                    'HOME_TEAM': game['home_team'],
                                    'AWAY_TEAM': game['away_team'],
                                    'PLAYER_NAME': outcome.get('description'),
                                    'MARKET': market_data.get('key'),
                                    'OVER_UNDER': outcome.get('name'),
                                    'PRICE': outcome.get('price'),
                                    'POINT': outcome.get('point'),
                                    'LAST_UPDATE': pd.to_datetime(market_data.get('last_update'))
                                })


# Convert the betting data list to a DataFrame
df_betting = pd.DataFrame(betting_data_list)

# Convert 'COMMENCE_TIME' and 'LAST_UPDATE' to datetime format explicitly
df_betting['COMMENCE_TIME'] = pd.to_datetime(df_betting['COMMENCE_TIME'], utc=True)
df_betting['LAST_UPDATE'] = pd.to_datetime(df_betting['LAST_UPDATE'], utc=True)

# Now attempt to remove timezone information
df_betting['COMMENCE_TIME'] = df_betting['COMMENCE_TIME'].apply(lambda x: x.replace(tzinfo=None))
df_betting['LAST_UPDATE'] = df_betting['LAST_UPDATE'].apply(lambda x: x.replace(tzinfo=None))

# Extract GAME_DATE from COMMENCE_TIME
df_betting['GAME_DATE'] = df_betting['COMMENCE_TIME'].dt.date

# Sort by 'Last Update' to ensure the most recent entries are first
df_betting.sort_values(by=['PLAYER_NAME', 'MARKET', 'OVER_UNDER', 'LAST_UPDATE'], ascending=[True, True, True, False], inplace=True)

# Drop duplicates to keep only the latest entry for each type of market per player
df_betting.drop_duplicates(subset=['PLAYER_NAME', 'MARKET', 'OVER_UNDER'], keep='first', inplace=True)


# Generate 'OVER_PRICE' and 'UNDER_PRICE' columns
df_betting['OVER_PRICE'] = df_betting.apply(lambda x: x['PRICE'] if x['OVER_UNDER'] == 'Over' else pd.NA, axis=1)
df_betting['UNDER_PRICE'] = df_betting.apply(lambda x: x['PRICE'] if x['OVER_UNDER'] == 'Under' else pd.NA, axis=1)

# Prepare separate DataFrames for Over and Under prices
df_over = df_betting[df_betting['OVER_UNDER'] == 'Over'][['PLAYER_NAME', 'GAME_DATE', 'MARKET', 'OVER_PRICE', 'POINT', 'HOME_TEAM', 'AWAY_TEAM']].copy()
df_under = df_betting[df_betting['OVER_UNDER'] == 'Under'][['PLAYER_NAME', 'GAME_DATE', 'MARKET', 'UNDER_PRICE', 'POINT', 'HOME_TEAM', 'AWAY_TEAM']].copy()


# Merge Over and Under DataFrames to have a single row per player prop
df_over_under = pd.merge(df_over, df_under, on=['PLAYER_NAME', 'GAME_DATE', 'MARKET', 'POINT', 'HOME_TEAM', 'AWAY_TEAM'], how='outer')


# Merge with player data to include 'TEAM_NAME'
df_final = pd.merge(df_over_under, df_filtered_combined[['PLAYER_NAME', 'TEAM_NAME']], on='PLAYER_NAME', how='left')

# Determine if the player is playing at home or away and who the opponent is
df_final['HOME_AWAY'] = df_final.apply(lambda x: 'Home' if x['TEAM_NAME'] == x['HOME_TEAM'] else 'Away', axis=1)
df_final['OPPONENT_NAME'] = df_final.apply(lambda x: x['AWAY_TEAM'] if x['HOME_AWAY'] == 'Home' else x['HOME_TEAM'], axis=1)

# Drop any unnecessary columns if needed and reset index
df_final = df_final.reset_index(drop=True)

# print(df_final.head())

# concat to the bottom of the csv file
with open('data/final_odds_api_pull.csv', 'a') as f:
    df_final.to_csv(f, header=f.tell()==0, index=False)

# df_final.to_csv('data/final_odds_api_pull.csv', index=False)
