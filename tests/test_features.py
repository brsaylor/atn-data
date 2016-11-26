from atntools.features import *


def test_get_sim_number():
    assert get_sim_number('ATN.h5') == 0
    assert get_sim_number('ATN_1.h5') == 1
    assert get_sim_number('ATN_123.h5') == 123
    assert get_sim_number('WoB_Data.csv') == 0
    assert get_sim_number('WoB_Data_1.csv') == 1
    assert get_sim_number('WoB_Data_123.csv') == 123
    assert get_sim_number('one.two.three_123.csv') == 123
