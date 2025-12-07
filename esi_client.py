"""
EVE Co-Pilot ESI Client Module
Handles all ESI API calls with rate limiting, caching, and error protection

Rate Limit Strategy:
- Monitor X-Ratelimit-Remaining (token system)
- Monitor X-ESI-Error-Limit-Remain (error limit system)
- Automatic throttling when limits approach
- ETag caching for static routes
- Emergency shutdown on HTTP 420
"""

import requests
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass, field
from config import ESI_BASE_URL, ESI_USER_AGENT, REGIONS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("esi_client")


@dataclass
class RateLimitState:
    """Track rate limit status across requests"""
    # Token-based limits (new system)
    token_limit: int = 0
    token_remaining: int = 0

    # Error-based limits (old system)
    error_limit_remain: int = 100
    error_limit_reset: int = 0

    # Request stats
    total_requests: int = 0
    successful_requests: int = 0
    cached_requests: int = 0
    error_requests: int = 0

    # Emergency state
    is_rate_limited: bool = False
    rate_limit_until: Optional[datetime] = None
    is_error_banned: bool = False

    def update_from_headers(self, headers: Dict[str, str]):
        """Update state from response headers"""
        # Token system
        if "X-Ratelimit-Limit" in headers:
            self.token_limit = int(headers["X-Ratelimit-Limit"])
        if "X-Ratelimit-Remaining" in headers:
            self.token_remaining = int(headers["X-Ratelimit-Remaining"])

        # Error limit system
        if "X-ESI-Error-Limit-Remain" in headers:
            self.error_limit_remain = int(headers["X-ESI-Error-Limit-Remain"])
        if "X-ESI-Error-Limit-Reset" in headers:
            self.error_limit_reset = int(headers["X-ESI-Error-Limit-Reset"])

    def get_summary(self) -> Dict:
        """Get current state as dict"""
        return {
            "token_limit": self.token_limit,
            "token_remaining": self.token_remaining,
            "error_limit_remain": self.error_limit_remain,
            "error_limit_reset": self.error_limit_reset,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "cached_requests": self.cached_requests,
            "error_requests": self.error_requests,
            "is_rate_limited": self.is_rate_limited,
            "is_error_banned": self.is_error_banned
        }


@dataclass
class ETagCache:
    """ETag cache entry"""
    etag: str
    data: Any
    expires: datetime


