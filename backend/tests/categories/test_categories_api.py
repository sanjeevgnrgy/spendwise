"""HTTP tests for the categories module: real requests through TestClient, in-memory database."""


def test_list_categories_is_empty_on_a_new_database(client):
    response = client.get("/categories")

    assert response.status_code == 200
    assert response.json() == []


def test_list_categories_returns_every_category(client, food, travel):
    response = client.get("/categories")

    assert response.status_code == 200
    assert response.json() == [
        {"id": food.id, "name": "Food", "icon": "utensils"},
        {"id": travel.id, "name": "Travel", "icon": "plane"},
    ]
