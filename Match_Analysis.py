# pip3 install numpy pandas scipy
# pip3 install matplotlib seaborn plotnine
# pip3 install scikit-learn statsmodels
# pip3 install xgboost shap dtreeviz

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.api as sm
import statsmodels.formula.api as smf
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.ensemble import BaggingClassifier, RandomForestRegressor, GradientBoostingRegressor
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split, ParameterGrid
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, classification_report, 
                             ConfusionMatrixDisplay, mean_absolute_error, mean_squared_error,
                             r2_score, confusion_matrix, roc_curve, roc_auc_score, auc)
import xgboost as xgb
import shap
import dtreeviz
from scipy.spatial.distance import pdist, squareform
from scipy.cluster.hierarchy import linkage, dendrogram, fcluster, set_link_color_palette
import scipy.cluster.hierarchy as sch
from pandas.api.types import CategoricalDtype
from plotnine import *
import matplotlib
import glob
from matplotlib.ticker import MaxNLocator


# Read in file paths
file_paths = glob.glob('C:/Users/cbmch/OneDrive/Desktop/Personal project/Data Sets/*.xlsx')

# Read and combine all Excel files
combined_df = pd.concat([pd.read_excel(f) for f in file_paths], ignore_index=True)

all_matches = combined_df

# Check the result
print(combined_df.shape)
print(combined_df.head())
### EDA
## Which Teams played the most matches? How many of those matches did those teams win?
# Get wins and total matches per team
team_stats = all_matches.groupby('Team').agg(
    total_matches=('Team', 'size'),
    matches_won=('Win', 'sum')
).sort_values('total_matches', ascending=False).head(15)

# Calculating win percentage
team_stats['win_pct'] = (team_stats['matches_won'] / team_stats['total_matches']) * 100

# Calculate matches lost
team_stats['matches_lost'] = team_stats['total_matches'] - team_stats['matches_won']

# Keep losses and wins for stacking 
team_stats_plot = team_stats[['matches_lost', 'matches_won']]

ax = team_stats_plot.plot(kind='bar', stacked=True, figsize=(10, 6), color=['orange', 'blue'])
for i, (idx, row) in enumerate(team_stats.iterrows()):
    ax.text(i, row['total_matches'] + 1, f"{row['win_pct']:.1f}%", 
            ha='center', va='bottom', fontsize=9)
    
plt.xlabel('Team')
plt.ylabel('Total Matches')
plt.title('Matches Won vs Lost by Team (Top 15)')
plt.xticks(rotation=30, fontsize=10)
plt.legend(['Losses', 'Wins'])
plt.tight_layout()
plt.savefig(r"C:/Users/cbmch/OneDrive/Desktop/Personal project/Graphs/figure_1.png", dpi=600)
plt.show()

### Which teams have the highest and lowest average ADR
team_game_counts = all_matches.groupby('Team').size()
teams_with_enough_games = team_game_counts[team_game_counts >= 15].index
filtered_matches = all_matches[all_matches['Team'].isin(teams_with_enough_games)]

adr_max = pd.DataFrame(filtered_matches.groupby('Team')['Avg ADR'].mean().sort_values(ascending=False).head(5))
adr_min = pd.DataFrame(filtered_matches.groupby('Team')['Avg ADR'].mean().sort_values(ascending=False).tail(5).iloc[::-1])

## Highest average ADR
ax = sns.barplot(adr_max, x='Team', y='Avg ADR', hue='Team')
plt.ylabel('Average ADR')
plt.title('Highest Average ADR by Team (Min 15 Games)')
plt.ylim(70, 78)
plt.xticks(fontsize=10)
for container in ax.containers:
    ax.bar_label(container, fmt='%.2f', padding=3, fontsize=12)
plt.savefig(r"C:/Users/cbmch/OneDrive/Desktop/Personal project/Graphs/figure_2.png", dpi=600)
plt.show()

## Lowest average ADR
ax = sns.barplot(adr_min, x='Team', y='Avg ADR', hue='Team')
plt.ylabel('Average ADR')
plt.title('Lowest Average ADR by Team (Min 15 Games)')
plt.ylim(55, 75)
plt.xticks(fontsize=10)
for container in ax.containers:
    ax.bar_label(container, fmt='%.2f', padding=3, fontsize=12)
plt.savefig(r"C:/Users/cbmch/OneDrive/Desktop/Personal project/Graphs/figure_3.png", dpi=600)
plt.show()

### Which teams have the highest average round differential?

# Filter to only include teams with enough matches
m1 = all_matches.copy()

m1['avg_round_diff'] = m1['Round Differential'] / m1['Maps Played'] # Calculating average round differential

# Count matches per team and filter for teams with at least 15 matches
team_match_counts = m1.groupby('Team').size()
teams_with_enough_matches = team_match_counts[team_match_counts >= 15].index

