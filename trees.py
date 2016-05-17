#!/usr/bin/env python3

"""
Classes and functions for working with decision trees

For now, these deal with parsing and representing Weka's J48 decision tree.
"""

import sys
import re

class TreeNode(object):
    """
    Decision tree node.

    Attributes represent all of the information from Weka's J48 decision tree.
    """

    def __init__(self):
        self.parent = None
        self.split_attribute = None
        self.split_value = None
        self.child_lte = None
        self.child_gt = None
        self.class_label = None
        self.instance_count = None
        self.misclassified_count = None

    @property
    def is_leaf(self):
        return self.child_lte is None and self.child_gt is None

    def __str__(self):
        return self.to_string()

    def to_string(self, indent=0):
        """
        Return a string representation of this subtree.

        The format is identical to Weka's J48 output.
        
        Parameters
        ----------
        indent : int, optional
            Number of levels to indent this subtree.

        Returns
        -------
        str
            String diagram of this subtree.
        """

        if self.is_leaf:
            # print leaf
            if self.misclassified_count > 0:
                string = ("{0.class_label} ({0.instance_count}/{0.misclassified_count})"
                        .format(self))
            else:
                string = ("{0.class_label} ({0.instance_count})".format(self))

        else:
            # print first line of this node
            string = ('|  ' * indent +
                    "{0.split_attribute} <= {0.split_value}".format(self))

            # print <= child
            if self.child_lte.is_leaf:
                string += ": " + self.child_lte.to_string()
            else:
                string += "\n" + self.child_lte.to_string(indent + 1)

            # print matching line of this node
            string += "\n" + ("|  " * indent +
                    "{0.split_attribute} > {0.split_value}".format(self))

            # print > child
            if self.child_gt.is_leaf:
                string += ": " + self.child_gt.to_string()
            else:
                string += "\n" + self.child_gt.to_string(indent + 1)

        return string

def parse_weka_j48_output(lines, parent=None):
    """
    Parse the output of Weka's J48 classifier.

    Parameters
    ----------
    lines : iterable object
        List of lines of text from the portion of Weka's output.
    parent : TreeNode, optional
        Parent node of the subtree described by `lines`.

    Returns
    -------
    TreeNode
        Root node of parsed decision tree.
    """

    # The first line looks like:
    # indentation split_attribute <= split_value
    # OR
    # indentation split_attribute <= split_value: class_label (instance_count/misclassified_count)
    # where indentation is '|   ' repeated <indentation_level> times.
    #
    # The matching line (referring to the same node) has the same indentation
    # level, may occur anywhere below the first line, and looks like
    # indentation split_attribute > split_value
    # OR
    # indentation split_attribute > split_value: class_label (instance_count/misclassified_count)
    #
    # If the first line does not have a : followed by more tokens,
    # - the lines between the first line and the matching line describe the
    #   child_lte subtree.
    # Else, the portion after the : describes a leaf.
    #
    # If the matching line does not have a : followed by more tokens,
    # - the lines after the matching line describe the child_gt subtree.
    # Else, the portion after the : describes a leaf.
    
    indentation_width = re.match(r'(\|   )*', lines[0]).end()
    first_line = lines[0][indentation_width:]

    matching_line = None
    matching_line_index = None
    for i, line in enumerate(lines[1:], 1):
        if line[indentation_width] not in ('|', ' '):
            # found the matching line
            matching_line_index = i
            matching_line = line[indentation_width:]
            break

    node = TreeNode()
    node.parent = parent

    for line in (first_line, matching_line):
        tokens = re.split(r' |: ', line)

        if line is first_line:
            node.split_attribute = tokens[0]
            node.split_value = float(tokens[2])

        if len(tokens) > 3:
            # current line has a leaf
            leaf = TreeNode()
            leaf.parent = node
            leaf.class_label = tokens[3]
            leaf_instance_info = tokens[4][1:-1].split('/')
            leaf.instance_count = float(leaf_instance_info[0])
            if len(leaf_instance_info) == 2:
                leaf.misclassified_count = float(leaf_instance_info[1])
            else:
                leaf.misclassified_count = 0.0
            if line is first_line:
                node.child_lte = leaf
            else:
                node.child_gt = leaf

        else:
            # current line does not have a leaf
            if line is first_line:
                node.child_lte = parse_weka_j48_output(
                        lines[1:matching_line_index],
                        parent=node)
            else:
                node.child_gt = parse_weka_j48_output(
                        lines[matching_line_index+1:],
                        parent=node)

    return node

def parse_weka_j48_output_file(filename):
    """
    Parse an output file from Weka's J48 classifier.

    Parameters
    ----------
    filename : str
        Output filename

    Returns
    -------
    TreeNode
        Root node of parsed decision tree.
    """

    tree_lines = []
    with open(filename) as f:
        for line in f:
            if line.startswith('J48'):
                f.__next__() # skip ------- line
                f.__next__() # skip blank line
                break
        for line in f:
            line = line.strip()
            if line == '':
                # end of tree lines
                break
            tree_lines.append(line)

    return parse_weka_j48_output(tree_lines)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Run this script to test parsing. Output should match input.")
        print("Usage: ./trees.py weka-J48-output-file.txt")
        sys.exit(1)
    print(str(parse_weka_j48_output_file(sys.argv[1])))
