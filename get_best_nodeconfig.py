#!/usr/bin/env python3

import argparse

import pandas as pd

def get_best_node_config(node_config_file, feature_file, ranking_column):
    df = pd.read_csv(feature_file)
    df.sort_values(ranking_column, ascending=False, inplace=True)
    best_sim_number =  df.iloc[0]['simNumber']
    print("best sim number = {}".format(best_sim_number))
    
    best_node_config = None
    with open(node_config_file) as f:
        for i, line in enumerate(f):
            if i == best_sim_number:
                best_node_config = line
                break
    return best_node_config

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('node_config_file')
    parser.add_argument('feature_file')
    parser.add_argument('ranking_column')
    args = parser.parse_args()
    print(get_best_node_config(args.node_config_file, args.feature_file,
        args.ranking_column))
