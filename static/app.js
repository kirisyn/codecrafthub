/* ---------------------------------------------------------------------------
   CodeCraftHub dashboard
   Plain JavaScript, no framework. Everything the page does goes through the
   REST API with fetch():

     GET    /api/courses          load the list
     GET    /api/courses/stats    load the numbers in the statistics strip
     POST   /api/courses          add a course
     PUT    /api/courses/<id>     save edits to a course
     DELETE /api/courses/<id>     remove a course

   API_BASE is empty because the page is served by the same Flask app. If you
   host this page somewhere else, set it to e.g. "http://localhost:5000".
   --------------------------------------------------------------------------- */

const API_BASE = "";

// ---- Grab the page elements once, so the rest of the code can use them ----

const form        = document.getElementById("course-form");
const formTitle   = document.getElementById("form-title");
const submitBtn   = document.getElementById("submit-btn");
const cancelBtn   = document.getElementById("cancel-btn");
const refreshBtn  = document.getElementById("refresh-btn");
const courseList  = document.getElementById("course-list");
const emptyState  = document.getElementById("empty-state");
const messageBox  = document.getElementById("message");

const fields = {
  id:          document.getElementById("course-id"),
  name:        document.getElementById("name"),
  description: document.getElementById("description"),
  target_date: document.getElementById("target_date"),
  status:      document.getElementById("status"),
};

// ---- Talking to the API ---------------------------------------------------

/**
 * Send a request to the API and return the parsed JSON body.
 * Throws an Error whose message is the API's "error" field when the
 * response is not 2xx, so every caller can simply try/catch.
 */
async function api(method, path, body) {
  const options = { method, headers: {} };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  const response = await fetch(API_BASE + path, options);

  // A failed request still has a JSON body like {"error": "..."}.
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || `Request failed with status ${response.status}`);
  }
  return data;
}

// ---- Rendering ------------------------------------------------------------

/** Reload the course list and the statistics from the server. */
async function refresh() {
  try {
    const [courses, stats] = await Promise.all([
      api("GET", "/api/courses"),
      api("GET", "/api/courses/stats"),
    ]);
    renderCourses(courses);
    renderStats(stats);
  } catch (err) {
    showMessage(`Could not load courses: ${err.message}`, "error");
  }
}

function renderStats(stats) {
  document.getElementById("stat-total").textContent       = stats.total;
  document.getElementById("stat-not-started").textContent = stats.by_status["Not Started"];
  document.getElementById("stat-in-progress").textContent = stats.by_status["In Progress"];
  document.getElementById("stat-completed").textContent   = stats.by_status["Completed"];
}

function renderCourses(courses) {
  courseList.innerHTML = "";                       // clear the old cards
  emptyState.classList.toggle("hidden", courses.length > 0);

  // Show the nearest target date first.
  courses.sort((a, b) => a.target_date.localeCompare(b.target_date));

  for (const course of courses) {
    courseList.appendChild(createCourseCard(course));
  }
}

/** Build the HTML card for one course. */
function createCourseCard(course) {
  const card = document.createElement("article");
  card.className = "course";

  // Flag courses whose target date has passed and are not finished.
  const today = new Date().toISOString().slice(0, 10);     // "YYYY-MM-DD"
  const overdue = course.status !== "Completed" && course.target_date < today;

  // textContent (not innerHTML) is used for everything typed by the user, so
  // a course named "<script>" is displayed literally instead of executed.
  const top = document.createElement("div");
  top.className = "course-top";

  const title = document.createElement("h3");
  title.textContent = course.name;

  const badge = document.createElement("span");
  badge.className = "badge";
  badge.dataset.status = course.status;              // drives the badge colour
  badge.textContent = course.status;

  top.append(title, badge);

  const description = document.createElement("p");
  description.className = "course-description";
  description.textContent = course.description;

  const meta = document.createElement("div");
  meta.className = "course-meta" + (overdue ? " overdue" : "");
  meta.textContent = (overdue ? "Overdue, target was " : "Target: ") + formatDate(course.target_date);

  const actions = document.createElement("div");
  actions.className = "course-actions";

  const editBtn = document.createElement("button");
  editBtn.className = "btn btn-small";
  editBtn.textContent = "Edit";
  editBtn.addEventListener("click", () => startEditing(course));

  const deleteBtn = document.createElement("button");
  deleteBtn.className = "btn btn-small btn-danger";
  deleteBtn.textContent = "Delete";
  deleteBtn.addEventListener("click", () => deleteCourse(course));

  actions.append(editBtn, deleteBtn);
  card.append(top, description, meta, actions);
  return card;
}

/** Turn "2026-12-31" into a friendlier "31 Dec 2026" in the browser's locale. */
function formatDate(isoDate) {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString(undefined, {
    day: "numeric", month: "short", year: "numeric",
  });
}

// ---- Messages -------------------------------------------------------------

let messageTimer;

function showMessage(text, type) {
  messageBox.textContent = text;
  messageBox.className = `message message-${type}`;
  clearTimeout(messageTimer);
  messageTimer = setTimeout(() => messageBox.classList.add("hidden"), 4000);
}

// ---- Create & update (the form) ------------------------------------------

/** Put a course into the form and switch it to "edit" mode. */
function startEditing(course) {
  fields.id.value          = course.id;
  fields.name.value        = course.name;
  fields.description.value = course.description;
  fields.target_date.value = course.target_date;
  fields.status.value      = course.status;

  formTitle.textContent = `Edit course #${course.id}`;
  submitBtn.textContent = "Save changes";
  cancelBtn.hidden = false;

  form.scrollIntoView({ behavior: "smooth", block: "start" });
  fields.name.focus();
}

/** Clear the form and switch it back to "add" mode. */
function resetForm() {
  form.reset();
  fields.id.value = "";
  formTitle.textContent = "Add a course";
  submitBtn.textContent = "Add course";
  cancelBtn.hidden = true;
}

/** Collect the form values into the JSON shape the API expects. */
function readForm() {
  return {
    name:        fields.name.value.trim(),
    description: fields.description.value.trim(),
    target_date: fields.target_date.value,
    status:      fields.status.value,
  };
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();                          // stay on the page

  // Let the browser show its own "please fill out this field" bubbles first.
  if (!form.reportValidity()) return;

  const data = readForm();
  const editingId = fields.id.value;
  submitBtn.disabled = true;

  try {
    if (editingId) {
      await api("PUT", `/api/courses/${editingId}`, data);
      showMessage(`Course "${data.name}" updated.`, "success");
    } else {
      const created = await api("POST", "/api/courses", data);
      showMessage(`Course "${created.name}" added with id ${created.id}.`, "success");
    }
    resetForm();
    await refresh();
  } catch (err) {
    showMessage(err.message, "error");            // e.g. "Invalid status ..."
  } finally {
    submitBtn.disabled = false;
  }
});

cancelBtn.addEventListener("click", resetForm);
refreshBtn.addEventListener("click", refresh);

// ---- Delete ---------------------------------------------------------------

async function deleteCourse(course) {
  if (!confirm(`Delete "${course.name}"? This cannot be undone.`)) return;

  try {
    await api("DELETE", `/api/courses/${course.id}`);
    showMessage(`Course "${course.name}" deleted.`, "success");
    // If the deleted course was open in the form, clear it.
    if (fields.id.value === String(course.id)) resetForm();
    await refresh();
  } catch (err) {
    showMessage(err.message, "error");
  }
}

// ---- Start ----------------------------------------------------------------

refresh();