# Filter to only include teams with enough matches
m1_filtered = m1[m1['Team'].isin(teams_with_enough_matches)]

round_diff = m1_filtered.groupby('Team')['avg_round_diff'].mean().sort_values(ascending=False).reset_index() # Grouping by team
round_diff['Rank'] = round_diff['avg_round_diff'].rank(ascending=False, method='min').astype(int) # Ranking
round_diff['color'] = round_diff['avg_round_diff'].apply(lambda x: 'green' if x > 0 else 'red')

offset = 0.05

plt.figure(figsize=(10, 8))
bars = plt.barh(round_diff['Team'], round_diff['avg_round_diff'], color=round_diff['color'])
plt.axvline(0, color='black', linewidth=0.8)
plt.xlabel('Average Round Differential')
plt.title('Average Round Differential by Team (Min 15 Matches)')
plt.yticks(ticks=[], labels=[])

for bar, team in zip(bars, round_diff['Team']):
    width = bar.get_width()
    if width > 0:
        ha = 'left'
        x = width + offset
    else:
        ha = 'right'
        x = width - offset
    plt.text(
        x, bar.get_y() + bar.get_height() / 2, team, ha=ha, va='center', fontsize=8,
        color='black')
plt.gca().invert_yaxis()
plt.tight_layout()
plt.savefig(r"C:/Users/cbmch/OneDrive/Desktop/Personal project/Graphs/figure_4.png", dpi=600)
plt.show()

### Derived Variables
matches_copy = all_matches.copy()

## Calculate per map ratios
per_map_cols = {
    'avg_round_diff': 'Round Differential',
    'mk_per_map': 'Total MK',
    'opp_mk_per_map': 'Opp Total MK',
    'trade_per_map': 'Num Trades',
    'opp_trade_per_map': 'Opp Num Trades',
    'avg_t_round_per_map': 'T rounds won',
    'avg_ct_round_per_map': 'CT rounds won',
    'opp_avg_t_round_per_map': 'Opp T rounds won',
    'opp_avg_ct_round_per_map': 'Opp CT rounds won',
    '1vX_per_map': '1vX Num',
    'opp_1vX_per_map': 'Opp 1vX Num',
    'first_kills_per_map': 'Number of first kills',
    'opp_first_kills_per_map': 'Opp First Kills'
}

for new_col, base_col in per_map_cols.items():
    matches_copy[new_col] = matches_copy[base_col] / matches_copy['Maps Played']

### Modeling
## Decison Tree - Win as outcome
# Splitting into X and Y, training and test, dropping coloumns related to winning rounds
y = matches_copy['Win']
X = matches_copy[['Max Kill Count','Min Kill Count', 'Kill Count difference', 
                    'Max ADR', 'Min ADR','ADR Difference', 'Opp Max Kill Count', 'Opp Min Kill Count', 
                    'Opp Kill Count Difference','Opp Max ADR', 'Opp Min ADR','Rounds Streak','Opp Round Streak',
                    'Opp ADR Differential','mk_per_map','opp_mk_per_map', 'trade_per_map', 'opp_trade_per_map', 
                    'avg_t_round_per_map', 'avg_ct_round_per_map', 'opp_avg_t_round_per_map',
                    'opp_avg_ct_round_per_map', '1vX_per_map','opp_1vX_per_map','first_kills_per_map',
                    'opp_first_kills_per_map' ]]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size = 0.2, random_state = 42)

# Initiailizing and fitting the model
tree_model = DecisionTreeClassifier(max_depth = 6, random_state = 42,
                                    min_samples_split = 2, min_samples_leaf = 2)  
tree_model.fit(X_train, y_train) # Fitting the model

# Visualizing the tree and saving it
viz_model = dtreeviz.model(tree_model, X_train = X_train, y_train = y_train,
                            feature_names = list(X_train.columns),target_name = "outcome")

v = viz_model.view(fontname = "DejaVu Sans")
v.save(r"C:\Users\cbmch\OneDrive\Desktop\Personal project\decision_tree_win.svg")

# Predicting using the tree
y_pred = tree_model.predict(X_test)
acc = accuracy_score(y_test, y_pred) 
print(f"\nDecision Tree Accuracy on Test Set: {acc * 100:.2f}%")

# Creating and displaying the tree
labels = tree_model.classes_
cm = confusion_matrix(y_test, y_pred, labels = labels) 
disp = ConfusionMatrixDisplay(confusion_matrix = cm, display_labels = labels) 
disp.plot(cmap = "Blues") 
plt.title("Confusion Matrix — Decision Tree - Win")
plt.show()

# Prediciting using the tree
class_names = [str(c) for c in tree_model.classes_]

