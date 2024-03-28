import pandas as pd
from datetime import datetime, timedelta
from nba_api.stats.endpoints import commonallplayers, playergamelog, leaguedashplayerstats, leaguegamefinder
from nba_api.stats.static import teams
import time
import numpy as np
import os


def get_current_nba_season_year():
    current_date = datetime.now()
    if current_date.month > 9:  # NBA season starts in October
        return str(current_date.year) + "-" + str(current_date.year + 1)[2:]
    else:
        return str(current_date.year - 1) + "-" + str(current_date.year)[2:]

def calculate_cumulative_win_rates(season):
    try:
        # Adjust the season start date based on the typical NBA season start dates
        season_start_date = season.split('-')[0] + "-10-01"  # Assuming October 1st as a generic start date
        all_games = leaguegamefinder.LeagueGameFinder(season_nullable=season).get_data_frames()[0]
        all_games['GAME_DATE'] = pd.to_datetime(all_games['GAME_DATE'])
        all_games = all_games[all_games['GAME_DATE'] > pd.to_datetime(season_start_date)]
        all_games = all_games.sort_values('GAME_DATE')
        all_games['WIN'] = all_games['WL'].apply(lambda x: 1 if x == 'W' else 0)
        all_games['CUMULATIVE_WINS'] = all_games.groupby('TEAM_NAME')['WIN'].cumsum()
        all_games['CUMULATIVE_GAMES'] = all_games.groupby('TEAM_NAME').cumcount() + 1
        all_games['CUMULATIVE_WIN_RATE'] = all_games['CUMULATIVE_WINS'] / all_games['CUMULATIVE_GAMES']
        return all_games
    except Exception as e:
        print(f"Error calculating cumulative win rates: {e}")
        return pd.DataFrame()
    

def get_win_rate(row, team_type, all_games):
    game_date = row['GAME_DATE']
    team_name = row[team_type]
    team_games = all_games[(all_games['TEAM_NAME'] == team_name) & (all_games['GAME_DATE'] < game_date)]
    if not team_games.empty:
        return team_games.iloc[-1]['CUMULATIVE_WIN_RATE']
    else:
        return 0.0



def load_nba_player_game_logs(seasons, min_avg_minutes=30.0, save_path='data/player_game_logs.csv'):
    if not isinstance(seasons, list):
        seasons = [seasons]

    new_players_data = pd.DataFrame()

    for season in seasons:
        print(f"Processing season {season}...")
        try:
            all_players = commonallplayers.CommonAllPlayers(is_only_current_season=0).get_data_frames()[0]
            if all_players.empty:
                print(f"No players found for season {season}.")
                continue
            player_stats = leaguedashplayerstats.LeagueDashPlayerStats(season=season).get_data_frames()[0]
            if player_stats.empty:
                print(f"No player stats available for season {season}.")
                continue
        except Exception as e:
            print(f"Error fetching player stats for season {season}: {e}")
            continue

        player_stats['AVG_MIN'] = player_stats['MIN'] / player_stats['GP']
        eligible_players = player_stats[player_stats['AVG_MIN'] >= min_avg_minutes]
        if eligible_players.empty:
            print(f"No players meet the minimum average minutes threshold for season {season}.")
            continue

        teams_list = teams.get_teams()
        if not teams_list:
            print("Failed to load NBA teams list.")
            continue

        team_abbrev_to_full_name = {team['abbreviation']: team['full_name'] for team in teams_list}

        try:
            all_games = calculate_cumulative_win_rates(season)
            if all_games.empty:
                print("Skipping win rate calculation due to missing games data.")
                continue
        except Exception as e:
            print(f"Error calculating win rates for season {season}: {e}")
            continue

        for index, player in eligible_players.iterrows():
            try:
                player_id = player['PLAYER_ID']
                player_name = player['PLAYER_NAME']
                player_log = playergamelog.PlayerGameLog(player_id=player_id, season=season)
                player_data = player_log.get_data_frames()[0]
                #print(f"Processing player {player_name} in season {season}...")
                if player_data.empty:
                    print(f"No game logs found for player {player_name} in season {season}.")
                    continue

                player_data['PLAYER_NAME'] = player_name
                player_data['TEAM_ABBREVIATION'] = player_data['MATCHUP'].str[:3]
                player_data['OPPONENT_ABBREVIATION'] = player_data['MATCHUP'].apply(lambda x: x.split(' ')[2] if 'vs.' in x else x.split(' ')[-1])
                player_data['TEAM_NAME'] = player_data['TEAM_ABBREVIATION'].map(team_abbrev_to_full_name)
                player_data['OPPONENT_NAME'] = player_data['OPPONENT_ABBREVIATION'].map(team_abbrev_to_full_name)
                
                new_players_data = pd.concat([new_players_data, player_data], ignore_index=True)

            except Exception as e:
                print(f"Error processing player {player_name} in season {season}: {e}")
                continue
            time.sleep(0.6)
    #print(new_players_data.head())
    if not new_players_data.empty:
        new_players_data['GAME_DATE'] = pd.to_datetime(new_players_data['GAME_DATE'])
        new_players_data['TEAM_WIN_RATE'] = new_players_data.apply(lambda row: get_win_rate(row, 'TEAM_NAME', all_games), axis=1)
        new_players_data['OPPONENT_WIN_RATE'] = new_players_data.apply(lambda row: get_win_rate(row, 'OPPONENT_NAME', all_games), axis=1)
        new_players_data['HOME_AWAY'] = new_players_data['MATCHUP'].str.split(' ').str[1].apply(lambda x: 'Away' if '@' in x else 'Home')
        new_players_data.reset_index(drop=True, inplace=True)
        new_players_data.to_csv(save_path, index=False)
        print(f"Player game logs saved to {save_path}")
        return new_players_data
    else:
        print("No player game logs to save after processing all selected seasons.")
        return pd.DataFrame()  # Ensure to return an empty DataFrame if no data



