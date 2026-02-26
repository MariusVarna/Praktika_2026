from fastapi.testclient import TestClient
from app.main import app
import pytest

client = TestClient(app)

def test_forecast_logic():
    # 1. Create a session with a high error margin
    session_data = {
        "admin_id": "test_admin",
        "forecast_error_margin": 0.5,  # 50% error
        "base_demand_mw": 3000.0
    }
    response = client.post("/api/sessions/", json=session_data)
    assert response.status_code == 200
    session_id = response.json()["id"]
    
    # 2. Get forecast for round 1
    forecast_response = client.get(f"/api/sessions/{session_id}/round/1/forecast")
    assert forecast_response.status_code == 200
    data = forecast_response.json()
    
    assert data["round_id"] == 1
    assert len(data["forecast"]) == 24
    
    for item in data["forecast"]:
        assert "predicted_price" in item
        assert "hour" in item
        print(f"Hour {item['hour']}: {item['predicted_price']} EUR")

if __name__ == "__main__":
    test_forecast_logic()
