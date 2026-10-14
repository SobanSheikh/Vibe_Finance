import os

# Unit and API tests must never depend on an external market-data service.
os.environ["MARKET_DATA_MODE"] = "demo"
