from flask import Flask
from flask_caching import Cache

cache = Cache()

def create_app():
    app = Flask(__name__)
    
    # Configuration - Try Redis first, fallback to SimpleCache
    try:
        app.config['CACHE_TYPE'] = 'redis'
        app.config['CACHE_REDIS_URL'] = 'redis://localhost:6379/0'
        app.config['CACHE_DEFAULT_TIMEOUT'] = 300
        cache.init_app(app)
        print("✅ Cache: Redis enabled")
    except Exception as e:
        # Fallback to SimpleCache (in-memory)
        app.config['CACHE_TYPE'] = 'SimpleCache'
        app.config['CACHE_DEFAULT_TIMEOUT'] = 300
        cache.init_app(app)
        print(f"⚠️ Cache: Using SimpleCache fallback (Redis unavailable: {e})")
    
    # Register Blueprints

    from app.routes.main_routes import main_bp
    from app.routes.analytics_routes import analytics_bp
    from app.routes.api_routes import api_bp
    from app.routes.browse_routes import browse_bp
    from app.routes.admin_routes import admin_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(browse_bp)
    app.register_blueprint(admin_bp)
    
    return app
