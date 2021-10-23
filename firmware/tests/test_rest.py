from rest.util import convert_vals


def test_convert_int():
    assert convert_vals("19887") == 19887
    assert convert_vals("0") == 0
    assert convert_vals("-10") == -10


def test_convert_float():
    assert convert_vals("1.5") == 1.5
    assert convert_vals("-0.1") == -0.1
    assert convert_vals("5e6") == 5e6


def test_convert_bool():
    assert convert_vals("true")
    assert not convert_vals("false")
    assert convert_vals("tRuE")
    assert not convert_vals("fAlSe")


def test_convert_list():
    assert convert_vals("1,1.5,True,false,cheese") == [1, 1.5, True, False, "cheese"]