yhat = tree_model.predict(X_test)
print("Accuracy:           ", round(accuracy_score(y_test, yhat),4))
print("Balanced Accuracy:  ", round(balanced_accuracy_score(y_test, yhat),4))
print("\nClassification report:\n", classification_report(y_test, yhat, target_names = class_names))

#Feature Importance
feature_importance = pd.Series(tree_model.feature_importances_, 
                               index = X_train.columns).sort_values(ascending = False)
feature_importance

## Decision Tree- Round Differential
# Features Related to winning rounds are removed
y = matches_copy['avg_round_diff']
X = matches_copy[['Max Kill Count','Min Kill Count', 'Kill Count difference', 'Max ADR', 'Min ADR',
                  'ADR Difference','Opp Max Kill Count', 'Opp Min Kill Count', 'Opp Kill Count Difference', 
                  'Opp Max ADR', 'Opp Min ADR', 'Opp ADR Differential','Rounds Streak', 'Opp Round Streak',
                  'mk_per_map', 'opp_mk_per_map', 'trade_per_map','opp_trade_per_map', '1vX_per_map',
                  'opp_1vX_per_map','first_kills_per_map', 'opp_first_kills_per_map']]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size = 0.2, random_state = 42)

# Creating, fitting, and saving the tree
tree_model = DecisionTreeRegressor(max_depth = 8, random_state = 42, min_samples_leaf = 1,
                                   min_samples_split = 10, criterion = 'squared_error')

tree_model.fit(X_train, y_train)

viz_model = dtreeviz.model(tree_model, X_train = X_train, y_train = y_train,
                           feature_names = list(X_train.columns),target_name = "outcome")

v = viz_model.view(fontname = "DejaVu Sans")
v.save(r"C:\Users\cbmch\OneDrive\Desktop\Personal project\decision_tree_differential.svg")

# Predicting using Tree
y_pred = tree_model.predict(X_test)

# Calculating accurary metrics
mae = mean_absolute_error(y_test, y_pred)
mse = mean_squared_error(y_test, y_pred)
rmse = np.sqrt(mse)
r2 = r2_score(y_test, y_pred)

print("MAE:", mae)
print("R²:", r2)
print("MSE:", mse)
print("RMSE:", rmse)
    
# Displaying Actual vs. Predicted    
plt.scatter(y_test, y_pred, alpha = 0.7)
plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--')
plt.xlabel("Actual Round Difference")
plt.ylabel("Predicted Round Difference")
plt.title("Predicted vs Actual")
plt.show()

## Random Forest Classifier for Round Differential
# Decided to use an ensemble model to increase R2 of model
# Using same training and test split as before
rf = RandomForestRegressor(n_estimators = 500, max_depth = 10, min_samples_leaf = 5,
                           random_state = 42, n_jobs = -1)

# Fitting and predicting with the model
rf.fit(X_train, y_train)
y_pred = rf.predict(X_test)

# Calculating error metrics
mae = mean_absolute_error(y_test, y_pred)
mse = mean_squared_error(y_test, y_pred)
rmse = np.sqrt(mse)
r2 = r2_score(y_test, y_pred)

print("MAE:", mae)
print("R²:", r2)
print("MSE:", mse)
print("RMSE:", rmse)

# Plotting predicted vs. actual
plt.figure(figsize=(12, 8))
plt.scatter(y_test, y_pred, alpha = 0.7)
plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--')
plt.xlabel("Actual Round Difference")
plt.ylabel("Expected Round Difference")
plt.title("Expected vs Actual")
plt.savefig(r"C:/Users/cbmch/OneDrive/Desktop/Personal project/Graphs/figure_5.png", dpi=600)
plt.show()

## Feature Importance - Round Differential
feature_importance = pd.Series(rf.feature_importances_, 
                               index = X_train.columns).sort_values(ascending = False)
feature_importance

#### Logistic Regression - Win
## Features come from decision tree - Win feature importance
# Splitting into training and test set
y = matches_copy['Win']
X = matches_copy[['mk_per_map', 'opp_mk_per_map', 'opp_avg_t_round_per_map', 'avg_t_round_per_map',
                  'Rounds Streak', 'avg_ct_round_per_map', 'opp_avg_ct_round_per_map', 'Opp Max ADR',
                  'first_kills_per_map', 'trade_per_map', 'Opp Round Streak', '1vX_per_map', 'Opp ADR Differential',
                  'opp_first_kills_per_map', 'Opp Kill Count Difference', 'opp_trade_per_map', 'Max ADR', 'Min ADR',
                  'Max Kill Count']]

X_train, X_test, y_train, y_test = train_test_split(X,y,test_size = 0.2, random_state = 42,stratify = y)

# Scaling the features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

