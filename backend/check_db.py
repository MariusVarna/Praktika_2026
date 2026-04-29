from app.database import SessionLocal
from sqlalchemy import inspect, text
from app import models

db = SessionLocal()

# Check the actual column type from SQLite
inspector = inspect(db.bind)
columns = inspector.get_columns('market_results')
for col in columns:
    if col['name'] == 'clearing_price':
        print(f"Column type: {col['type']}")
        print(f"Column info: {col}")

# Check actual stored values
results = db.query(models.MarketResult).limit(5).all()
for r in results:
    print(f"Hour {r.hour}: clearing_price = {r.clearing_price} (type: {type(r.clearing_price)})")

db.close()