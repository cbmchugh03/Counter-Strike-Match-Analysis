#pip3 install html5lib
from playwright.sync_api import sync_playwright, Playwright
import pandas as pd
from io import StringIO
import time
import numpy as np

# This code must be run on the terminal. To run, navigate to the Windows terminal, navigate to the file path that the scraper is saved in,
# type python hltv_scrapper.py. The code may run into errors, due to the fact that the pages do not load every single time. If this error is 
# encountered, just re-run the file until it does not run into an error/


# Creating functions to count round streak and round wins
def count_round_streaks(img_elements):
    if not img_elements:
        return 0
    
    round_outcomes = []
    for img in img_elements:
        src = img.get_attribute('src')
        if '_win' in src or 'bomb_defused' in src or 'bomb_exploded' in src or 'stopwatch' in src:
            round_outcomes.append('W')
        else: 
            round_outcomes.append('L')
    
    streak_count = 0
    current_streak = 0
    
    for outcome in round_outcomes:
        if outcome == 'W':
            current_streak += 1
        else:
            if current_streak >= 3:
                streak_count += 1
            current_streak = 0
    
    if current_streak >= 3:
        streak_count += 1
    
    return streak_count

def count_ct_t_rounds(img_elements):
    if not img_elements:
        return 0, 0
    
    ct_wins = 0
    t_wins = 0
    
    for img in img_elements:
        src = img.get_attribute('src')
        if 'ct_win' in src or 'bomb_defused' in src or 'stopwatch' in src:
            ct_wins += 1
        elif 't_win' in src or 'bomb_exploded' in src:
            t_wins += 1
    
    return ct_wins, t_wins

# Setting save directory and starting playwright - change to desired path
save_dir = r'C:/Users/cbmch/OneDrive/Desktop/Personal project/HLTV Data Dump/'

# Set link equal to a match results page
link = "https://www.hltv.org/results?event=8246"

pw = sync_playwright().start()

chrome = pw.chromium.launch(headless=False,
                            args = ['--disable-blink-features=AutomationControlled'])

page = chrome.new_page()

page.goto(link)

time.sleep(2)

page.set_extra_http_headers({
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'
})

all_matches_data = []

for match_index in range(7):
    match_data = []
    matchup_links = page.locator("div.result-con a.a-reset").all()
    matchup_links[match_index].click()
    time.sleep(2)
    stats_buttons = page.locator("a.results-stats").all()
    for i in range(len(stats_buttons)):      
        stats_buttons = page.locator("a.results-stats").all()
        stats_buttons[i].click()
        time.sleep(2)
        
        html_page = page.content()
        all_tables = pd.read_html(StringIO(html_page))
        
        # Get metadata
        match_info = page.locator("css=.match-info-box").nth(0).inner_text()
        row1 = page.locator("css=.match-info-row").nth(1).inner_text()
        row2 = page.locator("css=.match-info-row").nth(2).inner_text()
        row3 = page.locator("css=.match-info-row").nth(3).inner_text()
        
        # Minimal Processing - Getting team stats
        team1_stats = all_tables[0].copy()
        team1_stats['Map'] = f'Map {i+1}'
        team1_stats['Team'] = 'Team 1'
        team1_stats['Match_Info'] = match_info
        team1_stats['rating'] = row1
        team1_stats['firstkill'] = row2
        team1_stats['clutches'] = row3
        team1_stats['Match_ID'] = match_index  

        team2_stats = all_tables[3].copy()
        team2_stats['Map'] = f'Map {i+1}'
        team2_stats['Team'] = 'Team 2'
        team2_stats['Match_Info'] = match_info
        team2_stats['rating'] = row1
        team2_stats['firstkill'] = row2
        team2_stats['clutches'] = row3
        team2_stats['Match_ID'] = match_index  

        team1_imgs = []
        team2_imgs = []
        team1_streaks = 0
        team2_streaks = 0 
        team1_ct = 0
        team1_t = 0
        team2_ct = 0
        team2_t = 0
        #Counting Rounds streaks
        try:
            time.sleep(2)
            round_boxes = page.locator("div.standard-box.round-history-con").count()
            if round_boxes > 0:
                reg_history = page.locator("div.standard-box.round-history-con").first
                team1_imgs = reg_history.locator("div.round-history-team-row").first.locator("img").all()
                team2_imgs = reg_history.locator("div.round-history-team-row").nth(1).locator("img").all()
            ot_boxes = page.locator("div.standard-box.round-history-con.round-history-overtime").count()
            if ot_boxes > 0:
                ot_history = page.locator("div.standard-box.round-history-con.round-history-overtime").first
                team1_imgs = team1_imgs + ot_history.locator("div.round-history-team-row").first.locator("img").all()
                team2_imgs = team2_imgs + ot_history.locator("div.round-history-team-row").nth(1).locator("img").all()
        
            team1_streaks = count_round_streaks(team1_imgs)
            team2_streaks = count_round_streaks(team2_imgs)

            team1_ct, team1_t = count_ct_t_rounds(team1_imgs)
            team2_ct, team2_t = count_ct_t_rounds(team2_imgs)
        except:
            pass

        team1_stats['Rounds_Streak_Map'] = team1_streaks
        team2_stats['Rounds_Streak_Map'] = team2_streaks

        team1_stats['T rounds won'] = team1_t
        team1_stats['CT rounds won'] = team1_ct
        team2_stats['T rounds won'] = team2_t
        team2_stats['CT rounds won'] = team2_ct

  
        match_data.append(team1_stats)
        match_data.append(team2_stats)
        page.go_back()
        time.sleep(5)
    
    match_df = pd.concat(match_data, ignore_index=True)
    all_matches_data.append(match_df)
    
    page.go_back()
    time.sleep(2)

