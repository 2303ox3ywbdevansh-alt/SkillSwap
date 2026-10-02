from flask import Blueprint, render_template
from flask_login import current_user, login_required
from .service import recommend

matching_bp = Blueprint("matching", __name__, url_prefix="/matches")


@matching_bp.route("/")
@login_required
def index():
    return render_template("matches.html", matches=recommend(current_user, limit=30))
