"""
CodeCraftHub - a tiny personalized learning platform.

A Flask REST API that lets developers track the courses they want to learn.
All data lives in a plain JSON file (courses.json) next to this script, so
there is no database to install.

Run it with:
    flask --app app run --debug
and then try, for example:
    curl http://localhost:5000/api/courses
"""

import json                      # read/write the JSON file
import os                        # check whether the data file exists
from datetime import date, datetime  # validate target_date, generate created_at

from flask import Flask, jsonify, request, send_from_directory

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

app = Flask(__name__)

# Build an absolute path to courses.json that sits in the same folder as
# app.py. Using an absolute path means the app works no matter which
# directory you start it from.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "courses.json")

# The only values a course's "status" field is allowed to hold.
VALID_STATUSES = ("Not Started", "In Progress", "Completed")

# Fields a client MUST send when creating or fully updating a course.
REQUIRED_FIELDS = ("name", "description", "target_date", "status")


# ---------------------------------------------------------------------------
# Custom exception for storage problems
# ---------------------------------------------------------------------------

class StorageError(Exception):
    """Raised when courses.json cannot be read or written.

    Having our own exception type lets the route functions stay simple: they
    don't need try/except blocks, because a single Flask error handler
    (see handle_storage_error below) turns this into a 500 JSON response.
    """


# ---------------------------------------------------------------------------
# JSON file helpers (the only code that touches the disk)
# ---------------------------------------------------------------------------

def ensure_data_file():
    """Create courses.json with an empty list if it doesn't exist yet."""
    if not os.path.exists(DATA_FILE):
        save_courses([])


def load_courses():
    """Read every course from courses.json and return them as a Python list."""
    ensure_data_file()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        # OSError  -> permission problems, disk errors, etc.
        # JSONDecodeError -> someone hand-edited the file and broke the JSON.
        raise StorageError(f"Could not read {DATA_FILE}: {exc}") from exc

    # Defensive check: the file should always contain a JSON array.
    if not isinstance(data, list):
        raise StorageError(f"{DATA_FILE} does not contain a JSON list")
    return data


def save_courses(courses):
    """Write the whole list of courses back to courses.json.

    We write to a temporary file first and then rename it over the real one.
    A rename is atomic on every major OS, so if the program crashes halfway
    through writing, courses.json is never left half-written.
    """
    tmp_file = DATA_FILE + ".tmp"
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(courses, f, indent=2)
        os.replace(tmp_file, DATA_FILE)
    except OSError as exc:
        raise StorageError(f"Could not write {DATA_FILE}: {exc}") from exc


def next_id(courses):
    """Return the next free id: 1 for an empty list, otherwise max id + 1."""
    if not courses:
        return 1
    return max(course["id"] for course in courses) + 1


def find_course(courses, course_id):
    """Return the course with the given id, or None if it doesn't exist."""
    for course in courses:
        if course["id"] == course_id:
            return course
    return None


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_course_data(data, partial=False):
    """Check the JSON body of a POST or PUT request.

    Returns an error message (a string) if something is wrong, or None if
    the data is valid.

    partial=False (POST): every required field must be present.
    partial=True  (PUT):  only the fields that are present are checked, so a
                          client can send just {"status": "In Progress"}.
    """
    # The body must be a JSON object, e.g. {"name": "..."}; not a list/string.
    if not isinstance(data, dict):
        return "Request body must be a JSON object"

    if partial:
        # A PUT that changes nothing is almost certainly a mistake.
        fields_to_check = [f for f in REQUIRED_FIELDS if f in data]
        if not fields_to_check:
            return f"Provide at least one of: {', '.join(REQUIRED_FIELDS)}"
        # A field that IS sent must not be empty.
        empty = [f for f in fields_to_check if not data.get(f)]
        if empty:
            return f"Field(s) cannot be empty: {', '.join(empty)}"
    else:
        # 1. Every required field must be present and not empty.
        missing = [f for f in REQUIRED_FIELDS if not data.get(f)]
        if missing:
            return f"Missing required field(s): {', '.join(missing)}"
        fields_to_check = list(REQUIRED_FIELDS)

    # 2. Text fields must actually be strings.
    for field in ("name", "description"):
        if field in fields_to_check and not isinstance(data[field], str):
            return f"'{field}' must be a string"

    # 3. status must be one of the allowed values.
    if "status" in fields_to_check and data["status"] not in VALID_STATUSES:
        return f"Invalid status '{data['status']}'. Must be one of: {', '.join(VALID_STATUSES)}"

    # 4. target_date must be a real date written as YYYY-MM-DD.
    #    date.fromisoformat also rejects impossible dates such as 2026-02-30.
    if "target_date" in fields_to_check:
        try:
            date.fromisoformat(str(data["target_date"]))
        except ValueError:
            return "'target_date' must be a valid date in YYYY-MM-DD format"

    return None  # everything is fine


# ---------------------------------------------------------------------------
# Error handlers - these turn exceptions into clean JSON responses
# ---------------------------------------------------------------------------

@app.errorhandler(StorageError)
def handle_storage_error(exc):
    """File read/write problems -> HTTP 500 with a JSON body."""
    return jsonify(error=str(exc)), 500


@app.errorhandler(404)
def handle_not_found(exc):
    """Unknown URL -> JSON instead of Flask's default HTML page."""
    return jsonify(error="Resource not found"), 404


