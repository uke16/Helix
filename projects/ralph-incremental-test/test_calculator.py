"""Tests for calculator module."""

from calculator import add, subtract, multiply, divide, get_history, clear_history


def test_add():
    """Test add function."""
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0


def test_subtract():
    """Test subtract function."""
    assert subtract(5, 3) == 2
    assert subtract(1, 1) == 0
    assert subtract(0, 5) == -5


def test_multiply():
    """Test multiply function."""
    assert multiply(2, 3) == 6
    assert multiply(-1, 5) == -5
    assert multiply(0, 10) == 0


def test_divide():
    """Test divide function."""
    assert divide(6, 2) == 3
    assert divide(5, 2) == 2.5
    assert divide(0, 5) == 0


def test_history():
    """Test history feature."""
    clear_history()
    add(1, 2)
    subtract(5, 3)
    history = get_history()
    assert len(history) == 2
    assert "add(1, 2) = 3" in history[0]
    assert "subtract(5, 3) = 2" in history[1]
