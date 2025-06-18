# Tests for firestore_module

import pytest
from src.firestore_module import SupabaseMDXManager

class DummyRoot:
    def __init__(self):
        self.title_called = False
        self.geometry_called = False
        self.minsize_called = False
    def title(self, _):
        self.title_called = True
    def geometry(self, _):
        self.geometry_called = True
    def minsize(self, *_):
        self.minsize_called = True

@pytest.fixture
def manager():
    # Patch out all methods that require GUI or Supabase
    root = DummyRoot()
    mgr = SupabaseMDXManager.__new__(SupabaseMDXManager)
    mgr.root = root
    return mgr

def test_placeholder():
    assert True

def test_format_file_size(manager):
    assert manager.format_file_size(0) == '0 B'
    assert manager.format_file_size(512) == '512.0 B'
    assert manager.format_file_size(2048) == '2.0 KB'
    assert manager.format_file_size(1048576) == '1.0 MB'

def test_format_date(manager):
    # ISO format
    assert manager.format_date('2024-06-18T12:34:56Z').startswith('2024-06-18')
    # Fallback
    assert manager.format_date('notadate') == 'notadate'
    assert manager.format_date('') == ''
