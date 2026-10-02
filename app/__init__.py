import os
from flask import Flask, jsonify, render_template
from .config import Config
from .extensions import db, migrate, login_manager, csrf, socketio


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    socketio.init_app(app, message_queue=app.config["REDIS_URL"] if os.getenv("FLASK_ENV") == "production" else None)

    from . import models  # noqa: F401
    from .auth.routes import auth_bp
    from .main.routes import main_bp
    from .matching.routes import matching_bp
    from .scheduling.routes import scheduling_bp
    from .seed import seed_demo
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(matching_bp)
    app.register_blueprint(scheduling_bp)
    app.cli.add_command(seed_demo)

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", code=404, message="We couldn't find that page."), 404

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("error.html", code=403, message="You don't have access to that."), 403

    @app.errorhandler(500)
    def server_error(_error):
        app.logger.exception("Unhandled server error")
        return render_template("error.html", code=500, message="Something went wrong. Please try again."), 500

    return app