X_train_scaled = pd.DataFrame(X_train_scaled, columns = X.columns, index = X_train.index)
X_test_scaled = pd.DataFrame(X_test_scaled, columns = X.columns, index = X_test.index)

# Adding in a constant
X_train_sm = sm.add_constant(X_train_scaled)
X_test_sm = sm.add_constant(X_test_scaled)

fit = sm.Logit(y_train,X_train_sm).fit(disp = False)

print(fit.summary2())

# Predicting with model
y_prob = fit.predict(X_test_sm)
y_pred = (y_prob >= 0.5).astype(int)

# Creating and displaying the confusion matrix
cm = confusion_matrix(y_test, y_pred)
disp = ConfusionMatrixDisplay(confusion_matrix = cm, display_labels = [0, 1])
disp.plot(cmap = plt.cm.Blues) 
plt.title("Logistic Regression - Win - Confusion Matrix")
plt.savefig(r"C:/Users/cbmch/OneDrive/Desktop/Personal project/Graphs/figure_6.png", dpi=600)
plt.show()

accuracy = accuracy_score(y_test, y_pred)
print(f"Accuracy: {accuracy:.3f}")

### Linear regression - Round Differential
## Features come from RandomForest feature importance
# Splitting into training and test set
y = matches_copy['avg_round_diff']
X = matches_copy[['mk_per_map', 'opp_mk_per_map', 'Opp Round Streak', 'Rounds Streak',
                  'opp_first_kills_per_map', 'first_kills_per_map', 'Opp Max ADR', 'Max ADR',
                  'Opp Min Kill Count', 'Min Kill Count', 'opp_1vX_per_map', 'Min ADR', '1vX_per_map',
                  'Opp Min ADR', 'Max Kill Count', 'Opp Max Kill Count', 'Opp ADR Differential',
                  'ADR Difference', 'opp_trade_per_map', 'trade_per_map', 'Kill Count difference',
                  'Opp Kill Count Difference']]

X_train,X_test,y_train,y_test = train_test_split(X, y, test_size = 0.2, random_state = 42)

# Adding in a constant
X_train_sm = sm.add_constant(X_train)
X_test_sm = sm.add_constant(X_test)

linreg = sm.OLS(y_train, X_train_sm).fit()
print(linreg.summary())

# Predicting with tree and calculating error metrics
y_pred = linreg.predict(X_test_sm)

mae = mean_absolute_error(y_test, y_pred)
mse = mean_squared_error(y_test, y_pred)
rmse = np.sqrt(mse)
r2 = r2_score(y_test, y_pred)

print("MAE:", mae)
print("R²:", r2)
print("MSE:", mse)
print("RMSE:", rmse)

# Plotting predicted vs. actual
plt.scatter(y_test, y_pred, alpha = 0.7)
plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--')
plt.xlabel("Actual Round Difference")
plt.ylabel("Predicted Round Difference")
plt.title("Predicted vs Actual")
plt.show()

### XGBoost - Win as Outcome
## Feature importance is done by XGBoost model
# Splitting into training and test sets
y = matches_copy['Win']
X = matches_copy[['Max Kill Count', 'Min Kill Count', 'Kill Count difference', 'Total MK', 'Max ADR','Min ADR',
                  'ADR Difference','Opp Max Kill Count','Opp Min Kill Count', 'Opp Kill Count Difference', 
                  'Opp Total MK','Opp Max ADR', 'Opp Min ADR','Opp ADR Differential','Rounds Streak','Number of first kills',
                  'Opp Round Streak', 'mk_per_map', 'opp_mk_per_map','trade_per_map', 'opp_trade_per_map',
                   '1vX_per_map','opp_1vX_per_map','first_kills_per_map', 'opp_first_kills_per_map']]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size = 0.2, random_state = 42)

# Creating DMatrix for training and test features 
dtrain = xgb.DMatrix(X_train, label = y_train, feature_names = X.columns.tolist())
dtest = xgb.DMatrix(X_test, label = y_test, feature_names = X.columns.tolist())

# Setting parameters
params = {
    "objective": "binary:logistic",
    "eval_metric": ["auc", "error"],
    "seed": 42,
    "eta": 0.05,
    "tree_method": "hist",
    "colsample_bytree":0.7,
    "subsample":0.7,
    "min_child_weight":3,
    "max_depth": 7
}

watchlist = [(dtrain, "train")]

# Creating the model
booster = xgb.train(
    params = params,
    dtrain = dtrain,
    num_boost_round = 300,
    evals = watchlist,
    verbose_eval = 50
)

# Predicting with the model and calculating accuracy
test_pred_raw = booster.predict(dtest) 
test_pred_cls = (test_pred_raw >= 0.5).astype(int)
print("\nAccuracy):")
print(accuracy_score(y_test, test_pred_cls))

