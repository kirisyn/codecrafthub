# CodeCraftHub

A small personalized learning platform where developers keep track of the
courses they want to learn. It is built as a **REST API** with Python and
Flask, and it stores everything in a plain JSON file, so there is no database
to install and nothing to configure.

The project is intentionally simple. Its goal is to teach the building blocks
of a REST API: HTTP methods, URL design, JSON request and response bodies,
status codes, validation and error handling. If you can read Python, you can
read the whole thing in one sitting.

## Features

- Create, read, update and delete courses (the classic **CRUD** operations)
- Each course tracks a name, description, target completion date and status
  (`Not Started`, `In Progress` or `Completed`)
- Ids and creation timestamps are generated automatically
- Every request is validated, and every error comes back as JSON with a clear
  message and the correct HTTP status code
- A statistics endpoint reports the total and the number of courses per status
- Data is saved to `courses.json`, which is created automatically on first run
- Writes are atomic, so a crash can never leave the data file half-written
- Comes with a curl-based test guide, a runnable curl script and a pytest suite

## Prerequisites

- **Python 3.10 or newer** (`python3 --version` to check)
- **curl** for trying the API from the command line. It is preinstalled on
  Linux and macOS and on recent versions of Windows.

## Installation

All commands are run from a terminal inside the project folder.

1. Get the project folder onto your machine and move into it:

   ```bash
   cd CodeCraftHub
   ```

2. Create a **virtual environment**. This is a private copy of Python for this
   project, so the packages you install here do not affect anything else:

   ```bash
   python3 -m venv .venv
   ```

3. Activate it. You need to do this every time you open a new terminal:

   ```bash
   source .venv/bin/activate        # Linux / macOS
   .venv\Scripts\activate           # Windows (Command Prompt / PowerShell)
   ```

   Your prompt now starts with `(.venv)`.

4. Install the dependencies listed in `requirements.txt` (Flask and Werkzeug):

   ```bash
   pip install -r requirements.txt
   ```

That is all. There is no database to set up.

## Running the application

With the virtual environment active:

```bash
python app.py
```

You will see:

```
- CodeCraftHub API is starting...
- Data will be stored in: /path/to/CodeCraftHub/courses.json
- API will be available at: http://localhost:5000
 * Running on http://127.0.0.1:5000
 * Debugger is active!
```

The API is now available at `http://localhost:5000`. The server runs in debug
mode, so it restarts automatically whenever you edit `app.py` and shows
detailed error pages. Press `Ctrl+C` to stop it.

(`flask --app app run --debug` starts the same server, just without the three
startup lines.)

On the first request, the app creates an empty `courses.json` next to
`app.py`. Open it in any editor to see your data as it is saved.

### Your first request

Leave the server running and open a **second terminal**:

```bash
curl http://localhost:5000/api/courses
```

You get `[]`, an empty list. Now add a course:

```bash
curl -X POST http://localhost:5000/api/courses \
  -H "Content-Type: application/json" \
  -d '{"name": "Flask Fundamentals", "description": "Learn REST APIs with Flask", "target_date": "2026-12-31", "status": "Not Started"}'
```

Run the first command again and your course is there.

## REST concepts in 60 seconds

If REST is new to you, this is the vocabulary used below.

- A **resource** is a thing the API manages. Here there is one: a course.
- Each resource has a **URL**. All courses live at `/api/courses`, and one
  particular course lives at `/api/courses/<id>`.
- The **HTTP method** says what you want to do with it: `GET` reads, `POST`
  creates, `PUT` replaces, `DELETE` removes.
- Data travels as **JSON** in the request body (for POST and PUT) and in the
  response body.
- The **status code** in the response tells you whether it worked: `2xx` is
  success, `4xx` means the request was wrong, `5xx` means the server failed.

## API endpoints

| Method | URL | What it does | Success |
|---|---|---|---|
| GET | `/api/courses` | List all courses | 200 |
| POST | `/api/courses` | Create a course | 201 |
| GET | `/api/courses/<id>` | Get one course | 200 |
| GET | `/api/courses/stats` | Totals and count per status | 200 |
| PUT | `/api/courses/<id>` | Update a course | 200 |
| DELETE | `/api/courses/<id>` | Delete a course | 200 |

### The course object

```json
{
  "id": 1,
  "name": "Flask Fundamentals",
  "description": "Learn REST APIs with Flask",
  "target_date": "2026-12-31",
  "status": "Not Started",
  "created_at": "2026-10-26T15:02:34"
}
```

