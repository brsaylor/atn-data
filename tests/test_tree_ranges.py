from atntools.tree_ranges import *


def test_combine_weighted_segments():

    # disjoint segments:
    # -- --
    in_segments =  [(1, 2, 3), (3, 4, 2)]
    out_segments = [(1, 2, 3), (2, 3, 0), (3, 4, 2)]
    assert combine_weighted_segments(in_segments) == out_segments

    # adjoining segments:
    # ----
    in_segments =  [(1, 2, 3), (2, 3, 2)]
    out_segments = [(1, 2, 3), (2, 3, 2)]
    assert combine_weighted_segments(in_segments) == out_segments

    # simple overlap:
    # ---
    #  ---
    in_segments =  [(1, 3, 3), (2, 4, 2)]
    out_segments = [(1, 2, 3), (2, 3, 5), (3, 4, 2)]
    assert combine_weighted_segments(in_segments) == out_segments

    # identical endpoints:
    # ---
    # ---
    in_segments =  [(1, 3, 1), (1, 3, 2)]
    out_segments = [(1, 3, 3)]
    assert combine_weighted_segments(in_segments) == out_segments

    # same segment overlapping on both ends:
    # ----
    #  --
    in_segments =  [(1, 4, 1), (2, 3, 2)]
    out_segments = [(1, 2, 1), (2, 3, 3), (3, 4, 1)]
    assert combine_weighted_segments(in_segments) == out_segments

    # 3-segment overlap:
    # 12345
    # ---
    #  ---
    #   ---
    in_segments =  [(1, 4, 1), (2, 5, 2), (3, 6, 3)]
    out_segments = [(1, 2, 1), (2, 3, 3), (3, 4, 6), (4, 5, 5), (5, 6, 3)]
    assert combine_weighted_segments(in_segments) == out_segments
