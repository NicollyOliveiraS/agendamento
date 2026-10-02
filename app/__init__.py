from flask import Flask

from config import Config
from app.extensions import db, login_manager


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    from app.models import AdminUser

    @login_manager.user_loader
    def load_user(user_id):
        return AdminUser.query.get(int(user_id))

    from app.routes.public import public_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # Disponibiliza o nome do negócio em todos os templates
    @app.context_processor
    def inject_settings():
        from app.models import Settings

        with app.app_context():
            try:
                settings = Settings.get()
            except Exception:
                settings = None
        return {"business_settings": settings}

    with app.app_context():
        db.create_all()

    return app
