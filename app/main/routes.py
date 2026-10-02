from flask import Blueprint, render_template
from flask_login import current_user, login_required
from ..models import User, Session, Review

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return render_template("dashboard.html", user=current_user, matches=[], sessions=Session.query.filter((Session.teacher_id == current_user.id) | (Session.learner_id == current_user.id)).order_by(Session.starts_at.desc()).limit(5).all())
    return render_template("landing.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    from ..matching.service import recommend
    matches = recommend(current_user, limit=4)
    sessions = Session.query.filter((Session.teacher_id == current_user.id) | (Session.learner_id == current_user.id)).order_by(Session.starts_at.asc()).limit(5).all()
    return render_template("dashboard.html", user=current_user, matches=matches, sessions=sessions)


@main_bp.route("/profile/<username>")
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    reviews = Review.query.filter_by(reviewee_id=user.id).order_by(Review.created_at.desc()).limit(8).all()
    return render_template("profile.html", profile=user, reviews=reviews)


@main_bp.route("/demo-profiles")
def demo_profiles():
    profiles = [user for user in User.query.order_by(User.name.asc()).all() if user.username.startswith("demo_")]
    return render_template("demo_profiles.html", profiles=profiles)
