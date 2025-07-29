import pandas as pd

def join_sheets(df_l, df_r, key):
    #JOIN LOGIC: first, determine which side has more duplicates of the key value than the other. then, if found,
    #perform either right first-match-only join or left first-match-only join
    left_num = df_l[key].value_counts()
    right_num = df_r[key].value_counts()
    left_total_dups = (left_num > 1).sum()
    right_total_dups = (right_num > 1).sum()

