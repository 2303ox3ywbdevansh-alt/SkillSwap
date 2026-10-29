from flask import session as flask_session
from flask import request
from flask_login import current_user
from flask_socketio import join_room, leave_room
from ..extensions import db, socketio
from ..models import Session


def _authorized_session(session_id):
    if not current_user.is_authenticated:
        return None
    booked = db.session.get(Session, session_id)
    if not booked or booked.status != "scheduled":
        return None
    if current_user.id not in {booked.teacher_id, booked.learner_id}:
        return None
    return booked


def _active_room(payload=None):
    if not current_user.is_authenticated:
        return None
    room = flask_session.get("video_room")
    session_id = flask_session.get("video_session_id")
    if not room or not session_id:
        return None
    try:
        booked = _authorized_session(int(session_id))
    except (TypeError, ValueError):
        return None
    if booked is None or room != f"video-session-{booked.id}":
        return None
    if isinstance(payload, dict) and payload.get("session_id") not in (None, booked.id, str(booked.id)):
        return None
    return room, booked


@socketio.on("video:join")
def join_video_room(payload):
    if not current_user.is_authenticated or not isinstance(payload, dict):
        return {"ok": False, "error": "Sign in to join this session."}
    try:
        session_id = int(payload.get("session_id"))
    except (TypeError, ValueError):
        return {"ok": False, "error": "Invalid session."}
    booked = _authorized_session(session_id)
    if booked is None:
        return {"ok": False, "error": "Only scheduled session participants can join this call."}

    old = _active_room()
    if old:
        old_room, _ = old
        leave_room(old_room)
        socketio.emit("video:peer_left", {"user_id": current_user.id}, to=old_room, skip_sid=request.sid)

    room = f"video-session-{session_id}"
    join_room(room)
    flask_session["video_room"] = room
    flask_session["video_session_id"] = session_id
    socketio.emit("video:peer_joined", {"user_id": current_user.id, "name": current_user.name}, to=room)
    return {"ok": True}


@socketio.on("video:ready")
def video_ready(payload=None):
    active = _active_room(payload)
    if active is None:
        return {"ok": False, "error": "Join an authorized session room first."}
    room, _ = active
    socketio.emit("video:ready", {"user_id": current_user.id}, to=room, skip_sid=request.sid)
    return {"ok": True}


def _relay(event_name, payload):
    active = _active_room(payload)
    if active is None or not isinstance(payload, dict):
        return {"ok": False, "error": "Join an authorized session room first."}
    data = payload.get("data")
    if not isinstance(data, dict) or len(str(data)) > 100_000:
        return {"ok": False, "error": "Invalid call signal."}
    room, _ = active
    socketio.emit(event_name, {"user_id": current_user.id, "data": data}, to=room, skip_sid=request.sid)
    return {"ok": True}


@socketio.on("video:offer")
def relay_offer(payload):
    return _relay("video:offer", payload)


@socketio.on("video:answer")
def relay_answer(payload):
    return _relay("video:answer", payload)


@socketio.on("video:ice")
def relay_ice_candidate(payload):
    return _relay("video:ice", payload)


@socketio.on("video:leave")
def leave_video_room():
    active = _active_room()
    if active:
        room, _ = active
        leave_room(room)
        socketio.emit("video:peer_left", {"user_id": current_user.id}, to=room, skip_sid=request.sid)
    flask_session.pop("video_room", None)
    flask_session.pop("video_session_id", None)
    return {"ok": True}


@socketio.on("disconnect")
def disconnect_video_room(_reason=None):
    active = _active_room()
    if active:
        room, _ = active
        socketio.emit("video:peer_left", {"user_id": current_user.id}, to=room, skip_sid=request.sid)
