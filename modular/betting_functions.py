import pandas as pd
import numpy as np

#Things to consider:
#1. Calculate the probability of a player achieving a certain statistic in a game
#2. Calculate the probability of a player achieving a certain statistic against a specific team
#3. Calculate the probability of a player achieving a certain statistic in a game given the player's recent performance

#proposed changes:
#add in the opposing team as a parameter
#add in the number of games against the opposing team as a parameter
#add league std as a parameter
#add in level of competition as a warning if the opponent win rate is higher than the average win rate of this teams previous competition
#add in the number of games above projection and number of games as a parameter as a confidence rate

#***Take out the best options according to these parameters into a daily dashboard***
#record the results from this^ and see if the model is accurate


def calculate_probability(player_data, stat, projection, league_std_data, n_games=10, league_std_rate=0.9, opposing_team=None):
    # Filter out games without statistics (e.g., future games without stats yet)
    games_with_stats = player_data.dropna(subset=[stat])
    
    # Now, select the last 10 games from this filtered dataset
    last_10_games = games_with_stats.tail(n_games)
    #print(f"Last 10 games for {stat}:")
    #print(last_10_games[[stat]])
    
    # Ensure stat is used directly without alteration
    if stat not in games_with_stats.columns:
        raise KeyError(f"Statistic '{stat}' not found in player data columns.")

    # Diagnostic prints
    #print(f"Last 10 games for {stat}:")
    #print(last_10_games[[stat]])
    #print(f"Number of NaN values for {stat}: {last_10_games[stat].isna().sum()}")

    player_std = last_10_games[stat].fillna(0).std()
    #print(f"Player Std Dev for {stat}: {player_std}")

    # Initialize metrics here
    number_of_games_against_team = 0
    against_team_probability = 0
    number_of_games_above_projection_against_team = 0  # Initialize here


    if opposing_team:
        player_data.loc[:, 'OPPONENT_NAME'] = player_data['OPPONENT_NAME'].str.strip()
        
        #print(f"Opposing Team: {opposing_team}")
        #print("player_data['OPPONENT_NAME'] before=", player_data['OPPONENT_NAME'].unique())
        games_against_team = player_data[player_data['OPPONENT_NAME'] == opposing_team]
        #print("games_against_team after=", games_against_team['OPPONENT_NAME'].unique())
        #print(f"Games against {opposing_team}:")
        #print(games_against_team[[stat]])
        if not games_against_team.empty:
            games_above_projection_against_team = games_against_team[games_against_team[stat] >= projection]
            number_of_games_above_projection_against_team = len(games_above_projection_against_team)
            number_of_games_against_team = len(games_against_team)
            against_team_probability = len(games_above_projection_against_team) / number_of_games_against_team if number_of_games_against_team > 0 else 0
        #print(f"Games above projection against {opposing_team}: {number_of_games_above_projection_against_team} out of {number_of_games_against_team}")
    else:
        against_team_probability = None

    games_above_projection = last_10_games[last_10_games[stat] >= projection]
    number_of_games_above_projection = len(games_above_projection)
    number_of_games = len(last_10_games)
    probability = number_of_games_above_projection / number_of_games if number_of_games > 0 else 0

    #print(f"Games above projection: {number_of_games_above_projection} out of {number_of_games}")
    
    league_std = league_std_data[stat].iloc[0] if stat in league_std_data.columns else 0
    std_dev_comparison = player_std < league_std * league_std_rate

    #print(f"League Std Dev for {stat}: {league_std}")
    #print(f"Std Dev Comparison: {'Yes' if std_dev_comparison else 'No'}")

    return probability, against_team_probability, number_of_games_against_team, player_std, std_dev_comparison, league_std, number_of_games_above_projection, number_of_games



def calculate_bet_outcome(bet_amount, odds, probability):
    """
    Calculate expected profit or loss from a bet based on American odds.
    - For positive odds: the profit is bet_amount * (odds / 100) if win.
    - For negative odds: the profit is bet_amount / (abs(odds) / 100) if win.
    The loss is always the bet amount as you lose the stake if the bet does not win.
    """
    if odds > 0:
        # For positive odds, potential profit includes the bet amount
        potential_profit = bet_amount * (odds / 100)
    else:
        # For negative odds, potential profit is the bet amount since you need to bet more to win 100 units
        potential_profit = bet_amount / (abs(odds) / 100)

    # Expected profit considering the probability of winning
    expected_profit = potential_profit
    # No need to adjust for bet_amount for positive odds as it's considered in potential profit
    probability_weighted_to_profit = probability * potential_profit

    # Expected loss is straightforward; it's the bet amount since you lose the stake if the bet doesn't win
    expected_loss = bet_amount

    return expected_profit, expected_loss, probability_weighted_to_profit


