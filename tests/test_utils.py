# Tests for utils

def test_placeholder():
    assert True

import pytest
from src.utils import add

def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0
