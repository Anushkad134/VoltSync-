import pytest
from smoke_test import run_smoke_test

def test_full_system_smoke():
    """Executes the comprehensive 7-step smoke test suite."""
    success = run_smoke_test()
    assert success is True
