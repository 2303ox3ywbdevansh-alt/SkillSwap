from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from .extensions import db, login_manager


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(40), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    bio = db.Column(db.String(500), default="")
    learning_language = db.Column(db.String(60), default="English")
    role = db.Column(db.String(20), nullable=False, default="student")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    skills = db.relationship("UserSkill", back_populates="user", cascade="all, delete-orphan")
    offered_sessions = db.relationship("Session", foreign_keys="Session.teacher_id", back_populates="teacher")
    learned_sessions = db.relationship("Session", foreign_keys="Session.learner_id", back_populates="learner")

    @property
    def credits(self):
        return sum(entry.amount for entry in self.credit_transactions)

    @property
    def rating(self):
        scores = [review.score for review in self.received_reviews]
        return round(sum(scores) / len(scores), 1) if scores else None

    @property
    def completed_sessions(self):
        return sum(s.status == "completed" for s in self.offered_sessions + self.learned_sessions)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)


class UserSkill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey("skill.id", ondelete="CASCADE"), nullable=False)
    direction = db.Column(db.String(10), nullable=False)  # offers | wants
    level = db.Column(db.String(20), default="Beginner", nullable=False)
    user = db.relationship("User", back_populates="skills")
    skill = db.relationship("Skill")
    __table_args__ = (db.UniqueConstraint("user_id", "skill_id", "direction"), db.Index("ix_user_skill_direction", "direction", "skill_id"))


class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    learner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    skill_id = db.Column(db.Integer, db.ForeignKey("skill.id"), nullable=False)
    starts_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    ends_at = db.Column(db.DateTime(timezone=True), nullable=False)
    status = db.Column(db.String(20), default="pending", nullable=False, index=True)
    notes = db.Column(db.String(500), default="")
    teacher = db.relationship("User", foreign_keys=[teacher_id], back_populates="offered_sessions")
    learner = db.relationship("User", foreign_keys=[learner_id], back_populates="learned_sessions")
    skill = db.relationship("Skill")


class CreditTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(120), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey("session.id"))
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    user = db.relationship("User", backref=db.backref("credit_transactions", cascade="all, delete-orphan"))


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("session.id", ondelete="CASCADE"), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    reviewee_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    body = db.Column(db.String(500), default="")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    reviewer = db.relationship("User", foreign_keys=[reviewer_id])
    reviewee = db.relationship("User", foreign_keys=[reviewee_id], backref=db.backref("received_reviews", lazy=True))
    session = db.relationship("Session")
    __table_args__ = (db.UniqueConstraint("session_id", "reviewer_id"), db.CheckConstraint("score >= 1 AND score <= 5"))


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
