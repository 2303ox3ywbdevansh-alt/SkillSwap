import re
from urllib.parse import urljoin, urlsplit
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user, login_required
from ..extensions import db
from ..models import User, Skill, UserSkill

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if len(name) < 2 or not re.fullmatch(r"[a-z0-9_]{3,40}", username):
            flash("Enter a name and a username (3–40 letters, numbers, or underscores).", "error")
        elif "@" not in email or len(password) < 10:
            flash("Use a valid email and a password with at least 10 characters.", "error")
        elif User.query.filter(db.or_(User.username == username, User.email == email)).first():
            flash("That username or email is already registered.", "error")
        else:
            user = User(name=name, username=username, email=email, bio=request.form.get("bio", "").strip()[:500], learning_language=request.form.get("language", "English").strip()[:60] or "English")
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Welcome to SkillSwap! Add your skills to get started.", "success")
            return redirect(url_for("main.dashboard"))
    return render_template("auth.html", mode="register")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        user = User.query.filter_by(email=request.form.get("email", "").strip().lower()).first()
        if user and user.check_password(request.form.get("password", "")):
            login_user(user, remember=bool(request.form.get("remember")))
            next_page = request.args.get("next", "")
            target = urlsplit(urljoin(request.host_url, next_page))
            if target.scheme in {"http", "https"} and target.netloc == request.host:
                return redirect(target.path + (("?" + target.query) if target.query else ""))
            return redirect(url_for("main.dashboard"))
        flash("Email or password is incorrect.", "error")
    return render_template("auth.html", mode="login")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You are signed out.", "info")
    return redirect(url_for("main.index"))


@auth_bp.route("/skills", methods=["POST"])
@login_required
def add_skill():
    name = request.form.get("name", "").strip()
    direction = request.form.get("direction", "")
    level = request.form.get("level", "Beginner")
    if not name or len(name) > 100 or direction not in {"offers", "wants"} or level not in {"Beginner", "Intermediate", "Advanced"}:
        flash("Check the skill details and try again.", "error")
    else:
        skill = Skill.query.filter(db.func.lower(Skill.name) == name.lower()).first()
        if not skill:
            skill = Skill(name=name)
            db.session.add(skill)
            db.session.flush()
        existing = UserSkill.query.filter_by(user_id=current_user.id, skill_id=skill.id, direction=direction).first()
        if not existing:
            db.session.add(UserSkill(user_id=current_user.id, skill_id=skill.id, direction=direction, level=level))
            db.session.commit()
            flash("Skill added to your profile.", "success")
        else:
            flash("That skill is already on your list.", "info")
    return redirect(url_for("main.dashboard"))


@auth_bp.route("/skills/<int:skill_link_id>/remove", methods=["POST"])
@login_required
def remove_skill(skill_link_id):
    link = db.session.get(UserSkill, skill_link_id)
    if not link or link.user_id != current_user.id:
        return "Not found", 404
    db.session.delete(link)
    db.session.commit()
    flash("Skill removed.", "success")
    return redirect(url_for("main.dashboard"))