class ESIClient:
    """
    Robust ESI API Client with rate limiting and error protection.

    Features:
    - Automatic rate limit monitoring
    - ETag caching for static routes
    - Throttling on low tokens
    - Emergency shutdown on HTTP 420
    - Discord notifications for critical errors
    """

    # Minimum tokens before throttling
    TOKEN_THROTTLE_THRESHOLD = 50

    # Minimum error limit before stopping
    ERROR_LIMIT_THRESHOLD = 20

    # Base delay between requests (seconds)
    BASE_DELAY = 0.5

    # Delay when throttling (seconds)
    THROTTLE_DELAY = 3.0

    def __init__(self, notify_callback=None):
        """
        Initialize ESI client.

        Args:
            notify_callback: Optional function(message, is_critical) for notifications
        """
        self.base_url = ESI_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": ESI_USER_AGENT,
            "Accept": "application/json"
        })

        # Rate limit tracking
        self.rate_state = RateLimitState()

        # ETag cache
        self._etag_cache: Dict[str, ETagCache] = {}

        # Price cache (short-term)
        self._price_cache: Dict[str, Tuple[Any, datetime]] = {}
        self._cache_duration = timedelta(minutes=5)

        # Notification callback
        self._notify = notify_callback

        # Last request time for throttling
        self._last_request_time: float = 0

    def _send_notification(self, message: str, is_critical: bool = False):
        """Send notification via callback if configured"""
        level = "CRITICAL" if is_critical else "WARNING"
        logger.log(logging.CRITICAL if is_critical else logging.WARNING, message)

        if self._notify:
            try:
                self._notify(message, is_critical)
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")

    def _should_throttle(self) -> bool:
        """Check if we should throttle requests"""
        # Token-based throttling
        if self.rate_state.token_remaining > 0 and \
           self.rate_state.token_remaining < self.TOKEN_THROTTLE_THRESHOLD:
            return True

        # Error-based throttling
        if self.rate_state.error_limit_remain < self.ERROR_LIMIT_THRESHOLD:
            return True

        return False

    def _wait_if_needed(self):
        """Apply throttling delay if needed"""
        now = time.time()
        elapsed = now - self._last_request_time

        # Check if we're rate limited
        if self.rate_state.is_rate_limited:
            if self.rate_state.rate_limit_until and \
               datetime.now() < self.rate_state.rate_limit_until:
                wait_time = (self.rate_state.rate_limit_until - datetime.now()).total_seconds()
                logger.info(f"Rate limited, waiting {wait_time:.1f}s")
                time.sleep(wait_time)
                self.rate_state.is_rate_limited = False

        # Apply throttle delay if needed
        if self._should_throttle():
            delay = self.THROTTLE_DELAY
            if elapsed < delay:
                time.sleep(delay - elapsed)
        elif elapsed < self.BASE_DELAY:
            time.sleep(self.BASE_DELAY - elapsed)

        self._last_request_time = time.time()

    def _handle_response(self, response: requests.Response, endpoint: str) -> Tuple[bool, Optional[Any]]:
        """
        Process response and update rate limit state.

        Returns:
            (success, data) tuple
        """
        self.rate_state.total_requests += 1
        self.rate_state.update_from_headers(dict(response.headers))

        # Log rate limit status periodically
        if self.rate_state.total_requests % 10 == 0:
            logger.debug(f"Rate limits - Tokens: {self.rate_state.token_remaining}, "
                        f"Errors: {self.rate_state.error_limit_remain}")

        status = response.status_code

        # Success (2XX)
        if 200 <= status < 300:
            self.rate_state.successful_requests += 1

            # Update ETag cache if present
            if "ETag" in response.headers:
                etag = response.headers["ETag"]
                expires = datetime.now() + timedelta(hours=1)
                if "Expires" in response.headers:
                    try:
                        expires = datetime.strptime(
                            response.headers["Expires"],
                            "%a, %d %b %Y %H:%M:%S %Z"
                        )
                    except ValueError:
                        pass

                self._etag_cache[endpoint] = ETagCache(
                    etag=etag,
                    data=response.json(),
                    expires=expires
                )

            return True, response.json()

        # Not Modified (304) - use cached data
        if status == 304:
            self.rate_state.cached_requests += 1
            if endpoint in self._etag_cache:
                return True, self._etag_cache[endpoint].data
            return False, None

        # Rate Limited (429)
        if status == 429:
            self.rate_state.error_requests += 1
            self.rate_state.is_rate_limited = True

            retry_after = int(response.headers.get("Retry-After", 60))
            self.rate_state.rate_limit_until = datetime.now() + timedelta(seconds=retry_after)

            msg = f"ESI Rate Limited (429)! Waiting {retry_after}s. Endpoint: {endpoint}"
            self._send_notification(msg, is_critical=False)

            return False, {"error": "rate_limited", "retry_after": retry_after}

        # Error Banned (420)
        if status == 420:
            self.rate_state.error_requests += 1
            self.rate_state.is_error_banned = True

            msg = f"ESI ERROR BANNED (420)! All requests blocked. Endpoint: {endpoint}"
            self._send_notification(msg, is_critical=True)

            return False, {"error": "error_banned", "fatal": True}

        # Other errors (4XX, 5XX)
        if status >= 400:
            self.rate_state.error_requests += 1

            # Log warning if error limit getting low
            if self.rate_state.error_limit_remain < 30:
                msg = f"ESI Error {status} on {endpoint}. Error limit: {self.rate_state.error_limit_remain}"
                self._send_notification(msg, is_critical=False)

            return False, {"error": f"http_{status}", "details": response.text[:200]}

        return False, None

    def _get(
        self,
        endpoint: str,
        params: dict = None,
        use_etag: bool = False
    ) -> Optional[Any]:
        """
        Make GET request to ESI with rate limiting.

        Args:
            endpoint: API endpoint (e.g., "/markets/10000002/orders/")
            params: Query parameters
            use_etag: Use ETag caching for this request

        Returns:
            Response data or None on error
        """
        # Check if error banned
        if self.rate_state.is_error_banned:
            logger.error("ESI client is error banned, refusing request")
            return None

        # Apply throttling
        self._wait_if_needed()

        url = f"{self.base_url}{endpoint}"
        headers = {}

        # Add ETag if cached
        if use_etag and endpoint in self._etag_cache:
            cache_entry = self._etag_cache[endpoint]
            if datetime.now() < cache_entry.expires:
                headers["If-None-Match"] = cache_entry.etag

        try:
            response = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=30
            )

            success, data = self._handle_response(response, endpoint)

            if success:
                return data
            elif data and data.get("error") == "rate_limited":
                # Retry after waiting
                time.sleep(data.get("retry_after", 60))
                return self._get(endpoint, params, use_etag)

            return None

        except requests.Timeout:
            self.rate_state.error_requests += 1
            logger.warning(f"ESI timeout on {endpoint}")
            return None
        except requests.RequestException as e:
            self.rate_state.error_requests += 1
            logger.error(f"ESI request error: {e}")
            return None

    def get_market_orders(
        self,
        region_id: int,
        type_id: int,
        max_pages: int = 10
    ) -> List[Dict]:
        """
        Get all market orders for an item in a region.

        Args:
            region_id: Region ID (e.g., 10000002 for The Forge)
            type_id: Item type ID
            max_pages: Maximum pages to fetch (safety limit)

        Returns:
            List of order dicts
        """
        all_orders = []
        page = 1

        while page <= max_pages:
            params = {
                "datasource": "tranquility",
                "order_type": "all",
                "type_id": type_id,
                "page": page
            }

            orders = self._get(f"/markets/{region_id}/orders/", params)

            if not orders:
                break

            all_orders.extend(orders)

            # Check pagination
            if len(orders) < 1000:
                break
            page += 1

        return all_orders

    def get_lowest_sell_price(self, region_id: int, type_id: int) -> Optional[float]:
        """Get lowest sell price for an item (with caching)"""
        cache_key = f"sell_{region_id}_{type_id}"

        # Check cache
        if cache_key in self._price_cache:
            price, cached_at = self._price_cache[cache_key]
            if datetime.now() - cached_at < self._cache_duration:
                return price

        orders = self.get_market_orders(region_id, type_id)
        sell_orders = [o for o in orders if not o.get("is_buy_order", True)]

        if not sell_orders:
            return None

        lowest = min(o["price"] for o in sell_orders)

        # Cache result
        self._price_cache[cache_key] = (lowest, datetime.now())

        return lowest

    def get_highest_buy_price(self, region_id: int, type_id: int) -> Optional[float]:
        """Get highest buy price for an item (with caching)"""
        cache_key = f"buy_{region_id}_{type_id}"

        # Check cache
        if cache_key in self._price_cache:
            price, cached_at = self._price_cache[cache_key]
            if datetime.now() - cached_at < self._cache_duration:
                return price

        orders = self.get_market_orders(region_id, type_id)
        buy_orders = [o for o in orders if o.get("is_buy_order", False)]

        if not buy_orders:
            return None

        highest = max(o["price"] for o in buy_orders)

        # Cache result
        self._price_cache[cache_key] = (highest, datetime.now())

        return highest

    def get_market_depth(self, region_id: int, type_id: int) -> Dict:
        """
        Get market depth (volume available at price points) for an item.

        Returns detailed volume information for availability analysis.
        """
        orders = self.get_market_orders(region_id, type_id)

        if not orders:
            return {
                "type_id": type_id,
                "region_id": region_id,
                "sell_volume": 0,
                "buy_volume": 0,
                "lowest_sell_price": None,
                "lowest_sell_volume": 0,
                "highest_buy_price": None,
                "highest_buy_volume": 0,
                "sell_orders": 0,
                "buy_orders": 0
            }

        sell_orders = [o for o in orders if not o.get("is_buy_order", True)]
        buy_orders = [o for o in orders if o.get("is_buy_order", False)]

        # Sort by price
        sell_orders.sort(key=lambda x: x.get("price", float('inf')))
        buy_orders.sort(key=lambda x: x.get("price", 0), reverse=True)

        return {
            "type_id": type_id,
            "region_id": region_id,
            "sell_volume": sum(o.get("volume_remain", 0) for o in sell_orders),
            "buy_volume": sum(o.get("volume_remain", 0) for o in buy_orders),
            "lowest_sell_price": sell_orders[0]["price"] if sell_orders else None,
            "lowest_sell_volume": sell_orders[0]["volume_remain"] if sell_orders else 0,
            "highest_buy_price": buy_orders[0]["price"] if buy_orders else None,
            "highest_buy_volume": buy_orders[0]["volume_remain"] if buy_orders else 0,
            "sell_orders": len(sell_orders),
            "buy_orders": len(buy_orders)
        }

    def get_market_stats(self, region_id: int, type_id: int) -> Dict:
        """Get comprehensive market statistics for an item"""
        orders = self.get_market_orders(region_id, type_id)

        sell_orders = [o for o in orders if not o.get("is_buy_order", True)]
        buy_orders = [o for o in orders if o.get("is_buy_order", False)]

        stats = {
            "type_id": type_id,
            "region_id": region_id,
            "total_orders": len(orders),
            "sell_order_count": len(sell_orders),
            "buy_order_count": len(buy_orders),
        }

        if sell_orders:
            sell_prices = [o["price"] for o in sell_orders]
            sell_volumes = [o["volume_remain"] for o in sell_orders]
            stats["lowest_sell"] = min(sell_prices)
            stats["highest_sell"] = max(sell_prices)
            stats["avg_sell"] = sum(sell_prices) / len(sell_prices)
            stats["total_sell_volume"] = sum(sell_volumes)

        if buy_orders:
            buy_prices = [o["price"] for o in buy_orders]
            buy_volumes = [o["volume_remain"] for o in buy_orders]
            stats["highest_buy"] = max(buy_prices)
            stats["lowest_buy"] = min(buy_prices)
            stats["avg_buy"] = sum(buy_prices) / len(buy_prices)
            stats["total_buy_volume"] = sum(buy_volumes)

        if sell_orders and buy_orders:
            stats["spread"] = stats["lowest_sell"] - stats["highest_buy"]
            stats["spread_percent"] = (stats["spread"] / stats["highest_buy"]) * 100 if stats["highest_buy"] > 0 else 0

        return stats

    def get_type_info(self, type_id: int) -> Optional[Dict]:
        """Get type information (uses ETag caching)"""
        return self._get(f"/universe/types/{type_id}/", use_etag=True)

    def get_rate_limit_status(self) -> Dict:
        """Get current rate limit status"""
        return self.rate_state.get_summary()

    def is_safe_to_continue(self) -> bool:
        """Check if it's safe to continue making requests"""
        if self.rate_state.is_error_banned:
            return False

        if self.rate_state.error_limit_remain < 10:
            return False

        if self.rate_state.token_remaining > 0 and self.rate_state.token_remaining < 10:
            return False

        return True

    def clear_cache(self):
        """Clear all caches"""
        self._price_cache.clear()
        self._etag_cache.clear()

    def reset_rate_state(self):
        """Reset rate limit state (use after error ban expires)"""
        self.rate_state = RateLimitState()

    # ========== MULTI-REGION METHODS ==========

    def get_all_region_prices(self, type_id: int) -> Dict[str, Dict]:
        """
        Get prices for an item across all trade hubs.

        Returns:
            Dict with region names as keys containing buy/sell prices
        """
        results = {}

        for region_name, region_id in REGIONS.items():
            stats = self.get_market_stats(region_id, type_id)

            results[region_name] = {
                "region_id": region_id,
                "lowest_sell": stats.get("lowest_sell"),
                "highest_buy": stats.get("highest_buy"),
                "sell_volume": stats.get("total_sell_volume", 0),
                "buy_volume": stats.get("total_buy_volume", 0),
                "spread_percent": stats.get("spread_percent", 0)
            }

        return results

    def find_arbitrage_opportunities(
        self,
        type_id: int,
        min_profit_percent: float = 5.0
    ) -> List[Dict]:
        """
        Find arbitrage opportunities for an item between regions.
        Buy low in one hub, sell high in another.

        Args:
            type_id: Item type ID
            min_profit_percent: Minimum profit percentage to consider

        Returns:
            List of arbitrage opportunities sorted by profit
        """
        prices = self.get_all_region_prices(type_id)
        opportunities = []

        # Compare each region pair
        region_names = list(prices.keys())
        for i, buy_region in enumerate(region_names):
            buy_data = prices[buy_region]
            buy_price = buy_data.get("lowest_sell")

            if not buy_price:
                continue

            for sell_region in region_names[i+1:] + region_names[:i]:
                if sell_region == buy_region:
                    continue

                sell_data = prices[sell_region]
                sell_price = sell_data.get("highest_buy")

                if not sell_price:
                    continue

                # Calculate profit (selling to buy orders for instant sale)
                profit = sell_price - buy_price
                profit_percent = (profit / buy_price) * 100 if buy_price > 0 else 0

                if profit_percent >= min_profit_percent:
                    opportunities.append({
                        "type_id": type_id,
                        "buy_region": buy_region,
                        "buy_region_id": buy_data["region_id"],
                        "buy_price": buy_price,
                        "sell_region": sell_region,
                        "sell_region_id": sell_data["region_id"],
                        "sell_price": sell_price,
                        "profit_per_unit": profit,
                        "profit_percent": round(profit_percent, 2),
                        "buy_volume_available": buy_data["sell_volume"],
                        "sell_volume_demand": sell_data["buy_volume"]
                    })

        # Sort by profit percentage
        opportunities.sort(key=lambda x: x["profit_percent"], reverse=True)
        return opportunities

    def find_best_production_regions(
        self,
        product_type_id: int,
        material_type_ids: List[int]
    ) -> Dict:
        """
        Find the best regions for production.

        Args:
            product_type_id: The finished product type ID
            material_type_ids: List of material type IDs needed

        Returns:
            Dict with best buy region for materials, best sell region for product
        """
        # Get product prices across all regions
        product_prices = self.get_all_region_prices(product_type_id)

        # Find best sell region (highest buy price for instant sale)
        best_sell_region = None
        best_sell_price = 0

        for region_name, data in product_prices.items():
            sell_price = data.get("highest_buy", 0) or 0
            if sell_price > best_sell_price:
                best_sell_price = sell_price
                best_sell_region = region_name

        # Get material prices across all regions
        material_prices = {}
        for mat_id in material_type_ids:
            material_prices[mat_id] = self.get_all_region_prices(mat_id)

        # Calculate total material cost per region
        region_material_costs = {}
        for region_name in REGIONS.keys():
            total_cost = 0
            missing = False

            for mat_id in material_type_ids:
                price = material_prices[mat_id][region_name].get("lowest_sell")
                if price is None:
                    missing = True
                    break
                total_cost += price

            if not missing:
                region_material_costs[region_name] = total_cost

        # Find cheapest region for materials
        best_buy_region = None
        lowest_material_cost = float('inf')

        for region_name, cost in region_material_costs.items():
            if cost < lowest_material_cost:
                lowest_material_cost = cost
                best_buy_region = region_name

        return {
            "product_type_id": product_type_id,
            "best_sell_region": best_sell_region,
            "best_sell_region_id": REGIONS.get(best_sell_region),
            "best_sell_price": best_sell_price,
            "product_prices_all": product_prices,
            "best_buy_region": best_buy_region,
            "best_buy_region_id": REGIONS.get(best_buy_region),
            "lowest_material_cost": lowest_material_cost if lowest_material_cost != float('inf') else None,
            "material_costs_all": region_material_costs
        }


# Notification callback for Discord
def create_discord_notifier():
    """Create a Discord notification callback"""
    from notification_service import notification_service

    def notify(message: str, is_critical: bool):
        color = 0xFF0000 if is_critical else 0xFFA500  # Red or Orange
        title = "ESI CRITICAL ERROR" if is_critical else "ESI Warning"

        embed = {
            "title": title,
            "description": message,
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {"text": "EVE Co-Pilot Rate Limiter"}
        }

        notification_service.send_discord_webhook(embeds=[embed])

    return notify


# Global ESI client instance (with Discord notifications)
try:
    esi_client = ESIClient(notify_callback=create_discord_notifier())
except Exception:
    # Fallback without Discord notifications
    esi_client = ESIClient()
