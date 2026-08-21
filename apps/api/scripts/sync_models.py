"""Keep LLM agent versions pointed at the configured Gemini model.

Google retires model IDs regularly (gemini-2.0-flash is gone, 2.5 sunsets
Oct 2026). The runner reads the model from the agent_versions row, so this
idempotent sync runs on every container boot and rewrites any stale LLM
model with the currently configured one (GEMINI_MODEL / config default).

Run from apps/api:  python -m scripts.sync_models
"""

from app.config import get_settings
from app.database import SessionLocal
from app.models import AgentVersion

# engine → which configured model it should track.
LLM_ENGINES = ("gemini", "langgraph", "groq")


def main() -> None:
    settings = get_settings()
    # Policy versions never call an LLM — their model label comes from the
    # seed definitions and is kept honest by this sync.
    from scripts.seed import AGENT_VERSIONS, ensure_agent_versions

    seed_model = {av["id"]: av["model"] for av in AGENT_VERSIONS}

    db = SessionLocal()
    try:
        # Register versions introduced after the database was first seeded.
        ensure_agent_versions(db)

        updated = 0
        versions = (
            db.query(AgentVersion)
            .filter(AgentVersion.engine.in_(LLM_ENGINES + ("policy",)))
            .all()
        )
        for av in versions:
            if av.engine == "groq":
                target = settings.groq_model
            elif av.engine in ("gemini", "langgraph"):
                target = settings.gemini_model
            else:
                target = seed_model.get(av.id, av.model)
            if av.model != target:
                print(f"  {av.id} ({av.version}): {av.model} → {target}")
                av.model = target
                updated += 1
        db.commit()
        print(f"→ LLM agent models synced ({updated} updated)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
