from functools import lru_cache
from flask import current_app
from ..models import User, UserSkill


@lru_cache(maxsize=1)
def _load_model(model_name):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_name)


def _semantic_scores(query, candidates):
    try:
        import numpy as np
        model = _load_model(current_app.config["AI_MODEL_NAME"])
        vectors = model.encode([query, *candidates], normalize_embeddings=True)
        return [float(np.dot(vectors[0], vector)) for vector in vectors[1:]]
    except Exception:
        current_app.logger.exception("Semantic model unavailable; using skill-overlap matching")
        return None


def recommend(user, limit=10):
    offered = [link.skill.name for link in user.skills if link.direction == "offers"]
    wanted = [link.skill.name for link in user.skills if link.direction == "wants"]
    if not offered and not wanted:
        return []
    candidates = User.query.filter(User.id != user.id).all()
    names = [" ".join([link.skill.name for link in candidate.skills]) for candidate in candidates]
    query = "teaching " + ", ".join(wanted) + "; learning " + ", ".join(offered)
    semantic = _semantic_scores(query, names) if current_app.config["MATCHING_USE_EMBEDDINGS"] and names else None
    results = []
    for index, candidate in enumerate(candidates):
        their_offers = {s.skill.name.lower() for s in candidate.skills if s.direction == "offers"}
        their_wants = {s.skill.name.lower() for s in candidate.skills if s.direction == "wants"}
        wanted_fit = max([1.0 if skill.lower() in their_offers else 0.0 for skill in wanted] or [0.0])
        exchange_fit = max([1.0 if skill.lower() in their_wants else 0.0 for skill in offered] or [0.0])
        if semantic is not None:
            relevance = max(0.0, semantic[index])
            score = round(100 * (0.65 * relevance + 0.2 * wanted_fit + 0.15 * exchange_fit))
            reason = "AI semantic similarity" if relevance > 0.35 else "Skill exchange compatibility"
        else:
            score = round(100 * (0.55 * wanted_fit + 0.45 * exchange_fit))
            reason = "Shared skill exchange" if wanted_fit and exchange_fit else "Offers a skill on your learning list" if wanted_fit else "Interested in a skill you offer"
        if score:
            results.append({"user": candidate, "score": score, "reason": reason})
    return sorted(results, key=lambda result: result["score"], reverse=True)[:limit]