chrome.close()
page.close()
pw.stop()    

# Data cleaning
final_df = pd.concat(all_matches_data, ignore_index=True)

# Extract match info components
final_df['Map_Name'] = final_df['Match_Info'].str.split('\nMap\n').str[1].str.split('\n').str[0]
final_df['Team1_Name'] = final_df['Match_Info'].str.split('\n').str[-4]
final_df['Team1_Score'] = final_df['Match_Info'].str.split('\n').str[-3]
final_df['Team2_Name'] = final_df['Match_Info'].str.split('\n').str[-2]
final_df['Team2_Score'] = final_df['Match_Info'].str.split('\n').str[-1]

# Extract team ratings
final_df[['team1_rating', 'team2_rating']] = final_df['rating'].str.extract(r'(\d\.\d+)\s*:\s*(\d\.\d+)')

# Extract first kills
final_df[['team1_firstkill', 'team2_firstkill']] = final_df['firstkill'].str.extract(r'(\d+)\s*:\s*(\d+)')
final_df['team1_firstkill'] = final_df['team1_firstkill'].astype(float)
final_df['team2_firstkill'] = final_df['team2_firstkill'].astype(float)

# Extract clutches
final_df[['team1_clutches', 'team2_clutches']] = final_df['clutches'].str.extract(r'(\d+)\s*:\s*(\d+)')
final_df['team1_clutches'] = final_df['team1_clutches'].astype(float)
final_df['team2_clutches'] = final_df['team2_clutches'].astype(float)

# Clean K column
final_df['Kill'] = final_df['K (hs)'].astype(str).str.extract(r'^(\d+)')[0].astype(float)

# Extract traded deaths
final_df['trade'] = final_df['D (t)'].str.extract(r'\((\d+)\)')[0].astype(float)

# Drop unnecessary columns
columns_to_keep = ['Op.K-D', 'MKs', '1vsX', 'ADR', 'Swing', 'Rating3.0', 'Map',
                   'Team','Map_Name','Team1_Name','Team1_Score','Team2_Name','Team2_Score',
                   'team1_rating','team2_rating','team1_firstkill', 'team2_firstkill',
                   'team1_clutches','team2_clutches','Kill','trade','Win','Rounds_Streak_Map',
                   'T rounds won','CT rounds won', 'Match_ID']  # ADD Match_ID HERE
