import os

# Unit and API tests must never depend on an external market-data service.
os.environ["MARKET_DATA_MODE"] = "demo"
# A developer's local .env must not turn unit tests into database or LLM integration tests.
os.environ["DATABASE_URL"] = ""
os.environ["LLM_API_KEY"] = ""
