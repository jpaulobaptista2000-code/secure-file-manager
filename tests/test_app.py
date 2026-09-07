import pytest

from secure_file_manager import create_app


@pytest.fixture
def client():
    return create_app({"TESTING": True}).test_client()


def test_skeleton_status_does_not_claim_a_working_file_manager(client):
    response = client.get("/health", base_url="https://localhost")
    assert response.status_code == 200
    assert response.json == {"status": "ok", "stage": "checkpoint-1-foundation"}


@pytest.mark.parametrize("path", ["/", "/health", "/missing"])
def test_security_headers_on_success_and_error_responses(client, path):
    response = client.get(path, base_url="https://localhost")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "script-src 'none'" in response.headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "Set-Cookie" not in response.headers  # No authenticated session yet.


def test_untrusted_host_is_rejected(client):
    response = client.get("/health", base_url="https://attacker.invalid")
    assert response.status_code == 400
    assert response.json == {"error": "Bad Request"}


def test_missing_resource_does_not_reflect_input(client):
    response = client.get("/private-secret-path", base_url="https://localhost")
    assert response.status_code == 404
    assert "private-secret-path" not in response.get_data(as_text=True)


def test_unimplemented_mutation_has_no_effect(client):
    response = client.post("/health", base_url="https://localhost")
    assert response.status_code == 405
    assert "GET" in response.headers["Allow"]


def test_internal_exception_is_not_returned_to_client():
    app = create_app({"TESTING": True, "PROPAGATE_EXCEPTIONS": False})

    @app.get("/test-error")
    def test_error():
        raise RuntimeError("a private diagnostic value")

    response = app.test_client().get("/test-error", base_url="https://localhost")
    assert response.status_code == 500
    assert response.json == {"error": "Internal server error"}
    assert "private diagnostic" not in response.get_data(as_text=True)
