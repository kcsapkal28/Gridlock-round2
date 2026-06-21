import os
class Settings:
    SCORES_PARQUET = os.environ.get("SCORES_PARQUET", "fe_work/cell_scores.parquet")
    IMPACT_MODEL = os.environ.get("IMPACT_MODEL", "fe_work/fe_out/model_impact.txt")
    FE_OUT = os.environ.get("FE_OUT", "fe_work/fe_out")
    RCP_CSV = os.environ.get("RCP_CSV", "fe_work/fe_out/rcp.csv")
    STATIC_OUT = os.environ.get("STATIC_OUT", "web/public/data")
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
    MAPPLS_SECRETS = os.environ.get("MAPPLS_SECRETS", ".mappls_secrets")
    MAPPLS_CACHE = os.environ.get("MAPPLS_CACHE", ".mappls_cache")
    OUTBOUND_TIMEOUT = float(os.environ.get("OUTBOUND_TIMEOUT", "5"))
    BREAKER_FAILS = int(os.environ.get("BREAKER_FAILS", "5"))
    BREAKER_COOLDOWN = float(os.environ.get("BREAKER_COOLDOWN", "120"))
    MAPPLS_RATE_PER_MIN = int(os.environ.get("MAPPLS_RATE_PER_MIN", "60"))
    ROADCLASS_SNAP = os.environ.get("ROADCLASS_SNAP", "off")  # off until snap-to-road verified
    VERSION = "0.1.0"
    # --- AI copilot (Claude via the local claude-openai proxy, port 4001 passthrough) ---
    AI_ENABLED = os.environ.get("AI_ENABLED", "1") not in ("0", "false", "")
    AI_BASE_URL = os.environ.get("AI_BASE_URL", "http://localhost:4001")
    AI_API_KEY = os.environ.get("AI_API_KEY", "sk-proxy-694c3321a907a1f281483b767e3be689")
    AI_MODEL = os.environ.get("AI_MODEL", "claude-sonnet-4-6")
    AI_TIMEOUT = float(os.environ.get("AI_TIMEOUT", "30"))
    AI_MAX_TOOL_ITERS = int(os.environ.get("AI_MAX_TOOL_ITERS", "5"))
    AI_MODEL_SUMMARY_MAX_CHARS = int(os.environ.get("AI_MODEL_SUMMARY_MAX_CHARS", "1500"))
    AI_HISTORY_EXCHANGES = int(os.environ.get("AI_HISTORY_EXCHANGES", "2"))
settings = Settings()