# Displaying confusion matrix
print("\nConfusion matrix:")
cm = (confusion_matrix(y_test, test_pred_cls))
disp = ConfusionMatrixDisplay(confusion_matrix = cm)
disp.plot(cmap = "Blues") 
plt.title("Confusion Matrix — XGBoost - Win") 
plt.show()

## Creating AUC Curve for model
# Predicting with dtest
y_pred_proba = booster.predict(dtest)
fpr, tpr, thresholds = roc_curve(y_test, y_pred_proba)
roc_auc = auc(fpr, tpr)

plt.figure(figsize = (8, 6))
plt.plot(fpr, tpr, label = f"ROC curve (AUC = {roc_auc:.3f})")
plt.plot([0, 1], [0, 1], linestyle = "--", label = "Random classifier")
plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")
plt.title("ROC Curve – XGBoost")
plt.legend(loc = "lower right")
plt.grid(True)
plt.show()

## Shap Values and Directionality
explainer = shap.TreeExplainer(booster)
shap_values = explainer(X_train)

ax = shap.plots.bar(shap_values, max_display = 8, show = False)  
plt.xticks(fontsize = 8)  
plt.yticks(fontsize = 5) 
plt.show()

fig = shap.plots.beeswarm(shap_values, show = False)
ax = plt.gca()
ax.xaxis.label.set_size(16)  
ax.yaxis.label.set_size(5)
ax.tick_params(axis = 'x', labelsize = 12)
ax.tick_params(axis = 'y', labelsize = 5)
plt.show()

### XGBoost - Round Differential as the outcome
## Feature importance is done by XGBoost model
# Splitting into training and test sets
y = matches_copy['avg_round_diff']
X = matches_copy[['Max Kill Count', 'Min Kill Count','Kill Count difference', 
                  'Max ADR', 'Min ADR','ADR Difference', 'Opp Max Kill Count',
                  'Opp Min Kill Count', 'Opp Kill Count Difference', 
                  'Opp Max ADR', 'Opp Min ADR', 'Opp ADR Differential', 'Rounds Streak',
                  'Opp Round Streak', 'mk_per_map', 'opp_mk_per_map','trade_per_map', 
                  'opp_trade_per_map', '1vX_per_map', 'opp_1vX_per_map','first_kills_per_map', 
                  'opp_first_kills_per_map']]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size = 0.2, random_state = 42)

X_xgb = X.copy()

# Creating the model
booster = xgb.XGBRegressor(
    objective = 'reg:squarederror',
    n_estimators = 300,
    learning_rate = 0.03,
    max_depth = 8,
    colsample_bytree = 0.7,
    reg_lambda = 2,
    reg_alpha = 0.01,
    subsample = 0.6,
    min_child_weight = 7,
    tree_method = 'hist',
    random_state = 42,
    gamma = 0.1
)

watchlist = [(X_test,y_test)]

# Fitting the model
booster.fit(X_train, y_train, eval_set = watchlist, verbose = True)

# Predicting and calculating error metrics
y_pred = booster.predict(X_test) 

mae = mean_absolute_error(y_test, y_pred)
mse = mean_squared_error(y_test, y_pred)
rmse = np.sqrt(mse)
r2 = r2_score(y_test, y_pred)

print("MAE:", mae)
print("MSE:", mse)
print("RMSE:", rmse)
print("R²:", r2)

# Plotting actual vs. predicted
results = pd.DataFrame({
    'Actual': y_test,
    'Predicted': y_pred
})

plt.figure(figsize = (8, 8))
sns.scatterplot(data = results, x = 'Actual', y = 'Predicted', alpha = 0.6)
plt.plot([results.Actual.min(), results.Actual.max()],
         [results.Actual.min(), results.Actual.max()],
         color = 'red', linestyle='--', label='Perfect prediction')
plt.xlabel('Actual', fontsize = 16)  
plt.ylabel('Predicted', fontsize = 16)
plt.title('Actual vs Predicted', fontsize = 18)
plt.xticks(fontsize = 12)
plt.yticks(fontsize = 12)
plt.legend(fontsize = 12)
plt.grid(True)
plt.show()

## Shap Values and Directionality
explainer = shap.TreeExplainer(booster)
shap_values = explainer(X_train)

shap.plots.bar(shap_values, max_display=10, show=False)
fig = plt.gcf()  
fig.set_size_inches(14, 8)
plt.xticks(fontsize=12)
plt.yticks(fontsize=10)
plt.savefig(r"C:/Users/cbmch/OneDrive/Desktop/Personal project/Graphs/figure_7.png", dpi=600)
plt.show()

