"""
API Proxy Helper for MCP Tools
Provides utilities for making requests to the FastAPI backend.
"""

import requests
import traceback
from typing import Any, Dict, Optional


class APIProxy:
    """Helper class for proxying MCP tool calls to FastAPI endpoints."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make GET request to API endpoint.

        Args:
            endpoint: API endpoint path (e.g., "/api/market/stats/10000002/34")
            params: Optional query parameters

        Returns:
            API response as dict with {"content": [...]} or {"error": "..."}
        """
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            return {"content": [{"type": "text", "text": str(data)}]}

        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}\n{traceback.format_exc()}"
            return {"error": error_msg, "isError": True}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
            return {"error": error_msg, "isError": True}

    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make POST request to API endpoint.

        Args:
            endpoint: API endpoint path
            data: Optional request body
            params: Optional query parameters

        Returns:
            API response as dict with {"content": [...]} or {"error": "..."}
        """
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.post(url, json=data, params=params, timeout=30)
            response.raise_for_status()

            result = response.json()
            return {"content": [{"type": "text", "text": str(result)}]}

        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}\n{traceback.format_exc()}"
            return {"error": error_msg, "isError": True}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
            return {"error": error_msg, "isError": True}

    def patch(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make PATCH request to API endpoint.

        Args:
            endpoint: API endpoint path
            data: Optional request body

        Returns:
            API response as dict with {"content": [...]} or {"error": "..."}
        """
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.patch(url, json=data, timeout=30)
            response.raise_for_status()

            result = response.json()
            return {"content": [{"type": "text", "text": str(result)}]}

        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}\n{traceback.format_exc()}"
            return {"error": error_msg, "isError": True}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
            return {"error": error_msg, "isError": True}

    def delete(self, endpoint: str) -> Dict[str, Any]:
        """
        Make DELETE request to API endpoint.

        Args:
            endpoint: API endpoint path

        Returns:
            API response as dict with {"content": [...]} or {"error": "..."}
        """
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.delete(url, timeout=30)
            response.raise_for_status()

            result = response.json()
            return {"content": [{"type": "text", "text": str(result)}]}

        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}\n{traceback.format_exc()}"
            return {"error": error_msg, "isError": True}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
            return {"error": error_msg, "isError": True}


# Global instance
api_proxy = APIProxy()
