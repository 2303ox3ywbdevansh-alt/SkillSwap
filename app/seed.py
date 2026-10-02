import secrets
import click
from flask import current_app
from .extensions import db
from .models import Skill, User, UserSkill


DEMO_PROFILES = [
    {
        "name": "Aarav Mehta", "username": "demo_aarav", "email": "demo.aarav@skillswap.example",
        "bio": "Backend developer who enjoys making Python feel approachable. Looking to trade coding help for creative feedback.",
        "language": "English, Hindi", "offers": [("Python", "Advanced"), ("Flask", "Intermediate"), ("REST APIs", "Intermediate")],
        "wants": [("UI Design", "Beginner"), ("Figma", "Beginner")],
    },
    {
        "name": "Maya Kapoor", "username": "demo_maya", "email": "demo.maya@skillswap.example",
        "bio": "Product designer focused on friendly, useful interfaces. Happy to teach design basics and learn to build them with code.",
        "language": "English, Hindi", "offers": [("UI Design", "Advanced"), ("Figma", "Advanced"), ("Prototyping", "Intermediate")],
        "wants": [("Python", "Beginner"), ("Flask", "Beginner")],
    },
    {
        "name": "Isha Rao", "username": "demo_isha", "email": "demo.isha@skillswap.example",
        "bio": "Confident communicator and spreadsheet enthusiast. I like learning practical tools by building small projects together.",
        "language": "English", "offers": [("Public Speaking", "Advanced"), ("Excel", "Intermediate")],
        "wants": [("Python", "Beginner"), ("Data Analysis", "Beginner")],
    },
]


@click.command("seed-demo")
def seed_demo():
    """Create clearly labeled demo profiles for local development."""
    if not current_app.config.get("ENABLE_DEMO_SEED") or current_app.config.get("SESSION_COOKIE_SECURE"):
        raise click.ClickException("Demo seed is disabled. Enable ENABLE_DEMO_SEED=true in a local development .env first.")

    created = 0
    for data in DEMO_PROFILES:
        user = User.query.filter_by(username=data["username"]).first()
        if user is None:
            user = User(name=data["name"], username=data["username"], email=data["email"], bio=data["bio"], learning_language=data["language"])
            user.set_password(secrets.token_urlsafe(32))
            db.session.add(user)
            db.session.flush()
            created += 1
        for direction in ("offers", "wants"):
            for skill_name, level in data[direction]:
                skill = Skill.query.filter(db.func.lower(Skill.name) == skill_name.lower()).first()
                if skill is None:
                    skill = Skill(name=skill_name)
                    db.session.add(skill)
                    db.session.flush()
                link = UserSkill.query.filter_by(user_id=user.id, skill_id=skill.id, direction=direction).first()
                if link is None:
                    db.session.add(UserSkill(user_id=user.id, skill_id=skill.id, direction=direction, level=level))
    db.session.commit()
    click.echo(f"Demo profiles ready: {len(DEMO_PROFILES)} total, {created} newly created.")
    click.echo("View them at /demo-profiles. The sample users have random, unreported passwords and are for profile/matching demos only.")
