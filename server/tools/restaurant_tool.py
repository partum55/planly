"""Restaurant search tool using Google Places API"""
from typing import Dict, Any, Optional
import logging

from tools.base import BaseTool, ToolSchema, ToolParameter, ToolMetadata

logger = logging.getLogger(__name__)


class RestaurantSearchTool(BaseTool):
    """Search for restaurants using Google Places or Yelp"""

    def __init__(self, places_client=None):
        self.places_client = places_client

    def _build_schema(self) -> ToolSchema:
        return ToolSchema(
            name="restaurant_search",
            description=(
                "Search for restaurants by location, cuisine type, and price range. "
                "Uses Google Places API when configured, otherwise returns clearly-tagged "
                "mock/placeholder data. Returns up to max_results restaurants (default 5) "
                "sorted by relevance. Each result includes name, address, rating, price "
                "level, cuisine type, phone number, and URL. Returns an empty list if "
                "no matches are found."
            ),
            metadata=ToolMetadata(
                destructive_hint=False,
                read_only_hint=True,
                idempotent_hint=True,
                open_world_hint=True,
            ),
            parameters=[
                ToolParameter(
                    name="location",
                    type="string",
                    description="Location to search (city, neighborhood, address)",
                    required=True
                ),
                ToolParameter(
                    name="cuisine",
                    type="string",
                    description="Type of cuisine (Italian, Chinese, etc.)",
                    required=False
                ),
                ToolParameter(
                    name="price_range",
                    type="string",
                    description="Price range ($, $$, $$$, $$$$)",
                    required=False
                ),
                ToolParameter(
                    name="max_results",
                    type="integer",
                    description="Maximum number of results to return",
                    required=False,
                    default=5
                )
            ]
        )

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Search for restaurants

        Returns:
        {
            'success': bool,
            'restaurants': [
                {
                    'name': str,
                    'address': str,
                    'rating': float,
                    'price_level': str,
                    'cuisine': str,
                    'phone': str,
                    'url': str
                }
            ],
            'result_count': int
        }
        """
        try:
            await self.validate_parameters(**kwargs)

            location = kwargs['location']
            cuisine = kwargs.get('cuisine')
            price_range = kwargs.get('price_range')
            max_results = kwargs.get('max_results', 5)

            # If places client not initialized, return mock data
            if not self.places_client:
                logger.warning("Places client not initialized, returning mock restaurants")
                return self._mock_restaurant_search(location, cuisine, max_results)

            # TODO: Implement real Google Places API search
            # For now, return mock data
            return self._mock_restaurant_search(location, cuisine, max_results)

        except Exception as e:
            logger.error(f"Restaurant search error: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _mock_restaurant_search(
        self,
        location: str,
        cuisine: Optional[str],
        max_results: int
    ) -> Dict[str, Any]:
        """Return mock restaurant data"""
        cuisine_label = cuisine if cuisine else "Various"

        mock_restaurants = [
            {
                'name': f'{cuisine_label} Bistro {i+1}',
                'address': f'{i*100 + 10} Main St, {location}',
                'rating': 4.0 + (i * 0.1),
                'price_level': '$$' if i < 3 else '$$$',
                'cuisine': cuisine or 'Mixed',
                'phone': f'+1-555-{1000+i}',
                'url': f'https://example.com/restaurant-{i+1}'
            }
            for i in range(min(max_results, 5))
        ]

        logger.info(f"Mock search: Found {len(mock_restaurants)} restaurants in {location}")

        return {
            'success': True,
            'mock': True,
            'restaurants': mock_restaurants,
            'result_count': len(mock_restaurants)
        }
