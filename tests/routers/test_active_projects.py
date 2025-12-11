"""
Tests for Active Projects Endpoint
GET /api/dashboard/projects

Requirements:
- Return shopping lists with item counts
- Include total_items and checked_items
- Calculate progress percentage
- Return: id, name, total_items, checked_items, progress
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_get_active_projects_returns_list():
    """Should return a list of active projects (shopping lists)"""
    response = client.get("/api/dashboard/projects")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)


def test_active_project_structure():
    """Each project should have required fields with correct types"""
    response = client.get("/api/dashboard/projects")
    assert response.status_code == 200

    data = response.json()

    # If there are projects, verify structure
    if len(data) > 0:
        project = data[0]

        # Required fields
        assert 'id' in project
        assert 'name' in project
        assert 'total_items' in project
        assert 'checked_items' in project
        assert 'progress' in project

        # Type validation
        assert isinstance(project['id'], int)
        assert isinstance(project['name'], str)
        assert isinstance(project['total_items'], int)
        assert isinstance(project['checked_items'], int)
        assert isinstance(project['progress'], (int, float))

        # Progress should be percentage (0-100)
        assert 0 <= project['progress'] <= 100

        # checked_items should not exceed total_items
        assert project['checked_items'] <= project['total_items']


def test_active_project_progress_calculation():
    """Progress should be correctly calculated as percentage"""
    response = client.get("/api/dashboard/projects")
    assert response.status_code == 200

    data = response.json()

    for project in data:
        total = project['total_items']
        checked = project['checked_items']
        progress = project['progress']

        if total > 0:
            expected_progress = round((checked / total) * 100, 1)
            assert progress == expected_progress
        else:
            # Empty list should have 0% progress
            assert progress == 0
