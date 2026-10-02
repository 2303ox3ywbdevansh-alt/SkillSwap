from datetime import datetime
from flask import Blueprint, flash, redirect, request, url_for
from flask_login import current_user, login_required
from ..extensions import db
from ..models import User, Skill, Session, CreditTransaction, UserSkill

scheduling_bp = Blueprint("scheduling", __name__, url_prefix="/sessions")


@scheduling_bp.route("/request/<int:teacher_id>", methods=["POST"])
@login_required
def request_session(teacher_id):
    teacher = db.session.get(User, teacher_id)
    try:
        starts = datetime.fromisoformat(request.form["starts_at"])
        ends = datetime.fromisoformat(request.form["ends_at"])
        skill_id = int(request.form["skill_id"])
    except (KeyError, ValueError):
        flash("Enter a valid date, time, and skill.", "error")
        return redirect(url_for("matching.index"))
    skill = db.session.get(Skill, skill_id)
    teaches_skill = UserSkill.query.filter_by(user_id=teacher_id, skill_id=skill_id, direction="offers").first()
    if not teacher or teacher_id == current_user.id or not skill or not teaches_skill or ends <= starts or (ends - starts).total_seconds() > 4 * 3600:
        flash("That session request is not valid.", "error")
        return redirect(url_for("matching.index"))
    if starts <= datetime.now(starts.tzinfo):
        flash("Choose a future time.", "error")
        return redirect(url_for("matching.index"))
    conflict = Session.query.filter(Session.status.in_(["pending", "accepted", "scheduled"]), Session.starts_at < ends, Session.ends_at > starts, db.or_(Session.teacher_id.in_([teacher_id, current_user.id]), Session.learner_id.in_([teacher_id, current_user.id]))).first()
    if conflict:
        flash("One of the participants already has a session at that time.", "error")
        return redirect(url_for("matching.index"))
    session = Session(teacher_id=teacher_id, learner_id=current_user.id, skill_id=skill_id, starts_at=starts, ends_at=ends)
    db.session.add(session)
    db.session.commit()
    flash("Session request sent.", "success")
    return redirect(url_for("main.dashboard"))


@scheduling_bp.route("/<int:session_id>/respond", methods=["POST"])
@login_required
def respond(session_id):
    session = db.session.get(Session, session_id)
    action = request.form.get("action")
    if not session or session.teacher_id != current_user.id or session.status != "pending" or action not in {"accepted", "rejected"}:
        return "Not found", 404
    session.status = "scheduled" if action == "accepted" else "rejected"
    db.session.commit()
    flash("Session request updated.", "success")
    return redirect(url_for("main.dashboard"))


@scheduling_bp.route("/<int:session_id>/complete", methods=["POST"])
@login_required
def complete(session_id):
    session = db.session.get(Session, session_id)
    if not session or current_user.id not in {session.teacher_id, session.learner_id} or session.status != "scheduled":
        return "Not found", 404
    if session.starts_at > datetime.now(session.starts_at.tzinfo):
        flash("A session can be completed after its start time.", "error")
        return redirect(url_for("main.dashboard"))
    hours = max(1, round((session.ends_at - session.starts_at).total_seconds() / 3600))
    learner = db.session.get(User, session.learner_id)
    if learner.credits < hours:
        flash("Learner doesn't have enough time credits for this session.", "error")
        return redirect(url_for("main.dashboard"))
    session.status = "completed"
    db.session.add_all([CreditTransaction(user_id=session.teacher_id, amount=hours, reason="Teaching session", session_id=session.id), CreditTransaction(user_id=session.learner_id, amount=-hours, reason="Learning session", session_id=session.id)])
    db.session.commit()
    flash(f"Session completed. {hours} time credit(s) transferred.", "success")
    return redirect(url_for("main.dashboard"))
