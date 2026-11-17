"""
CampusAssist: Routes package.
Exposes main_bp, api_bp, and admin_bp blueprints.
"""

from app.routes.main_routes import main_bp
from app.routes.api_routes import api_bp
from app.routes.admin_routes import admin_bp

__all__ = ["main_bp", "api_bp", "admin_bp"]
