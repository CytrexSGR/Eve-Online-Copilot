import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app

client = TestClient(app)


def test_get_skills_for_item_returns_success():
    """Should return skills required for manufacturing an item"""
    with patch('routers.research.research_service.get_skills_for_item') as mock_get_skills:
        # Mock the service response
        mock_get_skills.return_value = {
            'type_id': 645,
            'blueprint_id': 1234,
            'required_skills': [
                {
                    'skill_id': 3380,
                    'skill_name': 'Gallente Battleship',
                    'required_level': 1,
                    'character_level': 0,
                    'training_time_seconds': 25000
                }
            ]
        }

        response = client.get("/api/research/skills-for-item/645")
        assert response.status_code == 200

        data = response.json()
        assert data['type_id'] == 645
        assert data['blueprint_id'] == 1234
        assert 'required_skills' in data
        assert len(data['required_skills']) > 0


def test_get_skills_for_item_with_character():
    """Should include character comparison when character_id provided"""
    with patch('routers.research.research_service.get_skills_for_item') as mock_get_skills:
        mock_get_skills.return_value = {
            'type_id': 645,
            'blueprint_id': 1234,
            'required_skills': [
                {
                    'skill_id': 3380,
                    'skill_name': 'Gallente Battleship',
                    'required_level': 1,
                    'character_level': 3,
                    'training_time_seconds': 0
                }
            ]
        }

        response = client.get("/api/research/skills-for-item/645?character_id=1117367444")
        assert response.status_code == 200

        data = response.json()
        assert data['required_skills'][0]['character_level'] == 3

        # Verify service was called with character_id
        mock_get_skills.assert_called_once_with(645, 1117367444)


def test_get_skills_for_item_not_found():
    """Should return 404 when blueprint not found for item"""
    with patch('routers.research.research_service.get_skills_for_item') as mock_get_skills:
        # Mock service returning error
        mock_get_skills.return_value = {
            'required_skills': [],
            'error': 'No blueprint found'
        }

        response = client.get("/api/research/skills-for-item/99999")
        assert response.status_code == 404

        data = response.json()
        assert 'detail' in data


def test_get_skills_for_item_structure():
    """Each skill should have required fields"""
    with patch('routers.research.research_service.get_skills_for_item') as mock_get_skills:
        mock_get_skills.return_value = {
            'type_id': 645,
            'blueprint_id': 1234,
            'required_skills': [
                {
                    'skill_id': 3380,
                    'skill_name': 'Gallente Battleship',
                    'required_level': 1,
                    'character_level': 0,
                    'training_time_seconds': 25000
                }
            ]
        }

        response = client.get("/api/research/skills-for-item/645")
        assert response.status_code == 200

        data = response.json()
        if len(data['required_skills']) > 0:
            skill = data['required_skills'][0]
            assert 'skill_id' in skill
            assert 'skill_name' in skill
            assert 'required_level' in skill
            assert 'character_level' in skill
            assert 'training_time_seconds' in skill


def test_get_training_recommendations_returns_list():
    """Should return list of recommended skills for character"""
    with patch('routers.research.research_service.get_skill_recommendations') as mock_get_recs:
        # Mock the service response
        mock_get_recs.return_value = [
            {
                'skill_id': 3380,
                'skill_name': 'Gallente Battleship',
                'current_level': 3,
                'recommended_level': 5,
                'priority': 'high',
                'reason': 'Required for multiple production blueprints'
            }
        ]

        response = client.get("/api/research/recommendations/1117367444")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)


def test_get_training_recommendations_empty():
    """Should handle case when no recommendations available"""
    with patch('routers.research.research_service.get_skill_recommendations') as mock_get_recs:
        mock_get_recs.return_value = []

        response = client.get("/api/research/recommendations/1117367444")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


def test_get_training_recommendations_structure():
    """Each recommendation should have required fields"""
    with patch('routers.research.research_service.get_skill_recommendations') as mock_get_recs:
        mock_get_recs.return_value = [
            {
                'skill_id': 3380,
                'skill_name': 'Gallente Battleship',
                'current_level': 3,
                'recommended_level': 5,
                'priority': 'high',
                'reason': 'Required for multiple production blueprints'
            }
        ]

        response = client.get("/api/research/recommendations/1117367444")
        assert response.status_code == 200

        data = response.json()
        if len(data) > 0:
            rec = data[0]
            assert 'skill_id' in rec
            assert 'skill_name' in rec
