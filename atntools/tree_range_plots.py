import os

import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt

from atntools import settings
from atntools.trees import *
from atntools.tree_ranges import *

DEPENDENT_VAR = settings.DEFAULT_CLASS_ATTRIBUTE.replace('label_', '')


def plot_tree_ranges(tree_file, feature_file, output_dir):
    """
    Parameters
    ----------
    tree_file : str
        Weka's J48 output file
    """

    # Make output_dir if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    tree = parse_weka_j48_output_file(tree_file)
    instances = pd.read_csv(feature_file)
    instances['label'] = instances['label_' + DEPENDENT_VAR]

    # for plotting parameter values of best instances; does not affect other computations
    instances.sort_values(DEPENDENT_VAR, ascending=False, inplace=True)

    distributions = get_distributions(tree, instances)
    range_weights = get_range_weights(distributions)

    min_weight = 1.0
    max_weight = -1.0
    for segments in range_weights.values():
        for low, high, weight in segments:
            min_weight = min(weight, min_weight)
            max_weight = max(weight, max_weight)

    legend_displayed = False
    num_params = len(distributions)
    plt.figure(figsize=(9, 3 * num_params))

    for i, (param, distribution) in enumerate(sorted(distributions.items())):        
        plt.subplot(num_params, 2, i * 2 + 1)
        plt.title(param + " - simulation outcomes")
        plt.xlabel(param + " parameter value")
        plt.ylabel("number of simulations")

        # Prevent overlapping x-axis tick labels
        #if param.startswith('X'):
        #    plt.xticks(np.arange(0, 1, 0.2))

        left = []; width = []
        bottom_unlabeled = []; bottom_good = []
        height_bad = []; height_unlabeled = []; height_good = []
        for low, high, good, bad, unlabeled in distribution:
            left.append(low)
            width.append(high - low)
            bottom_unlabeled.append(bad)
            bottom_good.append(bad + unlabeled)
            height_bad.append(bad)
            height_unlabeled.append(unlabeled)
            height_good.append(good)    
        plt.bar(left=left, bottom=bottom_good, height=height_good, width=width, color='green', label='good')
        plt.bar(left=left, height=height_bad, width=width, color='orange', label='bad')
        
        plt.bar(left=left, bottom=bottom_unlabeled, height=height_unlabeled, width=width, color='lightgray', label='unlabeled')
        #plt.bar(left=left, bottom=bottom_unlabeled, height=height_unlabeled, width=width, color='white', hatch='/', label='unlabeled')
        
        if not legend_displayed:
            lgd = plt.legend(bbox_to_anchor=(0., 1.12, 1., .202), loc=3,
                    ncol=2, mode='expand', borderaxespad=0.)
            legend_displayed = True
        
        ranges = range_weights[param]
        plt.subplot(num_params, 2, i * 2 + 2)
        plt.title(param + " - parameter range scores")
        plt.xlabel(param + " parameter value")
        plt.ylabel("P(good) - P(bad)")
        left = []; height = []; width = []; color = []

        for low, high, weight in ranges:
            left.append(low)
            height.append(weight)
            width.append(high - low)
            color.append('green' if weight > 0 else 'orange')
        plt.bar(left=left, height=height, width=width, color=color)
        plt.ylim(min_weight - 0.1, max_weight + 0.1)
        
        # Plot best instances
        for i in range(5):
            plt.plot([instances[param].iloc[i]], [0], 'co', markersize=(16-3*i))
            
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'tree-range-plots.pdf'),
            bbox_extra_artists=(lgd,), bbox_inches='tight')

    with open(os.path.join(output_dir, 'distributions.json'), 'w') as f:
        json.dump(distributions, f, indent=4, sort_keys=True)
    with open(os.path.join(output_dir, 'range-weights.json'), 'w') as f:
        json.dump(range_weights, f, indent=4, sort_keys=True)

