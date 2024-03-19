import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from modular.player_game_logs import load_nba_player_game_logs, prepare_upcoming_games_data
from modular.metrics_functions import prepare_mean_std_data, prepare_league_std_data, prepare_performance_against_all_teams
from modular.betting_functions import calculate_probability, calculate_bet_outcome, generate_betting_options, evaluate_bets, evaluate_bets_n_games_debug
import os

#file paths
prev_data_file_path = os.path.join('data', 'player_game_logs_winr.csv')
upcoming_games_file_path = os.path.join('data', '23_24_season_games.csv')



# Add a new section in your sidebar for navigation
st.sidebar.header("Navigation")
page = st.sidebar.radio("Select a page:", ["Player Analysis", "Forecasting Player Statistics"])


#------------Loading data with caching---------------
st.sidebar.header("Refresh Data for Select Season Year with Players at the Minimum Average Minutes Played")
# Season Year Selection slider
season_years = ['2022-23', '2023-24', '2024-25']  # Update this list with available seasons
selected_season = st.sidebar.selectbox('Select Season Year', season_years)

# min avg selection
min_avg_minutes =st.sidebar.slider('Minimum Average Minutes Played', min_value=1, max_value=60, value=20, step=1)

# Option to reload data
if st.sidebar.button('Load/Refresh Data'):
    load_nba_player_game_logs([selected_season], min_avg_minutes=min_avg_minutes, save_path=prev_data_file_path)
    st.sidebar.success(f"Data for the {selected_season} season loaded successfully.")

# Loading data with caching
@st.cache(ttl=3600, max_entries=10, show_spinner=False)
def load_data():
    data = pd.read_csv('data/player_game_logs_winr.csv')
    data['GAME_DATE'] = pd.to_datetime(data['GAME_DATE'])
    data.sort_values(by='GAME_DATE', inplace=True)
    return data

#pull in upcoming games to concatenate to data and input averages onto it
upcoming_games = prepare_upcoming_games_data(upcoming_games_file_path, prev_data_file_path, expand_with_players=True)

# Load the existing games data
previous_games = load_data()

# Ensure GAME_DATE is in datetime format for comparison
upcoming_games['GAME_DATE'] = pd.to_datetime(upcoming_games['GAME_DATE'])

# Filter out upcoming games that have dates already in previous games
unique_upcoming_games = upcoming_games[~upcoming_games['GAME_DATE'].isin(previous_games['GAME_DATE'])]

# Concatenate the unique upcoming games to the previous games dataset
data = pd.concat([previous_games, unique_upcoming_games], ignore_index=True)

# Sort the concatenated data by GAME_DATE to maintain chronological order
data.sort_values(by='GAME_DATE', inplace=True)

# Reset the index of the concatenated DataFrame
data.reset_index(drop=True, inplace=True)
#------------Loading data with caching---------------

