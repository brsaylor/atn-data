#!/usr/bin/env python3

# Ben Saylor
# October 2015

import sys
import csv

from nodeconfig_generator import parseNodeConfig

def nodeConfigToParams(nodeConfig):
    """
    Given a node config string, return a dictionary with one key-value pair for
    each node-parameter pair, where the keys are named with the parameter name
    with the node ID appended.
    """
    nodes = parseNodeConfig(nodeConfig)
    params = {}
    for node in nodes:
        for key, value in node.items():
            if key == 'nodeId':
                continue
            params[key + str(node['nodeId'])] = value
    return params

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 extinctions_csv_to_arff.py " +
                "<relation-basename> " +
                "<extinctions1.classified.csv> [<extinctions2.classified.csv> ...]")
        sys.exit(1)

    relationBasename = sys.argv[1]
    csvFilenames = sys.argv[2:]

    # Open the first CSV to get the attribute names
    infile = open(csvFilenames[0])
    reader = csv.DictReader(infile)
    headerRow = reader.__next__()
    extinctionAttributes = sorted(
            [s for s in headerRow if s.startswith('extinction')])
    firstDataRow = reader.__next__()
    nodeConfigParams = nodeConfigToParams(firstDataRow['nodeConfig'])
    nodeAttributes = sorted(nodeConfigParams.keys())
    infile.close()

    attributes = nodeAttributes + extinctionAttributes

    outfile1 =  open(relationBasename + '-labeled.arff', 'w', newline='')
    outfile2 =  open(relationBasename + '-unlabeled.arff', 'w', newline='')

    outfile1.write('@relation ' + relationBasename + '-labeled\n\n')
    outfile2.write('@relation ' + relationBasename + '-unlabeled\n\n')
    for f in (outfile1, outfile2):
        for attribute in attributes:
            f.write('@attribute ' + attribute + ' numeric\n')
        f.write('\n@attribute class {good,bad}\n')
        f.write('\n@data\n')

    outWriter1 = csv.DictWriter(
            outfile1, lineterminator='\n', fieldnames=(attributes + ['class']))
    outWriter2 = csv.DictWriter(
            outfile2, lineterminator='\n', fieldnames=(attributes + ['class']))

    for csvFilename in csvFilenames:
        infile = open(csvFilename)
        reader = csv.DictReader(infile)
        reader.__next__() # skip header row

        # Read the rows in the current input file, processing and routing each
        # one to one of the two output files (labeled or unlabeled).
        for inRow in reader:
            outRow = nodeConfigToParams(inRow['nodeConfig'])

            for attribute in extinctionAttributes:
                if inRow[attribute] is None:
                    outRow[attribute] = '?' # ARFF missing value marker
                else:
                    outRow[attribute] = inRow[attribute]

            if inRow['resultClass'] != '':
                # Write labeled data row to labeled file
                outRow['class'] = inRow['resultClass']
                outWriter1.writerow(outRow)
            else:
                # Write unlabeled data row to unlabeled file
                outRow['class'] = '?'
                outWriter2.writerow(outRow)

        infile.close()

    outfile1.close()
    outfile2.close()