def generate_betting_options(player_data, league_std_data, player_names, opposing_teams, all_players=True, n_games=10, league_std_rate=0.9, probability_high=0.9, probability_low=0.1):
    if not isinstance(player_names, list):
        player_names = [player_names]
    if opposing_teams is not None and not isinstance(opposing_teams, list):
        opposing_team = [opposing_teams]
    """
    Generate filtered betting options based on given criteria, now including game dates.
    """
    betting_categories = {
        'PTS': np.arange(9.5, 30.5, 1),
        'AST': np.arange(2.5, 12.5, 1),
        'REB': np.arange(2.5, 12.5, 1),
        'STL': np.arange(0.5, 5.5, 1),
        'BLK': np.arange(0.5, 5.5, 1),
        'FG3M': np.arange(0.5, 5.5, 1),
    }

    results = []
    
    if all_players:
        players = player_data['PLAYER_NAME'].unique()
    else:
        players = [player_name]

    for player in players:
        player_season_data = player_data[player_data['PLAYER_NAME'] == player].copy()
        game_dates = player_season_data['GAME_DATE'].unique()

        # Corrected handling of multiple opposing teams
        for game_date in game_dates:
            game_data = player_season_data[player_season_data['GAME_DATE'] < game_date]
            if not isinstance(opposing_team, list):
                opposing_teams_temp = [opposing_teams]  # Ensure opposing_teams is treated as a list
            else:
                opposing_teams_temp = opposing_teams

            for opposing_team in opposing_teams_temp:
                for stat, thresholds in betting_categories.items():
                    for threshold in thresholds:
                        # Calculate probability and other metrics for the specific game
                        probability, against_team_probability, number_of_games_against_team, player_std, std_dev_comparison, league_std, number_of_games_above_projection, number_of_games = calculate_probability(
                            game_data, stat, threshold, league_std_data, n_games, league_std_rate, opposing_teams)

                        if (probability > probability_high or probability < probability_low) and (player_std <= league_std * league_std_rate):
                            prob_comparison = 'Higher' if probability > probability_high else 'Lower' if probability < probability_low else 'Uncertain'
                            std_dev_comparison = 'Better than league std by at least 10%' if player_std <= league_std * league_std_rate else 'Not better than league std by at least 10%'
                            recommendation = 'Bet' if (prob_comparison == 'Higher' or prob_comparison == 'Lower') and player_std <= league_std * league_std_rate else 'Avoid'

                            result = {
                                'PLAYER_NAME': player,
                                'Stat': stat,
                                'Threshold': threshold,
                                'Probability': probability,
                                'Std Dev Comparison': std_dev_comparison,
                                'Probability comparison': prob_comparison,
                                'Recommendation based on Prob and std_dev': recommendation,
                                'Against Team Probability': against_team_probability if against_team_probability is not None else 'N/A',
                                'Games Against Team': number_of_games_against_team if number_of_games_against_team > 0 else 'N/A',
                                'GAME_DATE': game_date  # Include the game date in the results
                            }
                            results.append(result)

    results = [result for result in results if result['Recommendation based on Prob and std_dev'] == 'Bet']
                
    return pd.DataFrame(results)



def evaluate_bets(generated_bets, actual_performance):
    # Reset index to ensure it's sequential starting from 0
    generated_bets.reset_index(drop=True, inplace=True)

    # Iterate through generated bets using .iterrows() for safer access
    for index, row in generated_bets.iterrows():
        stat_column = row['Stat']
        actual_stat_row = actual_performance[
            (actual_performance['PLAYER_NAME'] == row['PLAYER_NAME']) & 
            (actual_performance['GAME_DATE'] == row['GAME_DATE'])
        ]
        
        if not actual_stat_row.empty:
            actual_value = actual_stat_row.iloc[0][stat_column]
            generated_bets.at[index, 'Actual Value'] = actual_value  # Assign actual value to the DataFrame
            
            if pd.notnull(actual_value):
                bet_correct = ((row['Probability comparison'] == 'Higher' and actual_value > row['Threshold']) or
                               (row['Probability comparison'] == 'Lower' and actual_value < row['Threshold']))
                generated_bets.at[index, 'Bet Outcome'] = bet_correct
            else:
                generated_bets.at[index, 'Bet Outcome'] = np.nan  # Mark as NaN if actual value is NaN
        else:
            # Mark as NaN if there's no matching performance data
            generated_bets.at[index, 'Actual Value'] = np.nan
            generated_bets.at[index, 'Bet Outcome'] = np.nan

    # Initialize running totals outside the loop to avoid resetting them on each iteration
    running_correct = 0
    running_incorrect = 0

    # After determining bet outcomes, calculate running totals
    for index, row in generated_bets.iterrows():
        if pd.notnull(row['Bet Outcome']):
            running_correct += int(row['Bet Outcome'] == True)
            running_incorrect += int(row['Bet Outcome'] == False)

            generated_bets.at[index, 'Running Correct'] = running_correct
            generated_bets.at[index, 'Running Incorrect'] = running_incorrect
        else:
            generated_bets.at[index, 'Running Correct'] = running_correct
            generated_bets.at[index, 'Running Incorrect'] = running_incorrect

    return generated_bets

    