# Example usage
#seasons = ['2022-23']  # You can adjust seasons as needed
#load_nba_player_game_logs(seasons, min_avg_minutes=30.0, save_path='data/player_game_logs_winr.csv')
        
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from nba_api.stats.static import teams

def prepare_upcoming_games_data(season_games_csv, player_game_logs_csv, expand_with_players=False):
    # Load season games data
    data = pd.read_csv(season_games_csv)
    
    # Process home and away data
    home_data = data[['DATE', 'Start (ET)', 'Home/Neutral']].copy()
    home_data['HOME_AWAY'] = 'Home'
    home_data['MATCHUP'] = home_data['Home/Neutral'] + ' vs. ' + data['Visitor/Neutral']
    home_data.rename(columns={'Home/Neutral': 'Team'}, inplace=True)
    home_data['WL_encoded'] = np.nan
    
    away_data = data[['DATE', 'Start (ET)', 'Visitor/Neutral']].copy()
    away_data['HOME_AWAY'] = 'Away'
    away_data['MATCHUP'] = away_data['Visitor/Neutral'] + ' @ ' + home_data['Team']  # Adjusted to use '@' for away games
    away_data.rename(columns={'Visitor/Neutral': 'Team'}, inplace=True)
    away_data['WL_encoded'] = np.nan
    
    final_data = pd.concat([home_data, away_data], ignore_index=True)
    final_data.sort_values(by=['DATE', 'Start (ET)', 'HOME_AWAY'], inplace=True)
    final_data.reset_index(drop=True, inplace=True)
    
    # Convert 'DATE' column to datetime format
    final_data['DATE'] = pd.to_datetime(final_data['DATE'], format='%a, %b %d, %Y')
    
    # Get unique team information from the NBA API
    teams_info = teams.get_teams()
    teams_df = pd.DataFrame(teams_info)
    teams_df.rename(columns={'id': 'TEAM_ID', 'full_name': 'TEAM_NAME', 'abbreviation': 'TEAM_ABBREVIATION'}, inplace=True)
    
    # Merge final_data with teams_df to include TEAM_ID and abbreviations
    final_data = pd.merge(final_data, teams_df[['TEAM_NAME', 'TEAM_ID', 'TEAM_ABBREVIATION']], left_on='Team', right_on='TEAM_NAME', how='left')
    
    # Ensure all team names in MATCHUP are abbreviations
    for index, row in final_data.iterrows():
        for _, team_row in teams_df.iterrows():
            final_data.at[index, 'MATCHUP'] = final_data.at[index, 'MATCHUP'].replace(team_row['TEAM_NAME'], team_row['TEAM_ABBREVIATION'])
    
    # Extract and filter for upcoming games
    today = pd.Timestamp.now().floor('D')  # Normalize to avoid time part
    week_out = today + timedelta(days=7)
    upcoming_games = final_data[(final_data['DATE'] >= today) & (final_data['DATE'] <= week_out)]
    upcoming_games.sort_values(by='DATE', inplace=True)
    upcoming_games.reset_index(drop=True, inplace=True)
    
    # Format the 'DATE' column to match the example output's 'GAME_DATE' format
    upcoming_games['GAME_DATE'] = upcoming_games['DATE'].dt.strftime('%Y-%m-%d')
    
    # Correct the column name for consistency
    upcoming_games.rename(columns={'HOME_AWAY': 'HOME_AWAY'}, inplace=True)
    
    # Drop unnecessary columns and adjust to match the target dataset structure
    upcoming_games = upcoming_games[['GAME_DATE', 'MATCHUP', 'HOME_AWAY', 'TEAM_ID', 'TEAM_NAME']]
    
    # Create OPPOSING_TEAM column
    upcoming_games['OPPONENT_NAME'] = np.nan  # Placeholder for opposing team names
    
    # Populate TEAM_NAME and OPPOSING_TEAM with correct names
    for index, row in upcoming_games.iterrows():
        if row['HOME_AWAY'] == 'Home':
            # If it's a home game, the home team is TEAM_NAME and the visitor team is OPPOSING_TEAM
            home_team_abbr = row['MATCHUP'].split(' vs. ')[0]
            away_team_abbr = row['MATCHUP'].split(' vs. ')[1]
        else:
            # If it's an away game, the visitor team is TEAM_NAME and the home team is OPPOSING_TEAM
            away_team_abbr = row['MATCHUP'].split(' @ ')[0]
            home_team_abbr = row['MATCHUP'].split(' @ ')[1]

        home_team_full_name = teams_df[teams_df['TEAM_ABBREVIATION'] == home_team_abbr]['TEAM_NAME'].values[0]
        away_team_full_name = teams_df[teams_df['TEAM_ABBREVIATION'] == away_team_abbr]['TEAM_NAME'].values[0]

        upcoming_games.at[index, 'TEAM_NAME'] = home_team_full_name if row['HOME_AWAY'] == 'Home' else away_team_full_name
        upcoming_games.at[index, 'OPPONENT_NAME'] = away_team_full_name if row['HOME_AWAY'] == 'Home' else home_team_full_name


    # Load player game logs to use for fetching rosters
    player_game_logs = pd.read_csv(player_game_logs_csv)
    print(player_game_logs.columns)
    print(upcoming_games.columns)
    
    if expand_with_players:
        expanded_games_with_players = pd.DataFrame()

        # Assuming player_game_logs_csv is correctly loaded into player_game_logs DataFrame
        player_game_logs = pd.read_csv(os.path.join('data', 'player_game_logs_winr.csv'))

        expanded_rows = []

        for _, game in upcoming_games.iterrows():
            team_name = game['TEAM_NAME']
            team_players = player_game_logs[player_game_logs['TEAM_NAME'] == team_name]

            for _, player in team_players.iterrows():
                expanded_row = game.copy().to_dict()
                expanded_row['Player_ID'] = player['Player_ID']
                expanded_row['PLAYER_NAME'] = player['PLAYER_NAME']
                expanded_rows.append(expanded_row)

        expanded_games_with_players = pd.DataFrame(expanded_rows)

        #drop duplicate players and game_dates
        expanded_games_with_players = expanded_games_with_players.drop_duplicates(subset=['GAME_DATE', 'PLAYER_NAME'], keep='first')

        # only include these columns: ['GAME_DATE', 'MATCHUP', 'HOME_AWAY', 'TEAM_NAME','OPPOSING_TEAM', 'Player_ID', 'PLAYER_NAME']
        expanded_games_with_players = expanded_games_with_players[['GAME_DATE', 'MATCHUP', 'HOME_AWAY', 'TEAM_NAME', 'OPPONENT_NAME', 'Player_ID', 'PLAYER_NAME']]
        
        # Return the expanded DataFrame
        return expanded_games_with_players


    return upcoming_games

# Example usage with file paths
#season_games_csv = 'data/23_24_season_games.csv'
#player_game_logs_csv = 'data/player_game_logs_winr.csv'
#upcoming_games_df = prepare_upcoming_games_data(season_games_csv, player_game_logs_csv, expand_with_players=True)
#print(upcoming_games_df.head())
#print(len(upcoming_games_df))


#Final data prepare
import pandas as pd



