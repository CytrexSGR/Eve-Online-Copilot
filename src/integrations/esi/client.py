"""ESI API Client for EVE Online."""

from typing import List, Dict, Any
import requests
from requests.exceptions import RequestException, Timeout

from src.core.config import get_settings
from src.core.exceptions import ExternalAPIError


class ESIClient:
    """
    Client for interacting with EVE Online's ESI API.

    This client handles all direct API calls to ESI, including proper
    error handling, rate limiting awareness, and consistent response formatting.
    """

    def __init__(self):
        """
        Initialize ESI client with configuration from settings.

        Sets up a requests.Session with appropriate headers for ESI API calls.
        """
        settings = get_settings()
        self.base_url = settings.esi_base_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": settings.esi_user_agent,
            "Accept": "application/json"
        })

    def get_market_prices(self) -> List[Dict[str, Any]]:
        """
        Fetch global market prices from ESI.

        This endpoint returns adjusted and average prices for all tradeable items
        in EVE Online. Typically returns ~15,000+ items.

        Returns:
            List[Dict[str, Any]]: List of market price data with structure:
                [
                    {
                        "type_id": int,
                        "adjusted_price": float,
                        "average_price": float  # Optional, may be missing
                    },
                    ...
                ]

        Raises:
            ExternalAPIError: If the API request fails, times out, or returns
                an error status code.

        Example:
            >>> client = ESIClient()
            >>> prices = client.get_market_prices()
            >>> print(f"Fetched {len(prices)} market prices")
            Fetched 15234 market prices
        """
        url = f"{self.base_url}/markets/prices/"

        try:
            response = self.session.get(
                url,
                params={"datasource": "tranquility"},
                timeout=60
            )

            if response.status_code != 200:
                raise ExternalAPIError(
                    service_name="ESI",
                    status_code=response.status_code,
                    message=f"Failed to fetch market prices: {response.text}"
                )

            try:
                return response.json()
            except ValueError as e:
                raise ExternalAPIError(
                    service_name="ESI",
                    status_code=response.status_code,
                    message=f"Invalid JSON response: {str(e)}"
                )

        except Timeout as e:
            raise ExternalAPIError(
                service_name="ESI",
                status_code=0,
                message=f"Request timeout: {str(e)}"
            )
        except RequestException as e:
            raise ExternalAPIError(
                service_name="ESI",
                status_code=0,
                message=f"Request failed: {str(e)}"
            )
        except ExternalAPIError:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            # Catch any other unexpected errors
            raise ExternalAPIError(
                service_name="ESI",
                status_code=0,
                message=f"Unexpected error: {str(e)}"
            )

    def get(self, endpoint: str, timeout: int = 30) -> List[Dict[str, Any]]:
        """
        Generic GET request to ESI API.

        Args:
            endpoint: API endpoint path (e.g., "/sovereignty/campaigns/")
            timeout: Request timeout in seconds (default: 30)

        Returns:
            List[Dict[str, Any]]: JSON response from ESI

        Raises:
            ExternalAPIError: If the API request fails

        Example:
            >>> client = ESIClient()
            >>> campaigns = client.get("/sovereignty/campaigns/")
            >>> print(f"Fetched {len(campaigns)} campaigns")
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.get(
                url,
                params={"datasource": "tranquility"},
                timeout=timeout
            )

            if response.status_code != 200:
                raise ExternalAPIError(
                    service_name="ESI",
                    status_code=response.status_code,
                    message=f"Failed to fetch {endpoint}: {response.text}"
                )

            try:
                return response.json()
            except ValueError as e:
                raise ExternalAPIError(
                    service_name="ESI",
                    status_code=response.status_code,
                    message=f"Invalid JSON response: {str(e)}"
                )

        except Timeout as e:
            raise ExternalAPIError(
                service_name="ESI",
                status_code=0,
                message=f"Request timeout: {str(e)}"
            )
        except RequestException as e:
            raise ExternalAPIError(
                service_name="ESI",
                status_code=0,
                message=f"Request failed: {str(e)}"
            )
        except ExternalAPIError:
            raise
        except Exception as e:
            raise ExternalAPIError(
                service_name="ESI",
                status_code=0,
                message=f"Unexpected error: {str(e)}"
            )
