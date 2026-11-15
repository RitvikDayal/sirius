from sirius.calib.session import View, is_novel


def test_first_view_is_novel():
    assert is_novel(View((640, 360), 50_000), [])


def test_same_place_same_size_is_not_novel():
    assert not is_novel(View((650, 365), 52_000), [View((640, 360), 50_000)])


def test_moved_or_resized_is_novel():
    saved = [View((640, 360), 50_000)]
    assert is_novel(View((740, 360), 50_000), saved)  # moved 100 px
    assert is_novel(View((640, 360), 65_000), saved)  # 30% bigger (closer)
