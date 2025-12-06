"""
Caching system for LLM responses to improve performance.
"""

import hashlib
import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from logging import getLogger

from .interface import LLMResponse
from spoon_ai.schema import Message

logger = getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry for LLM responses."""
    response: LLMResponse
    timestamp: float
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    
    def is_expired(self, ttl: float) -> bool:
        """Check if cache entry is expired.
        
        Args:
            ttl: Time to live in seconds
            
        Returns:
            bool: True if expired
        """
        return time.time() - self.timestamp > ttl
    
    def touch(self) -> None:
        """Update access information."""
        self.access_count += 1
        self.last_accessed = time.time()


class LLMResponseCache:
    """Cache for LLM responses with TTL and size limits."""
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 3600):
        """Initialize cache.
        
        Args:
            max_size: Maximum number of entries
            default_ttl: Default time to live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0
        }
    
    def _generate_key(self, messages: List[Message], provider: str, **kwargs) -> str:
        """Generate cache key from request parameters.
        
        Args:
            messages: List of messages
            provider: Provider name
            **kwargs: Additional parameters
            
        Returns:
            str: Cache key
        """
        # Create a deterministic representation of the request
        cache_data = {
            'messages': [{'role': msg.role, 'content': msg.content} for msg in messages],
            'provider': provider,
            'params': {k: v for k, v in sorted(kwargs.items()) if k not in ['request_id', 'timestamp']}
        }
        
        # Generate hash
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_str.encode()).hexdigest()
    
    def get(self, messages: List[Message], provider: str, ttl: Optional[float] = None, **kwargs) -> Optional[LLMResponse]:
        """Get cached response if available and not expired.
        
        Args:
            messages: List of messages
            provider: Provider name
            ttl: Time to live override
            **kwargs: Additional parameters
            
        Returns:
            Optional[LLMResponse]: Cached response if available
        """
        key = self._generate_key(messages, provider, **kwargs)
        entry = self._cache.get(key)
        
        if entry is None:
            self._stats['misses'] += 1
            return None
        
        # Check if expired
        ttl = ttl or self.default_ttl
        if entry.is_expired(ttl):
            del self._cache[key]
            self._stats['misses'] += 1
            self._stats['size'] = len(self._cache)
            return None
        
        # Update access info and return
        entry.touch()
        self._stats['hits'] += 1
        
        logger.debug(f"Cache hit for key: {key[:16]}...")
        return entry.response
    
    def put(self, messages: List[Message], provider: str, response: LLMResponse, **kwargs) -> None:
        """Store response in cache.
        
        Args:
            messages: List of messages
            provider: Provider name
            response: Response to cache
            **kwargs: Additional parameters
        """
        key = self._generate_key(messages, provider, **kwargs)
        
        # Check if we need to evict entries
        if len(self._cache) >= self.max_size:
            self._evict_lru()
        
        # Store entry
        entry = CacheEntry(
            response=response,
            timestamp=time.time()
        )
        self._cache[key] = entry
        self._stats['size'] = len(self._cache)
        
        logger.debug(f"Cached response for key: {key[:16]}...")
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return
        
        # Find LRU entry
        lru_key = min(self._cache.keys(), key=lambda k: self._cache[k].last_accessed)
        del self._cache[lru_key]
        self._stats['evictions'] += 1
        
        logger.debug(f"Evicted LRU entry: {lru_key[:16]}...")
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._stats['size'] = 0
        logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dict[str, Any]: Cache statistics
        """
        total_requests = self._stats['hits'] + self._stats['misses']
        hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0
        
        return {
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'evictions': self._stats['evictions'],
            'size': self._stats['size'],
            'max_size': self.max_size,
            'hit_rate': hit_rate,
            'total_requests': total_requests
        }
    
    def cleanup_expired(self) -> int:
        """Remove expired entries.
        
        Returns:
            int: Number of entries removed
        """
        expired_keys = []
        current_time = time.time()
        
        for key, entry in self._cache.items():
            if current_time - entry.timestamp > self.default_ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        self._stats['size'] = len(self._cache)
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)


# Global cache instance
_global_cache: Optional[LLMResponseCache] = None


def get_global_cache() -> LLMResponseCache:
    """Get global cache instance.
    
    Returns:
        LLMResponseCache: Global cache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = LLMResponseCache()
    return _global_cache


def set_global_cache(cache: LLMResponseCache) -> None:
    """Set global cache instance.
    
    Args:
        cache: Cache instance to set as global
    """
    global _global_cache
    _global_cache = cache


class CachedLLMManager:
    """LLM Manager wrapper with caching support."""
    
    def __init__(self, manager, cache: Optional[LLMResponseCache] = None):
        """Initialize cached manager.
        
        Args:
            manager: LLM manager instance
            cache: Cache instance (optional)
        """
        self.manager = manager
        self.cache = cache or get_global_cache()
        self.cache_enabled = True
    
    async def chat(self, messages: List[Message], provider: Optional[str] = None, use_cache: bool = True, **kwargs) -> LLMResponse:
        """Chat with caching support.
        
        Args:
            messages: List of messages
            provider: Provider name
            use_cache: Whether to use cache
            **kwargs: Additional parameters
            
        Returns:
            LLMResponse: Response (cached or fresh)
        """
        if not (self.cache_enabled and use_cache):
            return await self.manager.chat(messages, provider=provider, **kwargs)
        
        # Try to get from cache
        cached_response = self.cache.get(messages, provider or 'default', **kwargs)
        if cached_response is not None:
            return cached_response
        
        # Get fresh response
        response = await self.manager.chat(messages, provider=provider, **kwargs)
        
        # Cache the response
        self.cache.put(messages, provider or 'default', response, **kwargs)
        
        return response
    
    async def chat_with_tools(self, messages: List[Message], tools: List[Dict], provider: Optional[str] = None, use_cache: bool = True, **kwargs) -> LLMResponse:
        """Chat with tools and caching support.
        
        Args:
            messages: List of messages
            tools: List of tools
            provider: Provider name
            use_cache: Whether to use cache
            **kwargs: Additional parameters
            
        Returns:
            LLMResponse: Response (cached or fresh)
        """
        # Include tools in cache key
        kwargs['tools'] = tools
        
        if not (self.cache_enabled and use_cache):
            return await self.manager.chat_with_tools(messages, tools, provider=provider, **kwargs)
        
        # Try to get from cache
        cached_response = self.cache.get(messages, provider or 'default', **kwargs)
        if cached_response is not None:
            return cached_response
        
        # Get fresh response
        response = await self.manager.chat_with_tools(messages, tools, provider=provider, **kwargs)
        
        # Cache the response
        self.cache.put(messages, provider or 'default', response, **kwargs)
        
        return response
    
    def enable_cache(self) -> None:
        """Enable caching."""
        self.cache_enabled = True
        logger.info("LLM response caching enabled")
    
    def disable_cache(self) -> None:
        """Disable caching."""
        self.cache_enabled = False
        logger.info("LLM response caching disabled")
    
    def clear_cache(self) -> None:
        """Clear cache."""
        self.cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dict[str, Any]: Cache statistics
        """
        return self.cache.get_stats()
    
    def __getattr__(self, name):
        """Delegate other methods to the underlying manager."""
        return getattr(self.manager, name)