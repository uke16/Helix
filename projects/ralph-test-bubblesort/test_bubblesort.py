from bubblesort import bubble_sort


def test_empty_list():
    """Test sorting an empty list."""
    assert bubble_sort([]) == []


def test_already_sorted():
    """Test sorting an already sorted list."""
    assert bubble_sort([1, 2, 3, 4, 5]) == [1, 2, 3, 4, 5]


def test_unsorted_list():
    """Test sorting an unsorted list."""
    assert bubble_sort([5, 3, 8, 1, 2]) == [1, 2, 3, 5, 8]
