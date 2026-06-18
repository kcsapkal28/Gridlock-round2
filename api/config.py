import os
class Settings:
    SCORES_PARQUET = os.environ.get("SCORES_PARQUET", "fe_work/cell_scores.parquet")
    IMPACT_MODEL = os.environ.get("IMPACT_MODEL", "fe_work/fe_out/model_impact.txt")
    FE_OUT = os.environ.get("FE_OUT", "fe_work/fe_out")
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
settings = Settings()
