#!/usr/bin/env python3

# Ben Saylor
# October 2015

import sys
import os.path
import csv

def generateDataset(filenames):
    """
    Return the a dataset with one row per input file (ATN biomass CSV file).
    Each row describes the timesteps of extinction events.
    The first two elements are the filename and the node config given in the file.
    The third is a classification of the result as clearly "good" or "bad" based
    on the following criteria:
    "bad": more than 60% extinct in < 20 time steps
    "good": 2 or fewer extinctions by time step 400
      - i.e. the third extinction happens after time step 400

    Extinction is defined as biomass == 0.
    """

    # The maximum number of extinctions seen in any dataset
    maxExtinctions = 0

    dataset = []
    for filename in filenames:

        f = open(filename, 'r')
        reader = csv.reader(f)
        extinctionTimesteps = []
        reader.__next__()  # Skip the header row

        numSpecies = 0
        for row in reader:
            if len(row) == 0 or row[0] == '':
                # Blank line: end of biomass data
                break
            numSpecies += 1
            for timestep, biomass in enumerate([int(float(x)) for x in row[1:]]):
                if biomass == 0:
                    extinctionTimesteps.append(timestep)
                    break

        # The next row should have the node config
        row = reader.__next__()
        nodeConfig = row[0].split(': ')[1]

        f.close()
        extinctionTimesteps.sort()

        # Classify this simulation outcome as "bad" or "good" (or neither)
        # "bad": more than 60% extinct in < 20 time steps
        # "good": 2 or fewer extinctions by time step 400
        #  - i.e. the third extinction happens after time step 400

        USE_ORIGINAL_RULES = False

        if USE_ORIGINAL_RULES:
            if len(extinctionTimesteps) <= 2:
                # Only two extinctions = good
                resultClass = 'good'
            else:
                resultClass = ''
                for i, timestep in enumerate(extinctionTimesteps):
                    numExtinct = (i + 1)
                    percentExtinct = numExtinct / numSpecies
                    if timestep < 20 and percentExtinct > 0.6:
                        resultClass = 'bad'
                        break
                    elif timestep > 400 and numExtinct == 3:
                        resultClass = 'good'
                        break
        else:
            # Updated version of rules to get useful labels for 11-species data
            # If there were fewer than 11 extinctions, then label the case
            # "good". Otherwise, look at the last extinction timestep:
            # > 100 => good; < 6 => bad.
            if len(extinctionTimesteps) < 11:
                resultClass = 'good'
            else:
                resultClass = ''
                timestep = extinctionTimesteps[-1]
                if timestep > 100:
                    resultClass = 'good'
                elif timestep < 6:
                    resultClass = 'bad'

        maxExtinctions = max(maxExtinctions, len(extinctionTimesteps))
        dataset.append([os.path.basename(filename), nodeConfig, resultClass] +
                extinctionTimesteps)
    dataset.sort(reverse=True, key=lambda row: row[3:])
    return dataset, maxExtinctions

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 extinction-report.py file1.csv [file2.csv ...]")
        sys.exit(1)
    dataset, maxExtinctions = generateDataset(sys.argv[1:])
    writer = csv.writer(sys.stdout)
    writer.writerow(['filename', 'nodeConfig', 'resultClass'] +
            ['extinction' + str(i) for i in range(1, maxExtinctions + 1)])
    writer.writerows(dataset)
