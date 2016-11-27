import os
import json
import copy

import pytest

from atntools import settings
from atntools.util import *


# Directories to populate fake DATA_HOME for testing
directories = [
    '5-species/1-2-3-4-5/set-0',
    '5-species/1-2-3-4-5/set-1',
    '6-species/1-2-3-4-5-6/set-2',
    '6-species/1-2-3-4-5-6/set-3',
]

# Files to populate fake DATA_HOME (tuples of name, contents)
files = [
    ('5-species/1-2-3-4-5/food-web.json', '{"node_ids": [1, 2, 3, 4, 5]}'),
]

@pytest.fixture()
def fake_data_home(monkeypatch, tmpdir):
    for directory in directories:
        os.makedirs(os.path.join(str(tmpdir), directory))
    for file, contents in files:
        with open(os.path.join(str(tmpdir), file), 'w') as f:
            f.write(contents)

    monkeypatch.setattr(settings, 'DATA_HOME', str(tmpdir))


def test_get_food_web_dir(fake_data_home):
    assert get_food_web_dir([1, 2, 3, 4, 5]) == os.path.join(settings.DATA_HOME, '5-species/1-2-3-4-5')
    assert get_food_web_dir('1-2-3-4-5') == os.path.join(settings.DATA_HOME, '5-species/1-2-3-4-5')
    with pytest.raises(TypeError):
        get_food_web_dir(1)


def test_list_set_dirs(fake_data_home):
    assert sorted(list_set_dirs()) == list(enumerate(os.path.join(settings.DATA_HOME, d) for d in directories))


def test_find_set_dir(fake_data_home):
    assert find_set_dir(2) == os.path.join(settings.DATA_HOME, '6-species/1-2-3-4-5-6/set-2')
    assert find_set_dir(999) is None


def test_get_max_set_number(fake_data_home):
    assert get_max_set_number() == 3


def test_create_set_dir(fake_data_home):
    metaparameter_template = {
        "generator": "parallel_sweep",
        "args": {
            "param_ranges": {
                "initialBiomass": 1000,
                "X": [0, 1],
                "R": 1,
                "K": 5000
            },
            "count": 1000
        }
    }

    # Test that correct set directory was created
    max_set_num = get_max_set_number()
    set_num, set_dir = create_set_dir([1, 2, 3, 4, 5], metaparameter_template)
    assert set_num == max_set_num + 1
    assert os.path.isdir(set_dir)

    # Test that metaparameter file was created correctly
    metaparameter_file = os.path.join(set_dir, 'metaparameters.json')
    assert os.path.isfile(metaparameter_file)
    with open(metaparameter_file) as f:
        metaparameters = json.load(f)
    assert metaparameters == {
        "generator": "parallel_sweep",
        "args": {
            "node_ids": [1, 2, 3, 4, 5],
            "param_ranges": {
                "initialBiomass": 1000,
                "X": [0, 1],
                "R": 1,
                "K": 5000
            },
            "count": 1000
        }
    }
