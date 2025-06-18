# Tests for supabase_module

def test_placeholder():
    assert True

import pytest
from src.supabase_module import is_supabase_url

def test_is_supabase_url():
    assert is_supabase_url('https://xyzcompany.supabase.co')
    assert not is_supabase_url('http://example.com')
    assert not is_supabase_url('https://example.com')
