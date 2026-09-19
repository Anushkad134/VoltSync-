import pytest
from fastapi.testclient import TestClient
from fastapi import Request
from app.main import app
from app.api.deps import get_current_user
from app.models.user import User

client = TestClient(app)

class MockDBSession:
    def __init__(self):
        self.users = {
            "clerk_driver_1": User(clerk_user_id="clerk_driver_1", role="driver", linked_station_ids=[]),
            "clerk_op_1": User(clerk_user_id="clerk_op_1", role="operator", linked_station_ids=["ST-1"])
        }

    def query(self, model):
        self._current_model = model
        return self

    def filter(self, condition):
        # We know condition is User.clerk_user_id == something. We can extract it by string parsing the compiled statement,
        # but for a simple mock, let's just cheat and store the expected clerk_id in the mock db.
        self._last_condition = condition
        return self

    def first(self):
        # In our tests, verify_token will return the token string which we'll map directly to clerk_user_id
        # We can pass the actual clerk_id via an attribute we set during the test.
        # But wait, a better way is to override get_db dependency entirely.
        pass

@pytest.fixture(autouse=True)
def clear_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()

def test_missing_auth_header():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "error_code" in response.json() and response.json()["error_code"] == "UNAUTHENTICATED"

def test_invalid_auth_token():
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401
    assert response.json()["error_code"] == "UNAUTHENTICATED"

def test_auth_flow(monkeypatch):
    from app.api import deps
    
    def mock_verify(token):
        if token == "good_driver": return "clerk_driver_1"
        if token == "good_op": return "clerk_op_1"
        if token == "unknown_user": return "nobody"
        raise ValueError("Invalid")
        
    monkeypatch.setattr(deps, "verify_token", mock_verify)

    from app.api.deps import get_db
    
    class FakeQuery:
        def __init__(self, token):
            self.token = token
        def first(self):
            if self.token == "clerk_driver_1":
                return User(clerk_user_id="clerk_driver_1", role="driver", linked_station_ids=[])
            if self.token == "clerk_op_1":
                return User(clerk_user_id="clerk_op_1", role="operator", linked_station_ids=["ST-1"])
            return None
        def all(self):
            return []
        def count(self):
            return 0
        def order_by(self, *args):
            return self
            
    class FakeDB:
        def __init__(self, current_clerk_id=None):
            self.current_clerk_id = current_clerk_id
        def query(self, *args):
            return self
        def filter(self, condition):
            # Extract the right side of the condition (clerk_user_id == 'value')
            # It's a SQLAlchemy BinaryExpression. condition.right.value has the value.
            val = condition.right.value
            return FakeQuery(val)

    app.dependency_overrides[get_db] = lambda: FakeDB()

    # 1. Unknown user -> 403
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer unknown_user"})
    assert response.status_code == 403
    
    # 2. Good driver -> 200
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer good_driver"})
    assert response.status_code == 200
    assert response.json()["data"]["role"] == "driver"

    # 3. Role mismatch (driver accessing operator route) -> 403
    response = client.get("/api/v1/operator/dashboard", headers={"Authorization": "Bearer good_driver"})
    assert response.status_code == 403
    
    # 4. Good operator -> 200 on operator route
    response = client.get("/api/v1/operator/dashboard", headers={"Authorization": "Bearer good_op"})
    assert response.status_code != 403
    assert response.status_code != 401

