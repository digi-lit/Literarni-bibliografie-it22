import pandas as pd
import numpy as np

df = pd.read_excel("data/Bibliografie prekladu.xlsx", index_col=0)
df = df.reset_index()  

y_nan = pd.isnull(df.loc[:, df.columns != 'Číslo záznamu']).all(1).to_numpy().nonzero()[0]
y_nan = np.append([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 ], y_nan)
print(y_nan)
df = df.drop(df.index[y_nan]).copy(deep=True)
df.to_csv('Bibliografie_prekladu.csv')