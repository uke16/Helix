"""Basic Calculator Module."""

# History storage
_history = []


def add(a, b):
    """Add two numbers."""
    result = a + b
    _history.append(f"add({a}, {b}) = {result}")
    return result


def subtract(a, b):
    """Subtract b from a."""
    result = a - b
    _history.append(f"subtract({a}, {b}) = {result}")
    return result


def multiply(a, b):
    """Multiply two numbers."""
    result = a * b
    _history.append(f"multiply({a}, {b}) = {result}")
    return result


def divide(a, b):
    """Divide a by b."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    result = a / b
    _history.append(f"divide({a}, {b}) = {result}")
    return result


def get_history():
    """Get calculation history."""
    return _history.copy()


def clear_history():
    """Clear calculation history."""
    _history.clear()