final_df = final_df[[col for col in columns_to_keep if col in final_df.columns]]


# CSV Creating
final_df['Team1_Score'] = final_df['Team1_Score'].astype(int)
final_df['Team2_Score'] = final_df['Team2_Score'].astype(int)

final_df['Map_Winner'] = final_df.apply(
    lambda row: 'Team1' if row['Team1_Score'] > row['Team2_Score'] else 'Team2',
    axis=1
)

team1_df = final_df[final_df['Team'] == 'Team 1'].copy()
team2_df = final_df[final_df['Team'] == 'Team 2'].copy()

team1_df['team1_rating'] = pd.to_numeric(team1_df['team1_rating'], errors='coerce')
team2_df['team2_rating'] = pd.to_numeric(team2_df['team2_rating'], errors='coerce')

# Create map-level data (one row per map) for map stats
team1_map_data = team1_df.drop_duplicates(subset=['Match_ID', 'Team1_Name', 'Team2_Name', 'Map_Name'])
team2_map_data = team2_df.drop_duplicates(subset=['Match_ID', 'Team2_Name', 'Team1_Name', 'Map_Name'])

# Get map-level stats
team1_perspective = team1_map_data.groupby(['Match_ID', 'Team1_Name', 'Team2_Name']).agg({
    'Map': 'count',
    'Map_Winner': lambda x: (x == 'Team1').sum(),
    'Team1_Score': 'sum',
    'team1_rating': 'mean',
    'team1_clutches': 'sum',
    'team1_firstkill':'sum',
    'Rounds_Streak_Map': 'sum',
    'CT rounds won': 'sum',
    'T rounds won': 'sum'
}).reset_index()

# Get kill stats
team1_kill_stats = team1_df.groupby(['Match_ID', 'Team1_Name', 'Team2_Name']).agg({
    'Kill': ['max', 'min'],
    'MKs': 'sum',
    'ADR': ['max', 'min', 'mean'],
    'trade': 'sum'
}).reset_index()
team1_kill_stats.columns = ['Match_ID', 'Team1_Name', 'Team2_Name', 'Max_Kills', 'Min_Kills','Total MK','Max ADR', 'Min ADR', 'Avg ADR','Num Trades']

# Merge with Match_ID
team1_perspective = team1_perspective.merge(team1_kill_stats, on=['Match_ID', 'Team1_Name', 'Team2_Name'])

# Rename columns
team1_perspective = team1_perspective.rename(columns={
    'Team1_Name': 'Team',
    'Team2_Name': 'Opponent',
    'Map': 'Maps Played',
    'Map_Winner': 'Maps won',
    'Team1_Score': 'Total rounds won',
    'team1_rating': 'Average player rating',
    'Max_Kills': 'Max Kill Count',
    'Min_Kills': 'Min Kill Count',
    'Total MK': 'Total MK',
    'Max ADR': 'Max ADR',
    'Min ADR': 'Min ADR',
    'Avg ADR': 'Avg ADR',
    'team1_clutches': '1vX Num',
    'Num Trades':'Num Trades',
    'team1_firstkill':'Number of first kills',
    'Rounds_Streak_Map': 'Rounds Streak',
    'CT rounds won': 'CT rounds won',
    'T rounds won': 'T rounds won'
})

# Add kill difference
team1_perspective['Kill Count difference'] = team1_perspective['Max Kill Count'] - team1_perspective['Min Kill Count']
team1_perspective['ADR Difference'] = team1_perspective['Max ADR'] - team1_perspective['Min ADR']

# Do the same thing for team 2
team2_perspective = team2_map_data.groupby(['Match_ID', 'Team2_Name', 'Team1_Name']).agg({
    'Map': 'count',
    'Map_Winner': lambda x: (x == 'Team2').sum(),
    'Team2_Score': 'sum',
    'team2_rating': 'mean',
    'team2_clutches': 'sum',
    'team2_firstkill':'sum',
    'Rounds_Streak_Map': 'sum',
    'CT rounds won': 'sum',
    'T rounds won': 'sum'
}).reset_index()