fig = shap.plots.beeswarm(shap_values, show=False)
ax = plt.gca()
ax.xaxis.label.set_size(16)  
ax.yaxis.label.set_size(5)
ax.tick_params(axis='x', labelsize=12)
ax.tick_params(axis='y', labelsize=10)
plt.gcf().set_size_inches(14, 8)  
plt.tight_layout()                 
plt.savefig(r"C:/Users/cbmch/OneDrive/Desktop/Personal project/Graphs/figure_8.png", dpi=600, bbox_inches='tight')
plt.show()

### Clustering
## Hierarchical Clustering
# Setting up data that will be used for clustering, took out all columns that had a per map equivalant
cols = ['Max Kill Count', 'Min Kill Count','Kill Count difference', 'Max ADR', 'Min ADR',
        'Avg ADR','ADR Difference' , 'Opp Max Kill Count', 'Opp Min Kill Count',
        'Opp Kill Count Difference','Opp Max ADR', 'Opp Min ADR', 'Opp Avg ADR', 
        'Opp ADR Differential', 'Rounds Streak', 'Opp Round Streak','avg_round_diff',
        'mk_per_map', 'opp_mk_per_map', 'trade_per_map', 'opp_trade_per_map',
        'avg_t_round_per_map', 'avg_ct_round_per_map', 'opp_avg_t_round_per_map',
        'opp_avg_ct_round_per_map', '1vX_per_map', 'opp_1vX_per_map', 'first_kills_per_map',
        'opp_first_kills_per_map']

# Grouping by team
matches_grouped = matches_copy.groupby('Team')[cols].mean()
matches_grouped

match_counts = matches_copy.groupby('Team').size()

# Filter teams with at least 15 matches
matches_grouped = matches_grouped[match_counts >= 15]
matches_grouped

X = matches_grouped.select_dtypes(include = [np.number]).copy()

# Scaling my features
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X) 
sdata = pd.DataFrame(X_scaled, index = matches_grouped.index, columns = X.columns)

# Making distance vectors and matrix
dist_vec = pdist(sdata.values, metric = 'euclidean')
dist_mat = squareform(dist_vec) 

hc = linkage(dist_vec, method = 'ward')

distance_threshold = 9

# Pulling out cluster labels
cluster_labels = fcluster(hc, t = distance_threshold, criterion = 'distance')
sdata['Cluster'] = cluster_labels

# Plotting the tree
plt.figure(figsize=(16, 8))
dendrogram(hc,labels = list(sdata.index), orientation = 'right', leaf_font_size = 9,
           color_threshold = distance_threshold, above_threshold_color = "#888888")
plt.title("Team Performance Clustering — Dendrogram (Average linkage, Euclidean distance)")
plt.xlabel("Distance")
plt.tight_layout()
plt.savefig(r"C:/Users/cbmch/OneDrive/Desktop/Personal project/Graphs/figure_9.png", dpi=1200, bbox_inches='tight')
plt.show() 

# Cluster Assignment and Stats
clusters = fcluster(hc, t = distance_threshold, criterion = 'distance') 
data_k = matches_grouped.copy() 
data_k['cluster'] = clusters
data_k.head()

print(data_k['cluster'].value_counts().sort_index().to_frame('n'))

profile_c = (data_k.groupby('cluster').agg(['mean', 'std', 'count']).round(2))
profile_c

## Heat Map - Hierarchical clustering
# Extract cluster centers
cluster_means = (data_k.groupby('cluster')[X.columns].mean())

cluster_means_scaled = pd.DataFrame(scaler.fit_transform(cluster_means), 
                                    index = cluster_means.index,
                                    columns = cluster_means.columns)

# Plotting the heatmap
plt.figure(figsize = (14, 8))
sns.heatmap(cluster_means_scaled.T, cmap = "RdBu_r", center = 0, linewidths = 0.5,
            linecolor = "white", cbar_kws = {"label": "Scaled Feature Value"})
plt.title("Hierarchical Clustering – Cluster Profiles\n"
          "Blue = Below Avg, Red = Above Avg", fontsize = 14)
plt.xlabel("Cluster")
plt.ylabel("Features")
plt.xticks(rotation = 0)
plt.yticks(rotation = 0)
plt.tight_layout()
plt.savefig(r"C:/Users/cbmch/OneDrive/Desktop/Personal project/Graphs/figure_10.png", dpi=600, bbox_inches='tight')
plt.show()

## Clustering - Multiple Linkage
# Using same split
hc = linkage(pdist(sdata.values, metric = 'euclidean'), method ='complete')

plt.figure(figsize = (10, 12))
dendrogram(hc, labels = list(sdata.index), orientation = 'right', leaf_font_size = 9,
           color_threshold = hc[-5+1, 2], above_threshold_color = "#888888")
