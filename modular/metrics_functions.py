import pandas as pd
import numpy as np
import os

def calculate_running_stats(group, stats):
    """
    Calculate running mean and standard deviation for the specified statistics.
    """
    # Calculate mean and std for the last n games
    running_means = group[stats].mean()
    running_stds = group[stats].std(ddof=0)  # ddof=0 for population standard deviation
    return running_means, running_stds

def prepare_mean_std_data(df, n_games=10, current_date=None, current_season=None, game_location='All'):
    """
    Prepare aggregated data for players over the last n games up to the current date and within the current season,
    considering home/away context.
    """
    stats = ['PTS', 'FGM', 'FGA', 'FG3M', 'FG3A', 'FTM', 'FTA', 'AST', 'OREB', 'DREB', 'REB', 'TOV', 'STL', 'BLK', 'MIN', 'TEAM_WIN_RATE', 'OPPONENT_WIN_RATE']
    
    if current_date:
        df = df[df['GAME_DATE'] <= current_date]
    if current_season:
        df = df[df['SEASON'] == current_season]
    if game_location in ['Home', 'Away']:
        df = df[df['HOME_AWAY'] == game_location]

    grouped = df.groupby(['PLAYER_NAME', 'TEAM_NAME'])
    result_list = []

    for (player_name, team_name), group in grouped:
        group = group.sort_values(by='GAME_DATE', ascending=False).head(n_games)
        mean_values, std_values = calculate_running_stats(group, stats)
        
        mean_values['TYPE'] = 'mean_'+str(n_games)+'_games'
        std_values['TYPE'] = 'std_'+str(n_games)+'_games'
        mean_values['PLAYER_NAME'] = player_name
        mean_values['TEAM_NAME'] = team_name
        mean_values['HOME_AWAY'] = game_location
        
        std_values['PLAYER_NAME'] = player_name
        std_values['TEAM_NAME'] = team_name
        std_values['HOME_AWAY'] = game_location

        result_list.append(mean_values)
        result_list.append(std_values)

    result_df = pd.DataFrame(result_list).reset_index(drop=True)
    return result_df


# Example usage
# Load in data
data = pd.read_csv('data/player_game_logs_winr.csv')
# Filter for a specific player, e.g., Cade Cunningham
data = data[data['PLAYER_NAME'] == 'Cade Cunningham']
# Assuming 'data' is your DataFrame loaded from 'player_game_logs_winr.csv'
aggregated_data = prepare_mean_std_data(data, n_games=10, game_location='Home')
#print(aggregated_data.head())
#print(aggregated_data.columns)

def calculate_league_stats(df, stats, n_games=10, current_date=None, current_season=None, game_location='All'):
    """
    Calculate league-wide standard deviation for the specified statistics over the last n games,
    considering the filters applied for date, season, and location.
    """
    if current_date:
        df = df[df['GAME_DATE'] <= current_date]
    if current_season:
        df = df[df['SEASON'] == current_season]
    if game_location in ['Home', 'Away']:
        df = df[df['HOME_AWAY'] == game_location]

    std_values = df[stats].std(ddof=0)  # Using population standard deviation

    # Correctly creating a DataFrame with the intended structure
    std_values_df = pd.DataFrame([std_values.values], columns=stats)  # Wrap in a list to create a single row DataFrame
    std_values_df['TYPE'] = 'league_std_' + str(n_games) + '_games'
    std_values_df['PLAYER_NAME'] = 'League'
    std_values_df['TEAM_NAME'] = 'All'
    std_values_df['HOME_AWAY'] = game_location

    return std_values_df


def prepare_league_std_data(df, n_games=10, current_date=None, current_season=None, game_location='All'):
    """
    Prepare league-wide aggregated standard deviation data over the last n games up to the current date and within the current season,
    considering home/away context.
    """
    stats = ['PTS', 'FGM', 'FGA', 'FG3M', 'FG3A', 'FTM', 'FTA', 'AST', 'OREB', 'DREB', 'REB', 'TOV', 'STL', 'BLK', 'MIN', 'TEAM_WIN_RATE', 'OPPONENT_WIN_RATE']
    league_stats = calculate_league_stats(df, stats, n_games, current_date, current_season, game_location)
    
    result_df = pd.DataFrame(league_stats).reset_index(drop=True)
    return result_df

# Example usage
# Assuming 'data' is your DataFrame loaded from 'player_game_logs_winr.csv'
#league_data = prepare_league_std_data(data, n_games=10, game_location='Home')
#print(league_data.head())

#example concatenated data
# Concatenate league_data and aggregated_data
#combined_data = pd.concat([league_data, aggregated_data], ignore_index=True)

# Check the first few rows of the combined dataframe to ensure it looks correct
#print(combined_data.head())

# Optionally, check the structure and summary of the combined dataframe
#print(combined_data.info())


def prepare_performance_against_all_teams(df):
    """
    Prepare aggregated data for each player against each team they've played against in the dataset.
    
    Parameters:
    - df (DataFrame): The dataset containing player game logs.
    
    Returns:
    - DataFrame: The aggregated data with running averages for each player against each team.
    """
    stats = ['PTS', 'FGM', 'FGA', 'FG3M', 'FG3A', 'FTM', 'FTA', 'AST', 'OREB', 'DREB', 'REB', 'TOV', 'STL', 'BLK', 'MIN', 'TEAM_WIN_RATE', 'OPPONENT_WIN_RATE']
    unique_players = df['PLAYER_NAME'].unique()
    unique_teams = df['OPPONENT_NAME'].unique()
    
    result_list = []

    for player in unique_players:
        for team in unique_teams:
            player_games = df[(df['PLAYER_NAME'] == player) & (df['OPPONENT_NAME'] == team)]
            
            if not player_games.empty:
                mean_values, _ = calculate_running_stats(player_games, stats)
                mean_values['PLAYER_NAME'] = player
                mean_values['OPPONENT_NAME'] = team
                mean_values['TYPE'] = f'mean_vs_{team}'
                result_list.append(mean_values)
    
    result_df = pd.DataFrame(result_list).reset_index(drop=True)
    return result_df

#Example usage
#performance_against_all_teams = prepare_performance_against_all_teams(data)
#print(performance_against_all_teams)


