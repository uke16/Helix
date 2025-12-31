def bubble_sort(arr: list) -> list:
    """Sort a list using the bubble sort algorithm.

    Args:
        arr: List to sort

    Returns:
        Sorted list (new list, original unchanged)
    """
    result = arr.copy()
    n = len(result)

    for i in range(n):
        for j in range(0, n - i - 1):
            if result[j] > result[j + 1]:
                result[j], result[j + 1] = result[j + 1], result[j]

    return result
