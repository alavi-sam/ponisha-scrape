import numpy as np
import pandas as pd
from pygments.lexers import asc

from DataAccessLayer.Connection import SQL
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeRegressor, DecisionTreeClassifier
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVR, SVC
from sklearn.linear_model import LinearRegression, Lasso, ridge_regression, LogisticRegression
from sklearn.preprocessing import MinMaxScaler, StandardScaler
import matplotlib.pyplot as plt
from mlxtend.frequent_patterns import apriori, association_rules


def create_ohe_df():
    instance = SQL()
    instance.connect()
    con = instance.connection

    df_skills = pd.read_sql("SELECT * FROM skills", con)
    df_projects = pd.read_sql("SELECT * FROM ProjectsPreview", con)

    df_skills_values = np.zeros((df_projects.shape[0], df_skills.shape[0]))

    df_skills_ohe = pd.DataFrame(df_skills_values, columns=df_skills["SkillName"].values.tolist())

    df_main = pd.concat([df_projects, df_skills_ohe], axis=1)

    df_projects_skills = pd.read_sql("SELECT * FROM ProjectPreviewSkills", con)
    df_projects_skills = df_projects_skills.merge(df_skills, how='inner', right_on='ID', left_on='SkillID')
    df_projects_skills.sort_values(by='ProjectID', inplace=True)

    for i in range(df_projects_skills.shape[0]):
        skill_name = df_projects_skills.loc[i, 'SkillName']
        project_id = df_projects_skills.loc[i, 'ProjectID']
        df_main.loc[project_id-4, skill_name] = 1
    return df_main


def scale_values(scaler_name: str, data_frame: pd.DataFrame, column_name: str):
    if scaler_name == 'min_max':
        scaler = MinMaxScaler()
    elif scaler_name == 'standard_scaler':
        scaler = StandardScaler()
    else:
        raise ValueError
    column_values = data_frame[column_name].values.reshape(-1, 1)
    return scaler.fit_transform(column_values)


df = create_ohe_df()
# scaled_prices = scale_values('min_max', df, 'Price')
# scaled_prices = df["Price"].values.reshape(-1, 1)
price_category_none = np.zeros((df.shape[0]))
price_category_series = pd.Series(name='PriceCategory', data=price_category_none)
df = pd.concat([df, price_category_series], axis=1)

df_ohe_skills = df.iloc[:, 9:]

freq_items = apriori(df_ohe_skills, min_support=0.001, max_len=4, use_colnames=True)
asc_rule = association_rules(freq_items, metric='lift')
asc_rule.iloc[:, 0] = asc_rule.iloc[:, 0].apply(lambda x: list(x)[0])
asc_rule.iloc[:, 1] = asc_rule.iloc[:, 1].apply(lambda x: '/'.join(list(x)))


def get_combination_numbers(dataframe: pd.DataFrame, comb_num: int):
    result_df = dataframe[dataframe["consequents"].map(lambda x: len(x.split("/"))) == comb_num]
    result_df.sort_values(by=["lift", "support", "confidence"], ascending=False)
    return result_df


three_item_res = get_combination_numbers(asc_rule, 3)
print(three_item_res.head(10).to_string())


# Due to imbalanced data with this labeling it is not functional here.
for i in range(df.shape[0]):
    price = df.loc[i, "Price"]
    price_category = None
    if price < 200000:
        price_category = 0
    elif price < 500000:
        price_category = 1
    elif price < 1000000:
        price_category = 2
    elif price < 2000000:
        price_category = 3
    elif price < 5000000:
        price_category = 4
    elif price < 8000000:
        price_category = 5
    elif price < 10000000:
        price_category = 6
    elif price < 15000000:
        price_category = 7
    elif price < 20000000:
        price_category = 8
    else:
        price_category = 9
    df.loc[i, "PriceCategory"] = price_category

labels = df["Price"].values.reshape(-1, 1)
ss = StandardScaler()
labels = ss.fit_transform(labels)

features = df.iloc[:, 4:-1]

X_train, X_test, y_train, y_test = train_test_split(features, labels, train_size=.8)

# the model would not be trained well because of imbalanced data
model = GradientBoostingRegressor()
model.fit(X_train, y_train)
print(model.score(X_test, y_test))
y_pred = model.predict(X_test)

plt.scatter(y_pred, y_test)
plt.show()

