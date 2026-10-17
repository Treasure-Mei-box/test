from flask import Flask
from .database import close_db, init_db
from .routes import main_bp


def create_app():
    app = Flask(__name__)
    app.secret_key = "change-this-secret-key-for-demo"

    app.teardown_appcontext(close_db)
    app.register_blueprint(main_bp)

    with app.app_context():
        init_db()

    return app