plt.title("Budapest Major: Match Results — Dendrogram (Multiple linkage, Euclidean distance))")
plt.xlabel("Distance")
plt.tight_layout()
plt.show()

clusters_single = fcluster(hc, t = 5, criterion = 'maxclust') 

data = matches_grouped.copy() 
data['cluster_single'] = clusters_single 

print(data['cluster_single'].value_counts().sort_index().to_frame('n'))

# Heatmap - Multiple Linkage
cluster_means_single = (data.groupby('cluster_single')[X.columns].mean())

cluster_means_single_scaled = pd.DataFrame(scaler.fit_transform(cluster_means_single),
                                           index = cluster_means_single.index,
                                           columns = cluster_means_single.columns)
plt.figure(figsize=(10, 14))
sns.heatmap(cluster_means_single_scaled.T, cmap = "RdBu_r", center = 0, linewidths = 0.4,
            linecolor = "white", cbar_kws = {"label": "Scaled Feature Value"})
plt.title("Hierarchical Clustering (Complete Linkage)\n"
    "Cluster Profiles — Blue = Below Avg, Red = Above Avg", fontsize = 14)
plt.xlabel("Cluster")
plt.ylabel("Features")
plt.xticks(rotation = 0)
plt.yticks(rotation = 0)
plt.tight_layout()
plt.show()

## kMeans Clustering
kmeans = KMeans(n_clusters = 5, random_state = 42)
labels = kmeans.fit_predict(X_scaled)

# Getting cluster labels
matches_grouped['cluster'] = labels

# Getting cluster counts
cluster_counts = matches_grouped['cluster'].value_counts().sort_index()
print(cluster_counts)

centroids = pd.DataFrame(kmeans.cluster_centers_,columns = X.columns)

# Get cluster summary
cluster_summary = (matches_grouped.groupby('cluster')[X.columns].mean().round(2))
cluster_summary

km_centroids = linkage(centroids.values, method = 'average', metric = 'euclidean')

# Plotting the clustering result
plt.figure(figsize = (8, 6))
dendrogram(km_centroids, labels = [f"Cluster {i}" for i in range(5)],
           leaf_rotation = 0, leaf_font_size = 12, color_threshold = None)
plt.title("Hierarchical Clustering of KMeans Centroids")
plt.xlabel("Distance")
plt.ylabel("Clusters")
plt.tight_layout()
plt.show()

## Heatmap - kMeans
cluster_summary_scaled = pd.DataFrame(scaler.fit_transform(cluster_summary),
                                      index = cluster_summary.index,
                                      columns = cluster_summary.columns)
sns.heatmap(cluster_summary_scaled.T, cmap = "RdBu_r", center = 0, linewidths = 0.4,
            linecolor = "white", cbar_kws = {"label": "Scaled Feature Value"})
plt.title("KMeans Clustering (k = 5)\n"
    "Cluster Profiles — Blue = Below Avg, Red = Above Avg", fontsize = 14)
plt.xlabel("Cluster")
plt.ylabel("Features")
plt.xticks(rotation = 0)
plt.yticks(rotation = 0)
plt.tight_layout()
plt.show()

### Agglomerative Clustering 
# Scaling data
X = matches_grouped.select_dtypes(include = [np.number]).copy()
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X) 
sdata = pd.DataFrame(X_scaled, index = matches_grouped.index, columns = X.columns)

# Finding optimal clusters
wcss = []
K_range = range(2, 11)

for k in K_range:
    clustering = AgglomerativeClustering(n_clusters=k, metric='euclidean', linkage='ward')
    clustering.fit(X_scaled)
    # Calculate WCSS manually
    wcss_k = 0
    for cluster in range(k):
        cluster_points = X_scaled[clustering.labels_ == cluster]
        centroid = cluster_points.mean(axis=0)
        wcss_k += ((cluster_points - centroid) ** 2).sum()
    wcss.append(wcss_k)

# Plot elbow curve
plt.figure(figsize=(10, 6))
plt.plot(K_range, wcss, 'bo-')
plt.xlabel('Number of Clusters')
plt.ylabel('Within-Cluster Sum of Squares')
plt.title('Elbow Method for Optimal k')
plt.grid(True)
plt.show()
# Clustering
clustering = AgglomerativeClustering(n_clusters=3, metric='euclidean', linkage='ward')
sdata['Cluster'] = clustering.fit_predict(X_scaled) + 1  

print(sdata['Cluster'].value_counts())

# Creating linkage matrix
linkage_matrix = sch.linkage(X_scaled, method='ward', metric='euclidean')

# Plotting the dendrogram - color threshold adjusted for 3 clusters
plt.figure(figsize=(16, 8))
sch.dendrogram(linkage_matrix, labels=sdata.index, leaf_rotation=0,
               leaf_font_size=10, color_threshold=linkage_matrix[-2, 2],  # -2 for 3 clusters
               orientation='right')