# Use if-else to control the page display based on the sidebar selection
if page == "Player Analysis":
    # Title of the app
    st.title("NBA Player Game Logs and Statistical Insights")

    # Sidebar for user inputs
    st.sidebar.header("User Input Features")

    #------------Date/Player data---------------


    # Unique Data
    unique_dates = data['GAME_DATE'].dt.strftime('%Y-%m-%d').unique()
    #players = data['PLAYER_NAME'].unique()
    games = data['MATCHUP'].unique()

    # App functions
    # --------Date Selection----------
    selected_date = st.sidebar.selectbox('Select a Date', unique_dates)
    # to provide data for the selected date
    current_data = data[data['GAME_DATE'] == pd.to_datetime(selected_date)]
    players = current_data['PLAYER_NAME'].unique()
    # --------Player Search Selection----------
    # Use a text input for search instead of a dropdown
    search_query = st.sidebar.text_input("Search Player Name")
    # Filter the list of players based on the search query
    filtered_players = [player for player in players if search_query.lower() in player.lower()]
    # If there are too many matches, you might want to limit the number displayed or adjust UI accordingly
    if len(filtered_players) > 1:
        st.sidebar.write("Please refine your search to see the results")
    # --------Player Dropdown Selection----------
    # Allow the user to select a player from the filtered list
    selected_player = st.sidebar.selectbox("Select a Player", filtered_players)

    # Datasets to use
    current_data = data[data['GAME_DATE'] == pd.to_datetime(selected_date)]
    player_data = data[data['PLAYER_NAME'] == selected_player]
    player_date_data = player_data[player_data['GAME_DATE'] == pd.to_datetime(selected_date)]
    current_stats_data = data[data['GAME_DATE'] <= selected_date]
    total_games_played = current_stats_data[current_stats_data['PLAYER_NAME'] == selected_player].shape[0]


    if not player_data.empty:
        game_location = 'Home' if player_data['HOME_AWAY'].iloc[0] == 'Home' else 'Away'
        game_opposing_team = player_data['OPPONENT_NAME'].iloc[0]
        st.write(f"Data for {selected_player} ({game_location} game) against {game_opposing_team} on {selected_date}:")
        #st.dataframe(player_data[['GAME_DATE', 'TEAM_NAME', 'HOME_AWAY', 'PLAYER_NAME', 'TEAM_WIN_RATE', 'OPPONENT_WIN_RATE', 'PTS', 'FG3M', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'MIN']])
    else:
        st.write(f"No data available for {selected_player} on {selected_date}.")


    # Filter data for the selected date
    current_stats_data = data[data['GAME_DATE'] <= selected_date]
    # Total games played by the player in the dataset
    total_games_played = current_stats_data[current_stats_data['PLAYER_NAME'] == selected_player].shape[0]
    # Display total games played
    print(f"Total games played by {selected_player} in the dataset: {total_games_played}")

    # Computing averages and league standard deviation
    # (Ensure functions like prepare_mean_std_data and prepare_league_std_data are correctly implemented)
    total_averages_data = prepare_mean_std_data(current_stats_data, n_games=total_games_played, game_location='All') #, current_date=current_date
    n_game_aggregated_data_all = prepare_mean_std_data(current_stats_data, n_games=10, game_location='All') #, current_date=current_date
    n_game_aggregated_data_home_or_away = prepare_mean_std_data(current_stats_data, n_games=10, game_location=game_location) #, current_date=current_date
    league_std_data = prepare_league_std_data(current_stats_data, n_games=10, game_location=game_location)

    # Performance against all teams
    performance_against_all_teams = prepare_performance_against_all_teams(current_stats_data)
    #filter against opposing_team
    performance_against_all_teams = performance_against_all_teams[performance_against_all_teams['OPPONENT_NAME'] == game_opposing_team]

    performance_against_all_teams = performance_against_all_teams.drop(columns=['OPPONENT_NAME'])
    #print(performance_against_all_teams.head())

    # Concatenate data for analysis
    combined_data = pd.concat([total_averages_data, n_game_aggregated_data_all, n_game_aggregated_data_home_or_away, league_std_data, performance_against_all_teams], ignore_index=True)

    # Filter for selected player and league standard
    combined_data_filtered = combined_data[combined_data['PLAYER_NAME'].isin([selected_player, 'League'])]
    #print(combined_data_filtered[['PLAYER_NAME', 'PTS', 'TYPE', 'HOME_AWAY', 'TEAM_NAME']])

    st.write(f"Total games played by {selected_player} in the dataset: {total_games_played}")
    st.dataframe(combined_data_filtered[['TEAM_NAME', 'HOME_AWAY', 'PLAYER_NAME', 'TYPE', 'TEAM_WIN_RATE', 'OPPONENT_WIN_RATE', 'PTS', 'FG3M', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'MIN']])

    # Move Statistic Selection to Main Body
    stats_options = ['PTS', 'REB', 'AST', 'STL', 'BLK']  # Extend with more stats as needed
    selected_stat = st.selectbox('Select a Statistic for Graph', stats_options)

    # Graph Visualization
    fig, ax = plt.subplots()
    player_season_data = data[data['PLAYER_NAME'] == selected_player]
    ax.plot(player_season_data['GAME_DATE'], player_season_data[selected_stat], marker='o', linestyle='-', label=selected_stat)
    ax.set_title(f"{selected_stat} Trend for {selected_player} During the Season")
    ax.set_xlabel('Game Date')
    ax.set_ylabel(selected_stat)
    plt.xticks(rotation=45)
    plt.legend()
    st.pyplot(fig)

    # Betting Analysis Section
    st.header("Betting Analysis")

    # Ensure that player_season_data is filtered for the selected player
    player_season_data = combined_data_filtered[combined_data_filtered['PLAYER_NAME'] == selected_player]


    #Testing the generate_betting_options filter-------------------------------------------------------------------------------------

    # Ensure GAME_DATE is in datetime format
    player_data['GAME_DATE'] = pd.to_datetime(player_data['GAME_DATE'])

    # Filter for selected date directly
    selected_date_dt = pd.to_datetime(selected_date)

    # Get today's date as a datetime object at midnight
    today = datetime.now()
    today = pd.to_datetime(today)
    yesterday = today - timedelta(days=1)
    yesterday = pd.to_datetime(yesterday)

    # Filter for selected date
    # If the selected date is today or in the future, filter data up to yesterday
    if selected_date_dt >= today:
        print("Selected date is today or in the future.")
        player_data_filt = player_data[player_data['GAME_DATE'] <= yesterday]
    # If the selected date is before today, filter for the selected day
    else:
        print("Selected date is before today.")
        player_data_filt = player_data[player_data['GAME_DATE'] <= selected_date_dt]

    # print("Filtered player data for selected date:", player_data_filt)

    #Testing the generate_betting_options filter-------------------------------------------------------------------------------------



    # Sidebar for interactive parameters
    n_games = st.sidebar.slider('Number of Games', min_value=1, max_value=60, value=10)
    league_std_rate = st.sidebar.slider('League Standard Deviation Above Rate', min_value=0.0, max_value=1.0, value=0.9, step=0.01)
    probability_high = st.sidebar.slider('High Probability Threshold', min_value=0.0, max_value=1.0, value=0.9, step=0.01)
    probability_low = st.sidebar.slider('Low Probability Threshold', min_value=0.0, max_value=1.0, value=0.1, step=0.01)

    with st.form("betting_form"):
        selected_stat_for_bet = st.selectbox('Select Statistic for Betting', stats_options)
        bet_stat_projection = st.number_input('Enter Bet Stat Projection', value=0.0, format="%.2f")
        bet_amount = st.number_input('Enter Bet Amount ($)', value=0.0, format="%.2f")
        odds = st.number_input('Enter Odds (American format, e.g., +150 or -150)', value=100)
        submit_bet = st.form_submit_button("Calculate")

    # When calling calculate_probability
    if submit_bet and not player_data.empty:
        probability, against_team_probability, number_of_games_against_team, player_std, std_dev_comparison, league_std, number_of_games_above_projection, number_of_games = calculate_probability(
            player_data, selected_stat_for_bet, bet_stat_projection, league_std_data, n_games, league_std_rate, game_opposing_team
        )

        
        # Call calculate_bet_outcome to get expected_profit and expected_loss
        expected_profit, expected_loss, probability_weighted_to_profit = calculate_bet_outcome(bet_amount, odds, probability)

        # Now you can correctly display the expected profit and loss
        st.write(f"Probability of achieving projection: {probability*100:.2f}% out of {number_of_games} games")
        if against_team_probability is not None:
            st.write(f"Probability against {game_opposing_team}: {against_team_probability*100:.2f}% with {number_of_games_against_team} games above projection")
        st.write(f"Player's Std Dev: {player_std:.2f}, Better than league's by 10%: {'Yes' if std_dev_comparison else 'No'}")

        # Your recommendation logic
        if probability >= probability_high and std_dev_comparison:
            recommendation = "Betting above the projection might be more favorable due to high probability and player's consistency."
        elif probability <= probability_low and std_dev_comparison:
            recommendation = "Betting below the projection might be more favorable due to low probability and player's consistency."
        else:
            recommendation = "Consider other options or exercise caution due to lower probability or player's inconsistency."
        st.write(recommendation)

        # Correctly output the expected profit and loss
        st.write(f"Expected Profit if Win: ${expected_profit:.2f}, Expected Loss if Lose: -${expected_loss:.2f}")
        st.write(f"Weighted Probability to Profit: {probability_weighted_to_profit:.2f}")

        st.write(f"Total games played by {selected_player} in the dataset: {total_games_played}")
        st.dataframe(combined_data_filtered[['TEAM_NAME', 'HOME_AWAY', 'PLAYER_NAME', 'TYPE', 'TEAM_WIN_RATE', 'OPPONENT_WIN_RATE', 'MIN', selected_stat_for_bet]])

        #print("Preview of player_data:")
        #print(player_data.head())
        #print("Preview of league_std_data:")
        #print(league_std_data.head())

        betting_options_df = generate_betting_options(
            player_data_filt, league_std_data, selected_player, game_opposing_team, 
            all_players=False, n_games=n_games, league_std_rate=league_std_rate, 
            probability_high=probability_high, probability_low=probability_low
        )

        #print("betting_options_df.head()=", betting_options_df.head())
        #filter for Stats
        print("selected stat=", selected_stat_for_bet)
        print("betting option columns =", betting_options_df.columns)
        #print("betting option head =", betting_options_df.head(1))
        #betting_options_df = betting_options_df[betting_options_df['Stat'] == selected_stat_for_bet]
        print("betting option columns =", betting_options_df.columns)
        #print("betting option head =", betting_options_df.head())
        st.dataframe(betting_options_df)

    # Ensure the correct datetime format and sort order
    print("Step 1: Data Preparation Completed")

    # Step 2: Generate Betting Options for all historical data
    betting_options_df = generate_betting_options(
        player_data_filt, league_std_data, selected_player, game_opposing_team, all_players=True, n_games=n_games, league_std_rate=league_std_rate, 
        probability_high=probability_high, probability_low=probability_low)
    print(f"Step 2: Generated {len(betting_options_df)} betting options for all historical data.")
    

    # Step 3: Filter Betting Options for the selected date
    selected_date_dt = pd.to_datetime(selected_date)
    if not betting_options_df.empty:
        betting_options_df_selected_date = betting_options_df[betting_options_df['GAME_DATE'] == selected_date_dt]
        print(f"Step 3: Filtered {len(betting_options_df_selected_date)} betting options for the selected date ({selected_date}):")
        #print(betting_options_df_selected_date[['PLAYER_NAME', 'Stat', 'Threshold', 'GAME_DATE']])
        st.dataframe(betting_options_df_selected_date)

        # Step 4: Evaluate Bets for an overall evaluation based on the last n games
        unique_dates = betting_options_df['GAME_DATE'].unique()
        if len(unique_dates) > n_games:
            unique_dates_n_games = unique_dates[-n_games:]
            betting_options_df_n_games = betting_options_df[betting_options_df['GAME_DATE'].isin(unique_dates_n_games)]
        else:
            betting_options_df_n_games = betting_options_df

        evaluated_bets_df = evaluate_bets(betting_options_df_n_games, player_data_filt)
        print("Step 4: Evaluated bets based on the last {n_games} games.")

        # Debugging prints for evaluated bets
        print(f"Evaluated Bets DataFrame has {len(evaluated_bets_df)} rows after evaluation.")

        #filter out NaN 
        evaluated_bets_df = evaluated_bets_df.dropna(subset=['Bet Outcome'])

        #get min and max
        min_date = evaluated_bets_df['GAME_DATE'].min()
        max_date = evaluated_bets_df['GAME_DATE'].max()

        # Display the last values of Running Correct and Running Incorrect
        if not evaluated_bets_df.empty:
            final_corrects = evaluated_bets_df.iloc[-1]['Running Correct']
            final_incorrects = evaluated_bets_df.iloc[-1]['Running Incorrect']
            overall_bets = final_corrects + final_incorrects
            print(f"Final Corrects: {final_corrects}, Final Incorrects: {final_incorrects}")
        else:
            print("No bets evaluated.")
        
        #Display Percentage of correct bets through Running Correct and Running Incorrect
        if final_corrects + final_incorrects > 0:
            correct_percentage = final_corrects / overall_bets
            st.write(f"Percentage of correct bets: {correct_percentage*100:.2f}% out of {overall_bets} chances over the last {n_games} games ({min_date} to {max_date})")
        else:
            st.write("No bets evaluated yet.")
    else:
        print("No betting options generated yet.")
        st.write("No betting options generated yet.")




