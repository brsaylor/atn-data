import os

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


@pytest.fixture()
def fake_data_home(monkeypatch, tmpdir):
    for directory in directories:
        os.makedirs(os.path.join(str(tmpdir), directory))
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