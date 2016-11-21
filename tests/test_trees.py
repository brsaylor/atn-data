import os.path

import pytest

from atntools.trees import *


@pytest.fixture()
def tree_lines():
    """ Decision tree section of Weka J48 output file """
    return get_weka_j48_tree_lines(os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'files/weka-j48-training-output.txt'))


def test_parse_weka_j48_output(tree_lines):
    tree = parse_weka_j48_output(tree_lines)
    assert str(tree) == '\n'.join(tree_lines)