#-------------------------------New Tab for All Around Dashboard for Betting--------------------------------
#elif page == "Overall Betting Details":
    #changes:
    #1. add in a team drop down
    #2. ensure these dropdowns go back to normal when nothings selected
    #3. add in parlay betting, so it should save each bet chosen unless user deletes the bets and will add the parlay automatically
    # New section for Betting Details
# ...

elif page == "Forecasting Player Statistics":
    st.header("Statistic Details")
    st.title("NBA Players Forecasted Statistics")

    # Sidebar selections
    unique_dates = data['GAME_DATE'].dt.strftime('%Y-%m-%d').unique()
    selected_date = st.sidebar.selectbox('Select a Date', unique_dates)
    #select date and filter for the players and teams
    data = data[data['GAME_DATE'] == pd.to_datetime(selected_date)]
    selected_players = st.sidebar.multiselect("Select Players", options=data['PLAYER_NAME'].unique())
    selected_teams = st.sidebar.multiselect("Select Teams", options=data['TEAM_NAME'].unique())  # Assuming this is used somewhere in your app
    game_location = st.sidebar.selectbox('Select Game Location', ['All', 'Home', 'Away'])

    # Parameters for betting options
    n_games = st.sidebar.slider('Number of Games', min_value=1, max_value=60, value=10)
    league_std_rate = st.sidebar.slider('League Standard Deviation Above Rate', min_value=0.0, max_value=1.0, value=0.9, step=0.01)
    probability_high = st.sidebar.slider('High Probability Threshold', min_value=0.0, max_value=1.0, value=0.9, step=0.01)
    probability_low = st.sidebar.slider('Low Probability Threshold', min_value=0.0, max_value=1.0, value=0.1, step=0.01)

    # Filter data for the selected date
    betting_today_data = data[data['GAME_DATE'] == pd.to_datetime(selected_date)]
    league_std_data = prepare_league_std_data(betting_today_data, n_games=n_games, game_location=game_location)

    if selected_players:
        evaluated_bets_list = []
        for player in selected_players:
            player_data = betting_today_data[betting_today_data['PLAYER_NAME'] == player]
            evaluated_bets_df = evaluate_bets_n_games_debug(player_data, player_data, n_games)  # Adjust this call as needed
            evaluated_bets_list.append(evaluated_bets_df)

        combined_evaluated_bets_df = pd.concat(evaluated_bets_list, ignore_index=True) if evaluated_bets_list else pd.DataFrame()
        
        if not combined_evaluated_bets_df.empty:
            st.dataframe(combined_evaluated_bets_df[['PLAYER_NAME', 'GAME_DATE', 'Stat', 'Threshold', 'Actual Value', 'Bet Correct']])
            total_bets = len(combined_evaluated_bets_df)
            correct_bets = combined_evaluated_bets_df['Bet Correct'].sum()
            correct_percentage = correct_bets / total_bets * 100 if total_bets > 0 else 0
            st.write(f"Total Bets: {total_bets}, Correct Bets: {correct_bets}, Correct Percentage: {correct_percentage:.2f}%")
        else:
            st.write("No betting options generated for the selected criteria.")

