#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# CodeCraftHub API - curl test script
#
# Runs every test from TESTING.md in order against a running server.
# Start the server first in another terminal:
#     flask --app app run --debug
# then run:
#     bash tests/test_api.sh
#
# Each test prints the HTTP status code and the response body. The expected
# status is shown in the test title so you can compare at a glance.
# A summary at the end counts how many status codes matched.
# ---------------------------------------------------------------------------

BASE_URL="${BASE_URL:-http://localhost:5000}"
PASS=0
FAIL=0

# Helper: run a request and compare the status code.
#   check "<title>" <expected_status> <curl arguments...>
check() {
  local title="$1" expected="$2"
  shift 2
  echo "------------------------------------------------------------"
  echo "TEST: $title   (expect HTTP $expected)"
  # -s silent, -w appends the status code on its own line after the body
  local output
  output=$(curl -s -w $'\n%{http_code}' "$@")
  local body="${output%$'\n'*}"
  local status="${output##*$'\n'}"
  echo "HTTP $status"
  echo "$body"
  if [ "$status" = "$expected" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo ">>> FAILED: expected $expected, got $status"
  fi
}

JSON='Content-Type: application/json'

# ============================ SUCCESS PATH ==================================

check "GET all courses (may be empty on a fresh install)" 200 \
  "$BASE_URL/api/courses"

check "POST create course #1" 201 \
  -X POST "$BASE_URL/api/courses" -H "$JSON" -d '{
    "name": "Flask Fundamentals",
    "description": "Learn how to build REST APIs with Flask",
    "target_date": "2026-12-31",
    "status": "Not Started"
  }'

check "POST create course #2" 201 \
  -X POST "$BASE_URL/api/courses" -H "$JSON" -d '{
    "name": "Docker for Developers",
    "description": "Containerize Python applications",
    "target_date": "2027-03-15",
    "status": "In Progress"
  }'

# Grab the id of the course we just created so the rest of the script works
# even if courses.json already contained data.
LAST_ID=$(curl -s "$BASE_URL/api/courses" | python3 -c 'import json,sys; print(max(c["id"] for c in json.load(sys.stdin)))')
echo
echo "Using course id $LAST_ID for the single-course tests"

check "GET all courses (now contains the new ones)" 200 \
  "$BASE_URL/api/courses"

check "GET one course by id" 200 \
  "$BASE_URL/api/courses/$LAST_ID"

check "GET statistics (total and count per status)" 200 \
  "$BASE_URL/api/courses/stats"

check "PUT partial update (only the status)" 200 \
  -X PUT "$BASE_URL/api/courses/$LAST_ID" -H "$JSON" -d '{"status": "In Progress"}'

check "PUT update several fields at once" 200 \
  -X PUT "$BASE_URL/api/courses/$LAST_ID" -H "$JSON" -d '{
    "description": "Containerize Python applications - done!",
    "status": "Completed"
  }'

check "GET the course again (shows the update)" 200 \
  "$BASE_URL/api/courses/$LAST_ID"

check "DELETE the course" 200 \
  -X DELETE "$BASE_URL/api/courses/$LAST_ID"

check "GET statistics again (one fewer course)" 200 \
  "$BASE_URL/api/courses/stats"

# ============================ ERROR SCENARIOS ==============================

check "POST with missing fields" 400 \
  -X POST "$BASE_URL/api/courses" -H "$JSON" -d '{"name": "Only a name"}'

check "POST with empty required field" 400 \
  -X POST "$BASE_URL/api/courses" -H "$JSON" -d '{
    "name": "",
    "description": "Empty name is not allowed",
    "target_date": "2026-12-31",
    "status": "Not Started"
  }'

check "POST with invalid status" 400 \
  -X POST "$BASE_URL/api/courses" -H "$JSON" -d '{
    "name": "Kubernetes",
    "description": "Orchestration",
    "target_date": "2026-12-31",
    "status": "Done"
  }'

check "POST with badly formatted date" 400 \
  -X POST "$BASE_URL/api/courses" -H "$JSON" -d '{
    "name": "Kubernetes",
    "description": "Orchestration",
    "target_date": "31/12/2026",
    "status": "Not Started"
  }'

check "POST with impossible date (Feb 30)" 400 \
  -X POST "$BASE_URL/api/courses" -H "$JSON" -d '{
    "name": "Kubernetes",
    "description": "Orchestration",
    "target_date": "2026-02-30",
    "status": "Not Started"
  }'

check "POST with body that is not JSON" 400 \
  -X POST "$BASE_URL/api/courses" -H "$JSON" -d 'this is not json'

check "POST with a JSON list instead of an object" 400 \
  -X POST "$BASE_URL/api/courses" -H "$JSON" -d '[1, 2, 3]'

check "GET course that does not exist" 404 \
  "$BASE_URL/api/courses/9999"

check "GET course with non-numeric id" 404 \
  "$BASE_URL/api/courses/abc"

check "PUT course that does not exist" 404 \
  -X PUT "$BASE_URL/api/courses/9999" -H "$JSON" -d '{
    "name": "Ghost",
    "description": "Does not exist",
    "target_date": "2026-12-31",
    "status": "Not Started"
  }'

check "PUT with invalid status on existing course" 400 \
  -X PUT "$BASE_URL/api/courses/$((LAST_ID - 1))" -H "$JSON" -d '{"status": "Done"}'

check "PUT with an empty field" 400 \
  -X PUT "$BASE_URL/api/courses/$((LAST_ID - 1))" -H "$JSON" -d '{"name": ""}'

check "PUT with no known fields" 400 \
  -X PUT "$BASE_URL/api/courses/$((LAST_ID - 1))" -H "$JSON" -d '{"colour": "blue"}'

check "DELETE course that does not exist" 404 \
  -X DELETE "$BASE_URL/api/courses/9999"

check "DELETE the same course twice (second time fails)" 404 \
  -X DELETE "$BASE_URL/api/courses/$LAST_ID"

check "POST to /stats is not supported" 405 \
  -X POST "$BASE_URL/api/courses/stats" -H "$JSON" -d '{}'

check "PATCH is not supported" 405 \
  -X PATCH "$BASE_URL/api/courses/1" -H "$JSON" -d '{"status": "Completed"}'

check "Unknown URL" 404 \
  "$BASE_URL/api/nothing-here"

# ============================ SUMMARY =======================================
echo
echo "============================================================"
echo "Passed: $PASS   Failed: $FAIL"
[ "$FAIL" -eq 0 ]
