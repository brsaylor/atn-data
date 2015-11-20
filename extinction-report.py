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
    Cumulative biomass values include only biomass before extinction ,though
    the model may cause the species' biomass to recover from extinction
    
    IMPORTANT: Assumes all datasets have the same set of nodeIds
    """

    # The maximum number of extinctions seen in any dataset
    maxExtinctions = 0

    # The set of all nodeIds seen in any dataset
    nodeIds = set()

    dataset = []
    for filename in filenames:

        f = open(filename, 'r')
        reader = csv.reader(f)
        extinctionTimesteps = []
        cumulativeBiomassByNode = {} # Cumulative biomass by nodeID
        reader.__next__()  # Skip the header row

        numSpecies = 0
        for row in reader:
            if len(row) == 0 or row[0] == '':
                # Blank line: end of biomass data
                break
            numSpecies += 1
            cumulativeBiomass = 0
            for timestep, biomass in enumerate([int(float(x)) for x in row[1:]]):
                if biomass == 0:
                    extinctionTimesteps.append(timestep)
                    break
                cumulativeBiomass += biomass

            nodeId = int(row[0].split('.')[1])
            cumulativeBiomassByNode[nodeId] = cumulativeBiomass

        nodeIds.update(cumulativeBiomassByNode.keys())

        # The next row should have the node config
        row = reader.__next__()
        nodeConfig = row[0].split(': ')[1]

        f.close()
        extinctionTimesteps.sort()

        # Classify this simulation outcome as "bad" or "good" (or neither)
        # "bad": more than 60% extinct in < 20 time steps
        # "good": 2 or fewer extinctions by time step 400
        #  - i.e. the third extinction happens after time step 400

        USE_ORIGINAL_RULES = True

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

        # Count the number of species surviving at timestep 20
        surviving20 = numSpecies
        for timestep in extinctionTimesteps:
            if timestep > 20:
                break
            surviving20 -= 1

        # Count the number of species surviving at timestep 1000
        surviving1000 = numSpecies
        for timestep in extinctionTimesteps:
            if timestep > 1000:
                break
            surviving1000 -= 1

        # Padded extinctionTimestepts out to numSpecies elements
        for i in range(numSpecies - len(extinctionTimesteps)):
            extinctionTimesteps.append(99999999)

        maxExtinctions = max(maxExtinctions, len(extinctionTimesteps))
        avgBiomass = [b / 1000
                for nId, b in sorted(cumulativeBiomassByNode.items())]
        dataset.append([os.path.basename(filename), nodeConfig, resultClass] +
                extinctionTimesteps +
                [surviving20, surviving1000] +
                avgBiomass)

        # end for filename in filenames

    dataset.sort(reverse=True, key=lambda row: row[3:])
    return dataset, maxExtinctions, nodeIds

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 extinction-report.py file1.csv [file2.csv ...]")
        sys.exit(1)
    dataset, maxExtinctions, nodeIds = generateDataset(sys.argv[1:])
    writer = csv.writer(sys.stdout)
    writer.writerow(['filename', 'nodeConfig', 'resultClass'] +
            ['extinction' + str(i) for i in range(1, maxExtinctions + 1)] +
            ['surviving20', 'surviving1000'] +
            ['avgBiomass' + str(nodeId) for nodeId in sorted(nodeIds)])
    writer.writerows(dataset)
