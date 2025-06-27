import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_read_root():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "status" in data
    assert data["status"] == "running"


def test_health_check():
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "FastAPI"


def test_get_items_empty():
    """Test getting items when none exist"""
    response = client.get("/items")
    assert response.status_code == 200
    assert response.json() == []


def test_create_item():
    """Test creating a new item"""
    item_data = {
        "name": "Test Item",
        "price": 29.99,
        "description": "A test item"
    }
    response = client.post("/items", json=item_data)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Item created successfully"
    assert data["item"]["name"] == item_data["name"]
    assert data["item"]["price"] == item_data["price"]
    assert data["item"]["id"] is not None


def test_get_item():
    """Test getting a specific item"""
    # First create an item
    item_data = {
        "name": "Test Item",
        "price": 29.99,
        "description": "A test item"
    }
    create_response = client.post("/items", json=item_data)
    created_item = create_response.json()["item"]
    
    # Then get the item
    response = client.get(f"/items/{created_item['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == item_data["name"]
    assert data["price"] == item_data["price"]


def test_get_item_not_found():
    """Test getting a non-existent item"""
    response = client.get("/items/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"


def test_update_item():
    """Test updating an existing item"""
    # First create an item
    item_data = {
        "name": "Original Item",
        "price": 29.99,
        "description": "Original description"
    }
    create_response = client.post("/items", json=item_data)
    created_item = create_response.json()["item"]
    
    # Then update the item
    update_data = {
        "name": "Updated Item",
        "price": 39.99,
        "description": "Updated description"
    }
    response = client.put(f"/items/{created_item['id']}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Item updated successfully"
    assert data["item"]["name"] == update_data["name"]
    assert data["item"]["price"] == update_data["price"]


def test_delete_item():
    """Test deleting an item"""
    # First create an item
    item_data = {
        "name": "Item to Delete",
        "price": 19.99,
        "description": "This item will be deleted"
    }
    create_response = client.post("/items", json=item_data)
    created_item = create_response.json()["item"]
    
    # Then delete the item
    response = client.delete(f"/items/{created_item['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Item deleted successfully"
    assert data["deleted_item"]["name"] == item_data["name"]
    
    # Verify the item is deleted
    get_response = client.get(f"/items/{created_item['id']}")
    assert get_response.status_code == 404


def test_delete_item_not_found():
    """Test deleting a non-existent item"""
    response = client.delete("/items/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"


if __name__ == "__main__":
    pytest.main([__file__]) 