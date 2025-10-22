"""
RootMe caching utilities to reduce API calls and improve performance.
"""
import re
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import AsyncSessionLocal
from db.models import AuthenticatedUser, RootMeCache
from api import RootMe


class RootMeCacheManager:
    """Manages RootMe data caching to reduce API calls."""
    
    @staticmethod
    async def get_user_stats(user_id: int, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get RootMe stats for a user, using cache when possible.
        
        Args:
            user_id: Discord user ID
            force_refresh: Force refresh from API even if cache is valid
            
        Returns:
            Dict with RootMe stats or None if user has no RootMe linked
        """
        async with AsyncSessionLocal() as session:
            # Get user with RootMe ID
            result = await session.execute(
                select(AuthenticatedUser).where(AuthenticatedUser.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user or not user.rootme_id:
                return None
            
            # Check for existing cache
            result = await session.execute(
                select(RootMeCache).where(RootMeCache.user_id == user_id)
            )
            cache = result.scalar_one_or_none()
            
            # Use cache if valid and not forcing refresh
            if cache and not cache.is_expired and not force_refresh:
                return {
                    'pseudo': cache.pseudo,
                    'score': cache.score,
                    'position': cache.position,
                    'rank': cache.rank,
                    'challenge_count': cache.challenge_count,
                    'cached': True,
                    'last_updated': cache.last_updated
                }
            
            # Fetch fresh data from API
            try:
                RootMe.setup()
                rootme_data = await RootMe.get_author(str(user.rootme_id))
                
                # Extract and normalize data
                pseudo = rootme_data.get("nom", str(user.rootme_id))
                raw_score = rootme_data.get("score", 0)
                try:
                    score = int(raw_score) if isinstance(raw_score, int) else int(str(raw_score).replace(',', '').strip())
                except Exception:
                    score = 0
                
                position = rootme_data.get("position", None)
                try:
                    position = int(position) if position else None
                except Exception:
                    position = None
                
                rank = rootme_data.get("rang", None)
                challenges = rootme_data.get("validations", [])
                challenge_count = len(challenges) if challenges else 0
                
                # Update or create cache
                if cache:
                    cache.pseudo = pseudo
                    cache.score = score
                    cache.position = position
                    cache.rank = rank
                    cache.challenge_count = challenge_count
                    cache.last_updated = datetime.now()
                else:
                    cache = RootMeCache(
                        user_id=user_id,
                        rootme_id=user.rootme_id,
                        pseudo=pseudo,
                        score=score,
                        position=position,
                        rank=rank,
                        challenge_count=challenge_count,
                        last_updated=datetime.now()
                    )
                    session.add(cache)
                
                await session.commit()
                
                return {
                    'pseudo': pseudo,
                    'score': score,
                    'position': position,
                    'rank': rank,
                    'challenge_count': challenge_count,
                    'cached': False,
                    'last_updated': datetime.now()
                }
                
            except Exception as e:
                # If API fails and we have cache, return stale cache
                if cache:
                    return {
                        'pseudo': cache.pseudo,
                        'score': cache.score,
                        'position': cache.position,
                        'rank': cache.rank,
                        'challenge_count': cache.challenge_count,
                        'cached': True,
                        'last_updated': cache.last_updated,
                        'api_error': str(e)
                    }
                raise e
    
    @staticmethod
    async def get_team_stats(user_ids: list[int], force_refresh: bool = False) -> Tuple[Dict[str, Any], list[Dict[str, Any]]]:
        """
        Get RootMe stats for multiple team members.
        
        Args:
            user_ids: List of Discord user IDs
            force_refresh: Force refresh from API even if cache is valid
            
        Returns:
            Tuple of (team_stats, member_stats_list)
        """
        team_total_score = 0
        team_total_challenges = 0
        linked_count = 0
        member_stats = []
        
        for user_id in user_ids:
            stats = await RootMeCacheManager.get_user_stats(user_id, force_refresh)
            if stats:
                linked_count += 1
                team_total_score += stats['score']
                team_total_challenges += stats['challenge_count']
                
                member_stats.append({
                    'user_id': user_id,
                    'pseudo': stats['pseudo'],
                    'score': stats['score'],
                    'position': stats['position'],
                    'rank': stats['rank'],
                    'challenge_count': stats['challenge_count'],
                    'cached': stats.get('cached', False),
                    'api_error': stats.get('api_error')
                })
            else:
                member_stats.append({
                    'user_id': user_id,
                    'pseudo': None,
                    'score': 0,
                    'position': None,
                    'rank': None,
                    'challenge_count': 0,
                    'cached': False
                })
        
        team_stats = {
            'total_score': team_total_score,
            'total_challenges': team_total_challenges,
            'average_score': team_total_score // max(linked_count, 1) if linked_count > 0 else 0,
            'linked_count': linked_count,
            'total_members': len(user_ids)
        }
        
        return team_stats, member_stats
    
    @staticmethod
    async def refresh_user_cache(user_id: int) -> bool:
        """
        Force refresh cache for a specific user.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            True if refresh successful, False otherwise
        """
        try:
            await RootMeCacheManager.get_user_stats(user_id, force_refresh=True)
            return True
        except Exception:
            return False
    
    @staticmethod
    async def cleanup_expired_cache() -> int:
        """
        Clean up expired cache entries.
        
        Returns:
            Number of entries cleaned up
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(RootMeCache).where(RootMeCache.is_expired == True)
            )
            expired_caches = result.scalars().all()
            
            count = len(expired_caches)
            for cache in expired_caches:
                await session.delete(cache)
            
            await session.commit()
            return count