team2_kill_stats = team2_df.groupby(['Match_ID', 'Team2_Name', 'Team1_Name']).agg({
    'Kill': ['max', 'min'],
    'MKs': 'sum',
    'ADR': ['max', 'min', 'mean'],
    'trade': 'sum'
}).reset_index()
team2_kill_stats.columns = ['Match_ID', 'Team2_Name', 'Team1_Name', 'Max_Kills', 'Min_Kills','Total MK','Max ADR', 'Min ADR', 'Avg ADR','Num Trades']

team2_perspective = team2_perspective.merge(team2_kill_stats, on=['Match_ID', 'Team2_Name', 'Team1_Name'])

team2_perspective = team2_perspective.rename(columns={
    'Team2_Name': 'Team',
    'Team1_Name': 'Opponent',
    'Map': 'Maps Played',
    'Map_Winner': 'Maps won',
    'Team2_Score': 'Total rounds won',
    'team2_rating': 'Average player rating',
    'Max_Kills': 'Max Kill Count',
    'Min_Kills': 'Min Kill Count',
    'Total MK': 'Total MK',
    'Max ADR': 'Max ADR',
    'Min ADR': 'Min ADR',
    'Avg ADR': 'Avg ADR',
    'team2_clutches': '1vX Num',
    'Num Trades':'Num Trades',
    'team2_firstkill':'Number of first kills',
    'Rounds_Streak_Map': 'Rounds Streak',
    'CT rounds won': 'CT rounds won',
    'T rounds won': 'T rounds won'
})

team2_perspective['Kill Count difference'] = team2_perspective['Max Kill Count'] - team2_perspective['Min Kill Count']
team2_perspective['ADR Difference'] = team2_perspective['Max ADR'] - team2_perspective['Min ADR']

# Sort by Match_ID to ensure matching pairs line up
team1_perspective = team1_perspective.sort_values(['Match_ID']).reset_index(drop=True)
team2_perspective = team2_perspective.sort_values(['Match_ID']).reset_index(drop=True)

# Create a unique map list per match
maps_per_match = team1_map_data.groupby(['Match_ID', 'Team1_Name', 'Team2_Name'])['Map_Name'].apply(list).reset_index()

# Create Map 1, Map 2, Map 3 columns
maps_per_match['Map 1'] = maps_per_match['Map_Name'].apply(lambda x: x[0] if len(x) > 0 else 'NA')
maps_per_match['Map 2'] = maps_per_match['Map_Name'].apply(lambda x: x[1] if len(x) > 1 else 'NA')
maps_per_match['Map 3'] = maps_per_match['Map_Name'].apply(lambda x: x[2] if len(x) > 2 else 'NA')
maps_per_match['Map 4'] = maps_per_match['Map_Name'].apply(lambda x: x[3] if len(x) > 3 else 'NA')
maps_per_match['Map 5'] = maps_per_match['Map_Name'].apply(lambda x: x[4] if len(x) > 4 else 'NA')

# Drop the list column
maps_per_match = maps_per_match.drop('Map_Name', axis=1)

# Rename for merging
maps_per_match_team1 = maps_per_match.rename(columns={'Team1_Name': 'Team', 'Team2_Name': 'Opponent'})
maps_per_match_team2 = maps_per_match.rename(columns={'Team2_Name': 'Team', 'Team1_Name': 'Opponent'})

# Merge into perspectives using Match_ID
team1_perspective = team1_perspective.merge(maps_per_match_team1, on=['Match_ID', 'Team', 'Opponent'], how='left')
team2_perspective = team2_perspective.merge(maps_per_match_team2, on=['Match_ID', 'Team', 'Opponent'], how='left')

# Interleave them
team_stats = pd.DataFrame()
for i in range(len(team1_perspective)):
    team_stats = pd.concat([team_stats, team1_perspective.iloc[[i]], team2_perspective.iloc[[i]]], ignore_index=True)