| Field | Who sets it | Rules |
|---|---|---|
| `id` | server | Integer starting at 1. Never reused after a delete. |
| `name` | you | Required, non-empty text |
| `description` | you | Required, non-empty text |
| `target_date` | you | Required, a real date written as `YYYY-MM-DD` |
| `status` | you | Required, exactly one of `Not Started`, `In Progress`, `Completed` |
| `created_at` | server | Timestamp of creation. Never changes. |

### GET /api/courses

```bash
curl http://localhost:5000/api/courses
```

Response `200 OK`, a JSON list (possibly empty):

```json
[
  {"id": 1, "name": "Flask Fundamentals", "description": "Learn REST APIs with Flask",
   "target_date": "2026-12-31", "status": "Not Started", "created_at": "2026-10-26T15:02:34"},
  {"id": 2, "name": "Docker for Developers", "description": "Containerize Python applications",
   "target_date": "2027-03-15", "status": "In Progress", "created_at": "2026-10-26T15:02:34"}
]
```

### POST /api/courses

Send the four fields you control. The server adds `id` and `created_at`.

```bash
curl -X POST http://localhost:5000/api/courses \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Docker for Developers",
    "description": "Containerize Python applications",
    "target_date": "2027-03-15",
    "status": "In Progress"
  }'
```

Response `201 Created` with the new course:

```json
{
  "id": 2,
  "name": "Docker for Developers",
  "description": "Containerize Python applications",
  "target_date": "2027-03-15",
  "status": "In Progress",
  "created_at": "2026-10-26T15:02:34"
}
```

### GET /api/courses/<id>

```bash
curl http://localhost:5000/api/courses/2
```

Response `200 OK` with that one course, or `404 Not Found`:

```json
{"error": "Course with id 2 not found"}
```

### GET /api/courses/stats

```bash
curl http://localhost:5000/api/courses/stats
```

Response `200 OK`. All three statuses are always present, even at 0:

```json
{
  "total": 2,
  "by_status": {
    "Not Started": 1,
    "In Progress": 1,
    "Completed": 0
  }
}
```

Why does `/api/courses/stats` not clash with `/api/courses/<id>`? The id
route is declared as `<int:course_id>`, so Flask only matches it when the
last part of the URL is a whole number. The word `stats` never qualifies.

### PUT /api/courses/<id>

Send **only the fields you want to change**. The others keep their current
value, and `id` and `created_at` can never be changed.

```bash
curl -X PUT http://localhost:5000/api/courses/2 \
  -H "Content-Type: application/json" \
  -d '{"status": "Completed"}'
```

Response `200 OK` with the whole updated course:

```json
{
  "id": 2,
  "name": "Docker for Developers",
  "description": "Containerize Python applications",
  "target_date": "2027-03-15",
  "status": "Completed",
  "created_at": "2026-10-26T15:02:34"
}
```

Sending a body with none of the four fields, or with an empty value, is a
`400` error.

### DELETE /api/courses/<id>

```bash
curl -X DELETE http://localhost:5000/api/courses/2
```

Response `200 OK`:

```json
{"message": "Course with id 2 deleted"}
```

### Error responses

Every error has the same shape, `{"error": "..."}`, so a client can always
read the same field.

| Status | When | Example message |
|---|---|---|
| 400 | POST: a required field is missing or empty | `Missing required field(s): description, target_date` |
| 400 | PUT: a sent field is empty, or no known field was sent | `Field(s) cannot be empty: name` |
| 400 | Status is not one of the three allowed values | `Invalid status 'Done'. Must be one of: Not Started, In Progress, Completed` |
| 400 | Date is malformed or does not exist | `'target_date' must be a valid date in YYYY-MM-DD format` |
| 400 | Body is not valid JSON, or is a JSON list | `Request body must be valid JSON` |
| 404 | No course has that id | `Course with id 9999 not found` |
| 404 | The URL does not exist, or the id is not a number | `Resource not found` |
| 405 | Method not supported on that URL, e.g. PATCH | `Method not allowed` |
| 500 | `courses.json` cannot be read or written | `Could not read .../courses.json: ...` |

### Handy tip: pretty-print responses

curl prints JSON on one line. Pipe it through Python to make it readable:

```bash
curl -s http://localhost:5000/api/courses | python3 -m json.tool
```

## Testing

