from app import app


def test_home():
    res = app.test_client().get("/")
    assert res.status_code == 200
    assert b"Your Local Shop" in res.data


def test_catalogue():
    res = app.test_client().get("/catalogue")
    assert res.status_code == 200


def test_login_page():
    res = app.test_client().get("/login")
    assert res.status_code == 200


def test_health():
    res = app.test_client().get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "OK"