plt.title('Agglomerative Clustering Dendrogram (3 Clusters)')
plt.xlabel('Euclidean Distance')
plt.ylabel('Samples')
plt.savefig(r"C:/Users/cbmch/OneDrive/Desktop/Personal project/Graphs/figure_11.png", dpi=600, bbox_inches='tight')
plt.show()

## Heatmap - Agglomerative
sdata_with_clusters = sdata.copy()
sdata_with_clusters['Cluster'] = sdata['Cluster']

# Getting cluster summary
cluster_summary = sdata_with_clusters.groupby('Cluster').agg(['mean', 'std'])
print("Cluster Summary Statistics:\n", cluster_summary)

cluster_means = (sdata.groupby('Cluster')[X.columns].mean())


profile_c = sdata.groupby('Cluster').agg(['mean', 'std', 'count']).round(2)

# Displaying the heat map
plt.figure(figsize = (14, 8))
sns.heatmap(cluster_means.T, cmap = "RdBu_r", center = 0, vmin = -1.5, vmax = 1.5,
            linewidths = 0.4, linecolor = "white", cbar_kws = {"label": "Scaled Feature Value"})
plt.title("Agglomerative Clustering (Ward Linkage)\n"
          "Cluster Profiles — Blue = Below Avg, Red = Above Avg", fontsize = 14)
plt.xlabel("Cluster")
plt.ylabel("Features")
plt.xticks(rotation = 0)
plt.yticks(rotation = 0)
plt.tight_layout()
plt.savefig(r"C:/Users/cbmch/OneDrive/Desktop/Personal project/Graphs/figure_12.png", dpi=600, bbox_inches='tight')
plt.show()

# FURIA World Team Ranking Graph
furia = pd.read_csv('C:/Users/cbmch/OneDrive/Desktop/Personal project/furia_weekly_rankings_2025_2026.csv')
furia['date'] = pd.to_datetime(furia['date'])

plt.figure(figsize = (14, 8))
sns.lineplot(data = furia, x = 'date', y = 'rank')
plt.gca().invert_yaxis()
plt.yticks(range(0, max(furia['rank']) + 5, 5))
plt.ylim(bottom = max(furia['rank']) + 1, top = 0)
plt.title('FURIA World Team Ranking 01/06/2025 - 02/16/2026')
plt.xlabel('Date')
plt.ylabel('World Ranking')
plt.axvline(x=pd.to_datetime('2025-04-11'), color='orange', linestyle='--')
plt.text(pd.to_datetime('2025-04-11'), 8, 'FURIA sign Molodoy', rotation=90, va='top', ha='right', fontsize=9, color='black')
plt.savefig(r"C:/Users/cbmch/OneDrive/Desktop/Personal project/Graphs/figure_15.png", dpi=600, bbox_inches='tight')
plt.show()

# Donk Water Fall Graph
spirit_chengdu = all_matches[
    (all_matches['Tournament'].str.contains('IEM Chengdu 2025', case=False)) &
    ((all_matches['Team'] == 'Spirit') & (all_matches['Opponent'] == 'Falcons'))
]

spirit_katowice = all_matches[
    (all_matches['Tournament'].str.contains('IEM Katowice 2025', case=False)) &
    ((all_matches['Team'] == 'Spirit') & (all_matches['Opponent'] == 'Natus Vincere'))
]

# Use positional index to align with X
chengdu_pos = all_matches.index.get_indexer(spirit_chengdu.index)
katowice_pos = all_matches.index.get_indexer(spirit_katowice.index)

X_chengdu = X_xgb.loc[spirit_chengdu.index]
X_katowice = X_xgb.loc[spirit_katowice.index]

explainer = shap.Explainer(booster, X_train)
shap_values_chengdu = explainer(X_chengdu)
shap_values_katowice = explainer(X_katowice)

plt.figure()
shap.plots.waterfall(shap_values_chengdu[0], show=False)
plt.title("Spirit vs Falcons - IEM Chengdu 2025")
plt.tick_params(axis='y', labelsize=8)
plt.tight_layout()
plt.savefig(r"C:/Users/cbmch/OneDrive/Desktop/Personal project/Graphs/figure_13.png", dpi=600, bbox_inches='tight')
plt.show()

plt.figure()
shap.plots.waterfall(shap_values_katowice[0], show=False)
plt.title("Spirit vs Natus Vincere - IEM Katowice 2025")
plt.tick_params(axis='y', labelsize=8)
plt.tight_layout()
plt.savefig(r"C:/Users/cbmch/OneDrive/Desktop/Personal project/Graphs/figure_14.png", dpi=600, bbox_inches='tight')
plt.show()