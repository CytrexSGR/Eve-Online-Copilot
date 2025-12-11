import pytest
from unittest.mock import Mock, patch
from services.portfolio_service import PortfolioService

@pytest.fixture
def portfolio_service():
    return PortfolioService()

@pytest.fixture
def character_ids():
    return [526379435, 1117367444, 110592475]  # Artallus, Cytrex, Cytricia

def test_get_character_summaries(portfolio_service, character_ids):
    """Should return summary for all characters"""
    with patch('services.portfolio_service.character') as mock_char:
        mock_char.get_character_wallet.return_value = 250000000
        mock_char.get_character_location.return_value = {'system_id': 30001365}
        mock_char.get_character_industry_jobs.return_value = []
        mock_char.get_character_skillqueue.return_value = []

        result = portfolio_service.get_character_summaries(character_ids)

        assert len(result) == 3
        assert all('character_id' in char for char in result)
        assert all('isk_balance' in char for char in result)

def test_get_total_portfolio_value(portfolio_service, character_ids):
    """Should calculate total ISK across all characters"""
    with patch('services.portfolio_service.character') as mock_char:
        mock_char.get_character_wallet.side_effect = [250000000, 180000000, 95000000]

        result = portfolio_service.get_total_portfolio_value(character_ids)

        assert result == 525000000