def evaluate_bets_n_games_debug(generated_bets, actual_performance, n_games=10):
    # Ensure the datetime format is correct
    actual_performance['GAME_DATE'] = pd.to_datetime(actual_performance['GAME_DATE'])
    actual_performance.sort_values(by='GAME_DATE', inplace=True)
    
    evaluated_bets_list = []  # To store evaluated bets for debugging

    for player in generated_bets['PLAYER_NAME'].unique():
        print(f"\nEvaluating bets for: {player}")  # Debug: Confirm the player
        
        player_bets = generated_bets[generated_bets['PLAYER_NAME'] == player]
        player_performance = actual_performance[actual_performance['PLAYER_NAME'] == player]
        
        player_performance.sort_values(by='GAME_DATE', inplace=True)
        if len(player_performance) < n_games:
            print(f"Warning: {player} has only {len(player_performance)} games available, less than {n_games} games specified.")
        
        min_date_for_n_games = player_performance['GAME_DATE'].unique()[-n_games]
        print(f"Minimum date for the last {n_games} games: {min_date_for_n_games}")  # Debug: Check min date

        # Filter for bets and performances within the last n games
        player_bets_filtered = player_bets[player_bets['GAME_DATE'] >= min_date_for_n_games]
        player_performance_filtered = player_performance[player_performance['GAME_DATE'] >= min_date_for_n_games]

        correct_bets = 0
        incorrect_bets = 0

        for index, bet in player_bets_filtered.iterrows():
            game_date = bet['GAME_DATE']
            actual = player_performance_filtered[player_performance_filtered['GAME_DATE'] == game_date]

            if not actual.empty:
                actual_value = actual.iloc[0][bet['Stat']]
                bet_correct = ((bet['Probability comparison'] == 'Higher' and actual_value > bet['Threshold']) or
                               (bet['Probability comparison'] == 'Lower' and actual_value < bet['Threshold']))
                
                if bet_correct:
                    correct_bets += 1
                else:
                    incorrect_bets += 1
                
                evaluated_bets_list.append({**bet, 'Actual Value': actual_value, 'Bet Correct': bet_correct})
            else:
                print(f"No actual performance data for {player} on {game_date}")

        print(f"{player} - Correct Bets: {correct_bets}, Incorrect Bets: {incorrect_bets}")  # Debug: Check bet outcomes

    # Compile the debug results into a DataFrame
    evaluated_bets_df_debug = pd.DataFrame(evaluated_bets_list)
    
    if not evaluated_bets_df_debug.empty:
        final_corrects = sum(evaluated_bets_df_debug['Bet Correct'])
        overall_bets = len(evaluated_bets_df_debug)
        correct_percentage = final_corrects / overall_bets * 100
        print(f"\nFinal Correct Percentage: {correct_percentage}% ({final_corrects}/{overall_bets})")
    else:
        print("No bets evaluated. Check if the date range or player selection might be too restrictive.")

    return evaluated_bets_df_debug








#PARLAYS*********************************************************
def calculate_parlay_odds(bets):
    """
    Calculate the total odds for a parlay bet from a list of individual bets.
    Each bet in the list is a dictionary containing at least the 'odds' and 'probability' keys.
    
    Args:
    - bets (list of dicts): Each dict contains 'odds' (int or float) and 'probability' (float).

    Returns:
    - float: The total odds for the parlay bet.
    - float: The combined probability of the parlay bet winning.
    """
    total_odds = 1
    combined_probability = 1
    
    for bet in bets:
        # Convert American odds to decimal odds
        if bet['odds'] > 0:
            decimal_odds = 1 + bet['odds'] / 100
        else:
            decimal_odds = 1 - 100 / bet['odds']
        
        total_odds *= decimal_odds
        combined_probability *= bet['probability']  # Assumes independent events
    
    # Convert back to American odds if needed
    if total_odds >= 2:
        american_odds = (total_odds - 1) * 100
    else:
        american_odds = -100 / (total_odds - 1)

    return american_odds, combined_probability

#Example usage
# bets = [
#     {'odds': +150, 'probability': 0.4},
#     {'odds': -120, 'probability': 0.6},
#     {'odds': +200, 'probability': 0.3}
# ]

# parlay_odds, parlay_probability = calculate_parlay_odds(bets)
# print(f"Parlay Odds: {parlay_odds}, Parlay Probability: {parlay_probability}")




