"""
Automated tests for the CodeCraftHub API using pytest.

These mirror the curl tests in TESTING.md but need no running server:
Flask's test client calls the app directly. Each test gets its own empty
temporary courses.json, so tests never interfere with each other or with
your real data.

Run with:
    pip install pytest
    pytest -v
"""

import pytest

import app as codecraft  # the module app.py


# A valid course payload reused across many tests.
VALID_COURSE = {
    "name": "Flask Fundamentals",
    "description": "Learn how to build REST APIs with Flask",
    "target_date": "2026-12-31",
    "status": "Not Started",
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Give each test a fresh Flask test client backed by a temporary file."""
    # Point the app at a file inside pytest's temporary directory.
    monkeypatch.setattr(codecraft, "DATA_FILE", str(tmp_path / "courses.json"))
    codecraft.app.config["TESTING"] = True
    return codecraft.app.test_client()


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------

def test_get_all_courses_empty(client):
    response = client.get("/api/courses")
    assert response.status_code == 200
    assert response.get_json() == []


def test_create_course(client):
    response = client.post("/api/courses", json=VALID_COURSE)
    assert response.status_code == 201
    course = response.get_json()
    assert course["id"] == 1                      # ids start at 1
    assert course["name"] == VALID_COURSE["name"]
    assert course["status"] == "Not Started"
    assert "created_at" in course                 # auto-generated


def test_ids_increment(client):
    first = client.post("/api/courses", json=VALID_COURSE).get_json()
    second = client.post("/api/courses", json={**VALID_COURSE, "name": "Docker"}).get_json()
    assert (first["id"], second["id"]) == (1, 2)


def test_get_single_course(client):
    created = client.post("/api/courses", json=VALID_COURSE).get_json()
    response = client.get(f"/api/courses/{created['id']}")
    assert response.status_code == 200
    assert response.get_json() == created


def test_update_course_partial(client):
    """PUT with only one field changes that field and keeps the rest."""
    created = client.post("/api/courses", json=VALID_COURSE).get_json()
    response = client.put(f"/api/courses/{created['id']}", json={"status": "In Progress"})
    assert response.status_code == 200
    updated = response.get_json()
    assert updated["status"] == "In Progress"
    assert updated["name"] == created["name"]              # untouched
    assert updated["description"] == created["description"]
    assert updated["target_date"] == created["target_date"]
    assert updated["id"] == created["id"]                  # never changes
    assert updated["created_at"] == created["created_at"]  # never changes


def test_update_course_several_fields(client):
    created = client.post("/api/courses", json=VALID_COURSE).get_json()
    update = {"status": "Completed", "description": "Done!"}
    response = client.put(f"/api/courses/{created['id']}", json=update)
    assert response.status_code == 200
    updated = response.get_json()
    assert updated["status"] == "Completed"
    assert updated["description"] == "Done!"
    assert updated["name"] == created["name"]


def test_update_cannot_change_id_or_created_at(client):
    created = client.post("/api/courses", json=VALID_COURSE).get_json()
    response = client.put(f"/api/courses/{created['id']}",
                          json={"id": 99, "created_at": "1999-01-01", "status": "Completed"})
    assert response.status_code == 200
    updated = response.get_json()
    assert updated["id"] == created["id"]
    assert updated["created_at"] == created["created_at"]


def test_delete_course(client):
    created = client.post("/api/courses", json=VALID_COURSE).get_json()
    response = client.delete(f"/api/courses/{created['id']}")
    assert response.status_code == 200
    # The course is really gone.
    assert client.get(f"/api/courses/{created['id']}").status_code == 404
    assert client.get("/api/courses").get_json() == []


def test_data_persists_in_file(client):
    """The JSON file, not memory, is the source of truth."""
    client.post("/api/courses", json=VALID_COURSE)
    assert codecraft.load_courses()[0]["name"] == VALID_COURSE["name"]


# ---------------------------------------------------------------------------
# Dashboard frontend
# ---------------------------------------------------------------------------

def test_dashboard_page_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.content_type.startswith("text/html")
    assert b"CodeCraftHub" in response.data


def test_static_assets_are_served(client):
    assert client.get("/static/style.css").status_code == 200
    assert client.get("/static/app.js").status_code == 200


def test_cors_headers_present(client):
    response = client.get("/api/courses")
    assert response.headers["Access-Control-Allow-Origin"] == "*"
    assert "PUT" in response.headers["Access-Control-Allow-Methods"]


def test_cors_preflight(client):
    """Browsers send OPTIONS before a cross-origin PUT or DELETE."""
    response = client.options("/api/courses/1")
    assert response.status_code == 200
    assert "DELETE" in response.headers["Access-Control-Allow-Methods"]


# ---------------------------------------------------------------------------
# Statistics endpoint
# ---------------------------------------------------------------------------

EMPTY_STATS = {"total": 0, "by_status": {"Not Started": 0, "In Progress": 0, "Completed": 0}}


def test_stats_empty(client):
    """Every status is present with a count of 0 when there are no courses."""
    response = client.get("/api/courses/stats")
    assert response.status_code == 200
    assert response.get_json() == EMPTY_STATS


def test_stats_counts_by_status(client):
    for status in ["Not Started", "In Progress", "In Progress", "Completed"]:
        client.post("/api/courses", json={**VALID_COURSE, "status": status})
    stats = client.get("/api/courses/stats").get_json()
    assert stats["total"] == 4
    assert stats["by_status"] == {"Not Started": 1, "In Progress": 2, "Completed": 1}


def test_stats_follow_updates_and_deletes(client):
    first = client.post("/api/courses", json=VALID_COURSE).get_json()
    second = client.post("/api/courses", json=VALID_COURSE).get_json()
    client.put(f"/api/courses/{first['id']}", json={"status": "Completed"})
    client.delete(f"/api/courses/{second['id']}")
    stats = client.get("/api/courses/stats").get_json()
    assert stats == {"total": 1, "by_status": {"Not Started": 0, "In Progress": 0, "Completed": 1}}


def test_stats_does_not_shadow_course_ids(client):
    """/api/courses/stats and /api/courses/<id> must both keep working."""
    created = client.post("/api/courses", json=VALID_COURSE).get_json()
    assert client.get(f"/api/courses/{created['id']}").status_code == 200
    assert "total" in client.get("/api/courses/stats").get_json()


# ---------------------------------------------------------------------------
# Error scenarios: bad input (400)
# ---------------------------------------------------------------------------

def test_missing_fields(client):
    response = client.post("/api/courses", json={"name": "Only a name"})
    assert response.status_code == 400
    assert "Missing required field(s)" in response.get_json()["error"]


def test_empty_field_counts_as_missing(client):
    response = client.post("/api/courses", json={**VALID_COURSE, "name": ""})
    assert response.status_code == 400
    assert "name" in response.get_json()["error"]


def test_invalid_status(client):
    response = client.post("/api/courses", json={**VALID_COURSE, "status": "Done"})
    assert response.status_code == 400
    assert "Invalid status" in response.get_json()["error"]


@pytest.mark.parametrize("bad_date", ["31/12/2026", "2026-02-30", "tomorrow", "2026-13-01"])
def test_invalid_date(client, bad_date):
    response = client.post("/api/courses", json={**VALID_COURSE, "target_date": bad_date})
    assert response.status_code == 400
    assert "target_date" in response.get_json()["error"]


def test_body_not_json(client):
    response = client.post("/api/courses", data="not json", content_type="text/plain")
    assert response.status_code == 400


def test_body_is_list_not_object(client):
    response = client.post("/api/courses", json=[1, 2, 3])
    assert response.status_code == 400


def test_put_with_invalid_status(client):
    created = client.post("/api/courses", json=VALID_COURSE).get_json()
    response = client.put(f"/api/courses/{created['id']}", json={"status": "Done"})
    assert response.status_code == 400
    assert "Invalid status" in response.get_json()["error"]


def test_put_with_empty_field(client):
    created = client.post("/api/courses", json=VALID_COURSE).get_json()
    response = client.put(f"/api/courses/{created['id']}", json={"name": ""})
    assert response.status_code == 400
    assert "cannot be empty" in response.get_json()["error"]


def test_put_with_no_known_fields(client):
    created = client.post("/api/courses", json=VALID_COURSE).get_json()
    response = client.put(f"/api/courses/{created['id']}", json={"colour": "blue"})
    assert response.status_code == 400
    assert "at least one" in response.get_json()["error"]


# ---------------------------------------------------------------------------
# Error scenarios: not found (404) and wrong method (405)
# ---------------------------------------------------------------------------

def test_get_unknown_course(client):
    response = client.get("/api/courses/9999")
    assert response.status_code == 404
    assert response.get_json()["error"] == "Course with id 9999 not found"


def test_put_unknown_course(client):
    assert client.put("/api/courses/9999", json={"status": "Completed"}).status_code == 404


def test_delete_unknown_course(client):
    assert client.delete("/api/courses/9999").status_code == 404


def test_non_numeric_id(client):
    assert client.get("/api/courses/abc").status_code == 404


def test_unknown_url_returns_json(client):
    response = client.get("/api/nothing-here")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Resource not found"}


def test_patch_not_allowed(client):
    assert client.patch("/api/courses/1", json={}).status_code == 405


# ---------------------------------------------------------------------------
# Error scenario: file problems (500)
# ---------------------------------------------------------------------------

def test_corrupted_file(client):
    with open(codecraft.DATA_FILE, "w") as f:
        f.write("{not valid json")
    response = client.get("/api/courses")
    assert response.status_code == 500
    assert "Could not read" in response.get_json()["error"]


def test_file_created_automatically(client, tmp_path):
    assert not (tmp_path / "courses.json").exists()
    client.get("/api/courses")
    assert (tmp_path / "courses.json").exists()
