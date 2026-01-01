from flask import Flask
from flask_caching import Cache

cache = Cache()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['CACHE_TYPE'] = 'redis'
    app.config['CACHE_REDIS_URL'] = 'redis://localhost:6379/0'
    app.config['CACHE_DEFAULT_TIMEOUT'] = 300
    
    # Initialize extensions
    try:
        cache.init_app(app)
    except Exception as e:
        print(f"⚠️ Redis not available: {e}")
    
    # Register Blueprints
    from app.routes.main_routes import main_bp
    from app.routes.analytics_routes import analytics_bp
    from app.routes.api_routes import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(api_bp)
    
    return app
