import pandas as pd
import streamlit as st
import numpy as np
import os

# Initialize session state for selected parlays if it doesn't exist
if 'selected_parlays' not in st.session_state:
    st.session_state.selected_parlays = []

# Path to save the parlay bets CSV
parlay_bets_csv = 'data/parlay_bets.csv'

# Initialize or load existing parlays
if os.path.exists(parlay_bets_csv):
    parlays_df = pd.read_csv(parlay_bets_csv)
else:
    parlays_df = pd.DataFrame(columns=['Bet Info', 'Price'])


# Load data from CSV
df = pd.read_csv('data/final_odds_api_pull.csv') 

# Add alternate markets if they do not exist for every player
alternate_markets = {
    'player_rebounds_alternate': [4.5, 7.5, 10.5],
    'player_assists_alternate': [4.5, 7.5, 10.5],
    'player_points_alternate': [9.5, 19.5, 29.5],
}

for player in df['PLAYER_NAME'].unique():
    for game_date in df['GAME_DATE'].unique():
        for market, points_options in alternate_markets.items():
            for point in points_options:
                if not ((df['PLAYER_NAME'] == player) & (df['GAME_DATE'] == game_date) & (df['MARKET'] == market) & (df['POINT'] == point)).any():
                    # Add row with placeholder prices, adjust as necessary
                    df = pd.concat([df, pd.DataFrame.from_records([{
                        'PLAYER_NAME': player,
                        'GAME_DATE': game_date,
                        'MARKET': market,
                        'POINT': point,
                        'OVER_PRICE': np.nan,  # Placeholder
                        'UNDER_PRICE': np.nan,  # Placeholder
                        # Add other necessary columns with defaults
                    }])], ignore_index=True)

# UI components for date, team, and player selection
date = st.selectbox('Select Date:', df['GAME_DATE'].unique())
team = st.selectbox('Select Team:', ['All'] + list(df['TEAM_NAME'].unique()))
players = df[df['TEAM_NAME'] == team]['PLAYER_NAME'].unique() if team != 'All' else df['PLAYER_NAME'].unique()
player = st.selectbox('Select Player:', players)

# Display odds table for selected player
filtered_df = df[(df['GAME_DATE'] == date) & (df['PLAYER_NAME'] == player)]
st.table(filtered_df[['MARKET', 'POINT', 'OVER_PRICE', 'UNDER_PRICE']])

# Mechanism to ensure no duplicate stat types for a player
already_selected_stats = set()
for parlay in st.session_state.selected_parlays:
    bet_player, bet_market = parlay['Bet Info'].split(' - ')[0], parlay['Bet Info'].split(' - ')[1]
    if bet_player == player:
        stat_type = bet_market.split(' ')[0]  # Extracting base stat type (e.g., "player_points")
        already_selected_stats.add(stat_type)

# Filter out indices for stats that have already been selected
def is_stat_available(market):
    base_stat = market.split('_')[1]  # 'player_points' -> 'points'
    alternate_forms = [base_stat, f"{base_stat}_alternate"]
    return not any(alternate in already_selected_stats for alternate in alternate_forms)

available_indices = [i for i in filtered_df.index if is_stat_available(filtered_df.loc[i, 'MARKET'])]

# Select statistics for betting
selected_indices = st.multiselect("Select stats for betting:", available_indices, format_func=lambda x: f"{filtered_df.loc[x, 'MARKET']} at {filtered_df.loc[x, 'POINT']} points")

# Process selected bets
for i in selected_indices:
    row = df.loc[i]
    over_under = st.radio(f"{row['PLAYER_NAME']} - {row['MARKET']} at {row['POINT']} points: Choose Over or Under:", ('Over', 'Under'), key=f"over_under_{i}")
    
    default_price = row['OVER_PRICE'] if over_under == 'Over' else row['UNDER_PRICE']
    price = st.number_input(f"Enter price for {row['MARKET']} ({'Over' if over_under == 'Over' else 'Under'}):", value=float(default_price) if pd.notnull(default_price) else 0.01, key=f"price_input_{i}")
    
    bet_info = f"{row['PLAYER_NAME']} - {row['MARKET']} at {row['POINT']} points: {over_under} at price {price}"
    
    if st.button(f"Add '{bet_info}' to parlay", key=f"add_to_parlay_{i}"):
        st.session_state.selected_parlays.append({'Bet Info': bet_info, 'Price': price})
        st.success(f"Added to parlay: {bet_info}")
        already_selected_stats.add(row['MARKET'].split('_')[1])  # Update already selected stats

# Display current parlays from session state
if st.session_state.selected_parlays:
    st.write("Current Parlays:")
    current_parlays = pd.DataFrame(st.session_state.selected_parlays)
    st.table(current_parlays)

# Input for how much to bet, after parlays selection
bet_amount = st.number_input("Enter your total bet amount:", min_value=0.01, value=1.00, step=0.01, key='bet_amount')

# Calculate and display potential payout based on bet amount
if st.session_state.selected_parlays:
    total_odds = np.prod([float(parlay['Price']) for parlay in st.session_state.selected_parlays])
    potential_payout = total_odds * bet_amount
    st.markdown(f"**Potential payout from a ${bet_amount:,.2f} bet on current parlays: ${potential_payout:,.2f}**")  # Enhanced formatting


# Buttons for saving, deleting, and downloading parlays
if st.button('Save Current Parlays'):
    current_parlays = pd.DataFrame(st.session_state.selected_parlays)
    current_parlays.to_csv(parlay_bets_csv, index=False)
    st.success("Current parlays saved.")

if st.button('Delete All Parlays'):
    st.session_state.selected_parlays = []
    if os.path.exists(parlay_bets_csv):
        os.remove(parlay_bets_csv)
    st.success("All parlays deleted.")

# Calculate and display potential payout based on bet amount
if st.session_state.selected_parlays:
    total_odds = np.prod(current_parlays['Price'].astype(float))
    potential_payout = total_odds * bet_amount
    payout_text = f"Potential payout from a ${bet_amount:,.2f} bet on current parlays: ${potential_payout:,.2f}"
    st.markdown(f"**{payout_text}**")  # Use markdown for consistent font

if os.path.exists(parlay_bets_csv):
    with open(parlay_bets_csv, "rb") as file:
        st.download_button(label="Download Current Parlays as CSV", data=file, file_name="current_parlays.csv", mime="text/csv")
