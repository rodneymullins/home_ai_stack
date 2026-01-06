#!/usr/bin/env python3
"""
Fellowship Cache - Response caching for faster repeated queries
Simple file-based caching with TTL support.
"""

import hashlib
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FellowshipCache:
    """Simple file-based cache for AI responses."""
    
    def __init__(self, cache_dir="~/fellowship_cache", default_ttl=3600):
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl  # seconds
        logger.info(f"✅ Cache initialized: {self.cache_dir}")
    
    def _get_cache_key(self, model, prompt):
        """Generate cache key from model and prompt."""
        content = f"{model}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key):
        """Get path to cache file."""
        return self.cache_dir / f"{cache_key}.json"
    
    def get(self, model, prompt):
        """Get cached response if available and not expired."""
        cache_key = self._get_cache_key(model, prompt)
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            logger.debug(f"❌ Cache miss for {model}")
            return None
        
        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
            
            # Check expiration
            expires_at = datetime.fromisoformat(cache_data['expires_at'])
            if datetime.now() > expires_at:
                logger.debug(f"⏰ Cache expired for {model}")
                cache_path.unlink()  # Delete expired cache
                return None
            
            logger.info(f"✅ Cache HIT for {model}")
            return cache_data['response']
            
        except Exception as e:
            logger.warning(f"⚠️  Cache read error: {e}")
            return None
    
    def set(self, model, prompt, response, ttl=None):
        """Cache a response."""
        if ttl is None:
            ttl = self.default_ttl
        
        cache_key = self._get_cache_key(model, prompt)
        cache_path = self._get_cache_path(cache_key)
        
        cache_data = {
            'model': model,
            'prompt': prompt[:100],  # Store truncated prompt
            'response': response,
            'cached_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(seconds=ttl)).isoformat()
        }
        
        try:
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f)
            logger.info(f"💾 Cached response for {model} (TTL: {ttl}s)")
        except Exception as e:
            logger.warning(f"⚠️  Cache write error: {e}")
    
    def clear_expired(self):
        """Remove all expired cache entries."""
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                expires_at = datetime.fromisoformat(cache_data['expires_at'])
                if datetime.now() > expires_at:
                    cache_file.unlink()
                    count += 1
            except:
                pass  # Skip corrupted files
        
        logger.info(f"🧹 Cleared {count} expired cache entries")
        return count
    
    def clear_all(self):
        """Clear entire cache."""
        count = len(list(self.cache_dir.glob("*.json")))
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
        logger.info(f"🧹 Cleared all cache ({count} entries)")
        return count
    
    def get_stats(self):
        """Get cache statistics."""
        total_files = len(list(self.cache_dir.glob("*.json")))
        total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.json"))
        
        return {
            'total_entries': total_files,
            'total_size_mb': total_size / (1024 * 1024),
            'cache_dir': str(self.cache_dir)
        }


def main():
    """Demo cache functionality."""
    cache = FellowshipCache()
    
    # Show stats
    stats = cache.get_stats()
    print(f"📊 Cache Stats:")
    print(f"  • Entries: {stats['total_entries']}")
    print(f"  • Size: {stats['total_size_mb']:.2f} MB")
    print(f"  • Location: {stats['cache_dir']}")
    
    # Clean expired
    cleaned = cache.clear_expired()
    print(f"🧹 Cleaned {cleaned} expired entries")


if __name__ == '__main__':
    main()