@app.errorhandler(405)
def handle_method_not_allowed(exc):
    """Wrong HTTP method for a URL (e.g. PATCH where only PUT exists)."""
    return jsonify(error="Method not allowed"), 405


# ---------------------------------------------------------------------------
# Dashboard (the HTML/CSS/JS frontend in the static/ folder)
# ---------------------------------------------------------------------------

@app.get("/")
def dashboard():
    """Serve the dashboard page. Flask already serves everything inside the
    static/ folder at /static/..., so the page's CSS and JS files need no
    extra routes of their own."""
    return send_from_directory(app.static_folder, "index.html")


@app.after_request
def add_cors_headers(response):
    """Allow the dashboard to call the API even when it is opened from
    another origin, e.g. a file on disk or a page hosted on Bolt.new.

    Browsers block cross-origin requests unless the server sends these
    CORS (Cross-Origin Resource Sharing) headers. Flask answers the
    browser's OPTIONS "preflight" request automatically; this hook just
    adds the headers to every response, including that one.
    Not needed when the page is served by this same app at /.
    """
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@app.get("/api/courses")
def get_courses():
    """GET /api/courses -> list every course (200)."""
    courses = load_courses()
    return jsonify(courses), 200


@app.get("/api/courses/stats")
def get_course_stats():
    """GET /api/courses/stats -> totals and a count per status (200).

    This route is declared before /api/courses/<int:course_id>, but the order
    does not actually matter here: that route only matches integers, so the
    word "stats" can never be mistaken for a course id.
    """
    courses = load_courses()

    # Start every status at 0 so the response always has the same shape,
    # even when there are no courses at all.
    by_status = {status: 0 for status in VALID_STATUSES}
    for course in courses:
        by_status[course["status"]] += 1

    return jsonify(total=len(courses), by_status=by_status), 200


@app.get("/api/courses/<int:course_id>")
def get_course(course_id):
    """GET /api/courses/<id> -> one course (200) or 404 if the id is unknown.

    The <int:course_id> converter means Flask only matches this route when
    the URL segment is an integer, and hands it to us already converted.
    """
    courses = load_courses()
    course = find_course(courses, course_id)
    if course is None:
        return jsonify(error=f"Course with id {course_id} not found"), 404
    return jsonify(course), 200


@app.post("/api/courses")
def create_course():
    """POST /api/courses -> create a course (201) or 400 on bad input."""
    # silent=True makes get_json return None instead of raising when the
    # body is missing or is not valid JSON, so we can answer with our own 400.
    data = request.get_json(silent=True)
    if data is None:
        return jsonify(error="Request body must be valid JSON"), 400

    error = validate_course_data(data)
    if error:
        return jsonify(error=error), 400

    courses = load_courses()

    # Build the course ourselves rather than storing the raw request body,
    # so clients cannot sneak in extra fields or choose their own id.
    course = {
        "id": next_id(courses),
        "name": data["name"].strip(),
        "description": data["description"].strip(),
        "target_date": data["target_date"],
        "status": data["status"],
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    courses.append(course)
    save_courses(courses)

    # 201 Created is the conventional status for a successful POST.
    return jsonify(course), 201


@app.put("/api/courses/<int:course_id>")
def update_course(course_id):
    """PUT /api/courses/<id> -> update a course (200).

    Send only the fields you want to change, e.g. {"status": "Completed"}.
    Fields you leave out keep their current value. id and created_at can
    never be changed by the client.

    (Strict REST would reserve partial updates for PATCH and make PUT replace
    the whole resource. Accepting partial bodies on PUT is friendlier for a
    first API, and it is what many real-world APIs do too.)
    """
    data = request.get_json(silent=True)
    if data is None:
        return jsonify(error="Request body must be valid JSON"), 400

    error = validate_course_data(data, partial=True)
    if error:
        return jsonify(error=error), 400

    courses = load_courses()
    course = find_course(courses, course_id)
    if course is None:
        return jsonify(error=f"Course with id {course_id} not found"), 404

    # Copy over only the fields that were sent. The dictionary is updated in
    # place; it is the same object that sits inside the `courses` list, so
    # saving the list persists the change.
    for field in REQUIRED_FIELDS:
        if field in data:
            value = data[field]
            course[field] = value.strip() if isinstance(value, str) else value
    save_courses(courses)

    return jsonify(course), 200


@app.delete("/api/courses/<int:course_id>")
def delete_course(course_id):
    """DELETE /api/courses/<id> -> remove a course (200) or 404."""
    courses = load_courses()
    course = find_course(courses, course_id)
    if course is None:
        return jsonify(error=f"Course with id {course_id} not found"), 404

    courses.remove(course)
    save_courses(courses)

    # Returning a small message is friendlier for beginners than an empty
    # 204 response, although 204 No Content would also be correct REST style.
    return jsonify(message=f"Course with id {course_id} deleted"), 200


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Make sure courses.json exists before the first request arrives.
    ensure_data_file()
    print("- CodeCraftHub API is starting...")
    print(f"- Data will be stored in: {DATA_FILE}")
    print("- API will be available at: http://localhost:5000")
    print("- Dashboard: open http://localhost:5000 in your browser")
    # debug=True reloads the server when you edit the code and shows
    # detailed error pages. Turn it off for anything public.
    app.run(debug=True)