# Indexing for column
team_stats = team_stats.reset_index(drop=True)

team_stats['Round Differential'] = team_stats.apply(
    lambda row: row['Total rounds won'] - team_stats.loc[row.name + 1 if row.name % 2 == 0 else row.name - 1, 'Total rounds won'],
    axis=1
)

def get_opponent_stat(df, source_col, new_col):
    df[new_col] = df.apply(lambda row: df.loc[row.name + 1 if row.name % 2 == 0 else row.name - 1, source_col], axis=1)
    return df

team_stats = get_opponent_stat(team_stats, 'Total rounds won', 'Opp Total Round Won')
team_stats = get_opponent_stat(team_stats, 'Average player rating', 'Opp Average Player Rating')
team_stats = get_opponent_stat(team_stats, 'Max Kill Count', 'Opp Max Kill Count')
team_stats = get_opponent_stat(team_stats, 'Min Kill Count', 'Opp Min Kill Count')
team_stats = get_opponent_stat(team_stats, 'Kill Count difference', 'Opp Kill Count Difference')
team_stats = get_opponent_stat(team_stats, 'Total MK', 'Opp Total MK')
team_stats = get_opponent_stat(team_stats, 'Max ADR', 'Opp Max ADR')
team_stats = get_opponent_stat(team_stats, 'Min ADR', 'Opp Min ADR')
team_stats = get_opponent_stat(team_stats, 'Avg ADR', 'Opp Avg ADR')
team_stats = get_opponent_stat(team_stats, 'ADR Difference', 'Opp ADR Differential')
team_stats = get_opponent_stat(team_stats, '1vX Num', 'Opp 1vX Num')
team_stats = get_opponent_stat(team_stats, 'Num Trades', 'Opp Num Trades')
team_stats = get_opponent_stat(team_stats, 'Number of first kills', 'Opp First Kills')
team_stats = get_opponent_stat(team_stats, 'Rounds Streak', 'Opp Round Streak')
team_stats = get_opponent_stat(team_stats, 'T rounds won', 'Opp T rounds won')
team_stats = get_opponent_stat(team_stats, 'CT rounds won', 'Opp CT rounds won')

team_stats[['Average player rating', 'Avg ADR', 'Opp Avg ADR','Opp Average Player Rating']] = team_stats[['Average player rating', 'Avg ADR', 'Opp Avg ADR','Opp Average Player Rating']].round(2)

team_stats['Win'] = (team_stats['Maps won'] / team_stats['Maps Played'] > 0.5).astype(int)

team_stats['Tournament'] = 'BLAST Bounty 2026 Season 1'
team_stats['Stage'] = 'Playoffs'

# Define column order
column_order = [
    'Team', 'Opponent', 'Tournament', 'Stage', 'Maps won', 'Maps Played',
    'T rounds won', 'CT rounds won', 'Total rounds won', 'Round Differential',
    'Opp T rounds won', 'Opp CT rounds won', 'Opp Total Round Won',
    'Average player rating', 'Max Kill Count', 'Min Kill Count', 'Kill Count difference',
    'Total MK', 'Max ADR', 'Min ADR', 'Avg ADR', 'ADR Difference',
    'Opp Average Player Rating', 'Opp Max Kill Count', 'Opp Min Kill Count',
    'Opp Kill Count Difference', 'Opp Total MK', 'Opp Max ADR', 'Opp Min ADR',
    'Opp Avg ADR', 'Opp ADR Differential', '1vX Num', 'Num Trades', 'Rounds Streak',
    'Number of first kills', 'Opp 1vX Num', 'Opp Num Trades', 'Opp Round Streak',
    'Opp First Kills', 'Map 1', 'Map 2', 'Map 3','Map 4','Map 5', 'Win'
]

team_stats = team_stats[[col for col in column_order if col in team_stats.columns]]

print(team_stats)


team_stats.to_csv(f'{save_dir}matches_stats.csv', index=False,float_format='%.2f')



