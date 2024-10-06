import pandas as pd


FI = pd.read_csv('assets/students_cyber_sante.csv')
FA = pd.read_csv('assets/students_cyber.csv').iloc[3:, 1:3]

print(FA['Prénom'])