There are three ways to test, from most hands-on to most automated.

**1. Manually with curl.** `TESTING.md` walks through 27 tests, each with the
command to paste and the exact response to expect. Best for learning.

**2. The curl script.** Runs all of those tests in one go against a running
server and prints a pass/fail count. Start the server in one terminal, then in
another:

```bash
bash tests/test_api.sh
```

**3. pytest.** Automated tests that call the app directly without starting a
server. Each test uses its own temporary data file, so your real
`courses.json` is never touched:

```bash
pip install pytest
pytest -v
```

Expected output ends with `33 passed`.

## Troubleshooting

**`flask: command not found` or `No module named flask`**
The virtual environment is not active. Run `source .venv/bin/activate` (you
should see `(.venv)` in your prompt) and try again.

**`Address already in use`**
Another program, or an earlier copy of this server, is using port 5000. Either
stop it or run on a different port: `flask --app app run --debug --port 5001`.
Remember to use the new port in your curl commands too.

**`curl: (7) Failed to connect to localhost port 5000`**
The server is not running. Start it in a separate terminal and leave it open.

**`{"error": "Request body must be valid JSON"}` but my JSON looks right**
The usual causes:
- The `-H "Content-Type: application/json"` header is missing.
- On Windows Command Prompt, single quotes do not work. Wrap the body in
  double quotes and escape the inner ones: `-d "{\"name\": \"x\", ...}"`.
- A trailing comma after the last field, which JSON does not allow.

**`{"error": "Missing required field(s): ..."}`**
POST needs all four fields: `name`, `description`, `target_date` and
`status`. Only PUT accepts a subset.

**`{"error": "'target_date' must be a valid date in YYYY-MM-DD format"}`**
Use four-digit year, two-digit month, two-digit day, e.g. `2026-12-31`. The
date must also exist, so `2026-02-30` is rejected.

**`500` with `Could not read ... courses.json`**
The data file is corrupted, usually from a manual edit. Delete it and the app
recreates an empty one: `rm courses.json`. Your courses are lost, so back the
file up before editing it by hand.

**`pytest: ModuleNotFoundError: No module named 'app'`**
Run `pytest` from the project root (the folder containing `app.py` and
`pytest.ini`), not from inside `tests/`.

**The server did not pick up my code change**
`python app.py` runs in debug mode and reloads on every edit. If you used
`flask --app app run` instead, add `--debug` or restart the server by hand.

## Project structure

```
CodeCraftHub/
├── app.py              # The whole API: storage helpers, validation, routes
├── courses.json        # Your data. Created automatically; safe to delete.
├── requirements.txt    # Python packages to install (Flask, Werkzeug)
├── pytest.ini          # Tells pytest where to find app.py and the tests
├── README.md           # This file
├── TESTING.md          # Step-by-step curl tests with expected responses
├── tests/
│   ├── test_api.sh     # Runs all curl tests against a live server
│   └── test_api.py     # Automated pytest suite
└── .venv/              # Virtual environment (do not edit, do not commit)
```

### How app.py is organized

Read it top to bottom. Each section builds on the previous one.

1. **Configuration.** The path to `courses.json`, the list of valid statuses
   and the list of required fields live at the top so they are easy to find
   and change.
2. **Storage helpers.** `load_courses()` and `save_courses()` are the only
   functions that touch the disk. Everything else works with ordinary Python
   lists and dictionaries. This separation means you could later swap the
   JSON file for a real database by changing only these two functions.
3. **Validation.** One function, `validate_course_data()`, checks a request
   body and returns an error message or `None`. POST and PUT share it, so they
   always agree on what a valid course is.
4. **Error handlers.** Flask normally answers unknown URLs with an HTML page.
   These handlers make sure every error, including file problems, comes back
   as JSON.
5. **Routes.** One function per endpoint. Each follows the same pattern: read
   and validate the input, load the courses, change the list, save it, return
   a response with the right status code.

## Ideas for what to build next

Once the basics make sense, these are natural extensions, roughly in order of
difficulty:

- Add `PATCH /api/courses/<id>` and make PUT strict (all fields required), as
  the HTTP standard describes
- Filter the list with a query string, e.g. `/api/courses?status=Completed`
- Add a `GET /api/health` endpoint that returns `{"status": "ok"}`
- Extend `/api/courses/stats` with the number of overdue courses
- Reject target dates in the past
- Replace the JSON file with SQLite using only the standard library
