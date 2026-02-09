"""Cinema search tool (Mock implementation)"""
from typing import Dict, Any
from datetime import datetime, timedelta
import logging

from tools.base import BaseTool, ToolSchema, ToolParameter, ToolMetadata

logger = logging.getLogger(__name__)


class CinemaSearchTool(BaseTool):
    """Search for movies and showtimes"""

    def _build_schema(self) -> ToolSchema:
        return ToolSchema(
            name="cinema_search",
            description=(
                "Search for movies and showtimes at cinemas near a given location. "
                "Optionally filter by date (ISO8601) and/or movie title. Returns a list "
                "of movies with genre, rating, available showtimes, theater name, address, "
                "and ticket price. Currently returns clearly-tagged mock/placeholder data "
                "when no real cinema API is configured."
            ),
            metadata=ToolMetadata(
                destructive_hint=False,
                read_only_hint=True,
                idempotent_hint=True,
                open_world_hint=True,
                requires_auth_hint=False,
                mock_mode=True,  # No real cinema API configured yet
            ),
            parameters=[
                ToolParameter(
                    name="location",
                    type="string",
                    description="Location to search for cinemas",
                    required=True
                ),
                ToolParameter(
                    name="date",
                    type="string",
                    description="Date to search for showtimes (ISO8601)",
                    required=False
                ),
                ToolParameter(
                    name="movie_title",
                    type="string",
                    description="Specific movie title to search for",
                    required=False
                )
            ]
        )

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Search for movies and showtimes (mock data)

        Returns:
        {
            'success': bool,
            'movies': [
                {
                    'title': str,
                    'genre': str,
                    'rating': str,
                    'showtimes': [str],
                    'theater': str,
                    'address': str,
                    'price': str
                }
            ]
        }
        """
        try:
            await self.validate_parameters(**kwargs)

            location = kwargs['location']
            date_str = kwargs.get('date')
            movie_title = kwargs.get('movie_title')

            # Parse date
            if date_str:
                target_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                target_date = datetime.now()

            # Generate mock showtimes
            base_times = ["14:00", "16:30", "19:00", "21:30"]

            mock_movies = [
                {
                    'title': movie_title if movie_title else f'Popular Movie {i+1}',
                    'genre': ['Action', 'Comedy', 'Drama', 'Thriller'][i % 4],
                    'rating': 'PG-13',
                    'showtimes': base_times,
                    'theater': f'Cinema {location} - Theater {i+1}',
                    'address': f'{(i+1)*100} Movie Boulevard, {location}',
                    'price': '$12.00'
                }
                for i in range(3)
            ]

            logger.info(f"Mock cinema search: Found {len(mock_movies)} movies in {location}")

            return {
                'success': True,
                'mock': True,
                'movies': mock_movies,
                'date': target_date.strftime('%Y-%m-%d')
            }

        except Exception as e:
            logger.error(f"Cinema search error: {e}", exc_info=True)
            return {
                'success': False,
                'error': "Failed to search cinemas. Please try again.",
            }
