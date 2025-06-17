"""Simple test to verify pytest is working correctly."""

def test_addition():
    """Test basic addition."""
    assert 1 + 1 == 2

def test_string_concatenation():
    """Test string concatenation."""
    assert "hello" + " " + "world" == "hello world"

def test_list_operations():
    """Test list operations."""
    my_list = [1, 2, 3]
    my_list.append(4)
    assert my_list == [1, 2, 3, 4]
    assert len(my_list) == 4

def test_dictionary_operations():
    """Test dictionary operations."""
    my_dict = {"key": "value"}
    my_dict["new_key"] = "new_value"
    assert "new_key" in my_dict
    assert my_dict["new_key"] == "new_value"