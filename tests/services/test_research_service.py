import pytest
from services.research_service import ResearchService

@pytest.fixture
def research_service():
    return ResearchService()

def test_get_skills_for_item():
    """Should return required skills for manufacturing an item"""
    service = ResearchService()

    # Thorax (typeID 645) requires various skills
    result = service.get_skills_for_item(645)

    assert 'required_skills' in result
    assert isinstance(result['required_skills'], list)
    assert len(result['required_skills']) > 0

def test_get_skills_for_character():
    """Should compare required skills with character's current skills"""
    service = ResearchService()
    character_id = 526379435  # Artallus

    result = service.get_skills_for_item(645, character_id=character_id)

    assert 'required_skills' in result
    for skill in result['required_skills']:
        assert 'skill_id' in skill
        assert 'skill_name' in skill
        assert 'required_level' in skill
        assert 'character_level' in skill
        assert 'training_time_seconds' in skill
