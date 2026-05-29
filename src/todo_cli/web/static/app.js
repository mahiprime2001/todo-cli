"use strict";

// --- tiny API client -------------------------------------------------------
const api = {
  async list(params) {
    const qs = new URLSearchParams(params).toString();
    return get(`/api/tasks?${qs}`);
  },
  create: (body) => send("POST", "/api/tasks", body),
  update: (id, body) => send("PATCH", `/api/tasks/${id}`, body),
  remove: (id) => send("DELETE", `/api/tasks/${id}`),
  stats: () => get("/api/stats"),
};

async function get(url) {
  const res = await fetch(url);
  if (!res.ok) throw await toError(res);
  return res.json();
}

async function send(method, url, body) {
  const res = await fetch(url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw await toError(res);
  return res.status === 204 ? null : res.json();
}

async function toError(res) {
  try {
    const data = await res.json();
    return new Error(data.detail || res.statusText);
  } catch {
    return new Error(res.statusText);
  }
}

// --- DOM references --------------------------------------------------------
const $ = (id) => document.getElementById(id);
const els = {
  form: $("add-form"),
  text: $("text"),
  priority: $("priority"),
  due: $("due"),
  tags: $("tags"),
  search: $("search"),
  sort: $("sort"),
  showAll: $("show-all"),
  list: $("task-list"),
  empty: $("empty"),
  stats: $("stats"),
};

// --- rendering -------------------------------------------------------------
function taskNode(task) {
  const el = document.createElement("div");
  el.className = `task pri-${task.priority}${task.done ? " done" : ""}`;

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.checked = task.done;
  checkbox.title = task.done ? "Reopen" : "Complete";
  checkbox.addEventListener("change", () =>
    guard(() => api.update(task.id, { done: checkbox.checked }).then(refresh))
  );

  const main = document.createElement("div");
  main.className = "task-main";

  const text = document.createElement("div");
  text.className = "task-text";
  text.textContent = task.text;
  main.appendChild(text);

  const meta = document.createElement("div");
  meta.className = "task-meta";
  meta.appendChild(badge(task.priority, "badge"));
  if (task.due) {
    const cls = task.is_overdue ? "due-overdue" : task.is_due_soon ? "due-soon" : "";
    meta.appendChild(badge(`📅 ${task.due}${task.is_overdue ? " (overdue)" : ""}`, `badge ${cls}`));
  }
  task.tags.forEach((t) => meta.appendChild(badge(`#${t}`, "badge tag")));
  if (task.notes) meta.appendChild(badge("📝 note", "badge"));
  main.appendChild(meta);

  const actions = document.createElement("div");
  actions.className = "task-actions";
  const del = document.createElement("button");
  del.className = "icon-btn";
  del.textContent = "🗑";
  del.title = "Delete";
  del.addEventListener("click", () =>
    guard(() => api.remove(task.id).then(refresh))
  );
  actions.appendChild(del);

  el.append(checkbox, main, actions);
  return el;
}

function badge(textContent, className) {
  const span = document.createElement("span");
  span.className = className;
  span.textContent = textContent;
  return span;
}

function renderStats(s) {
  els.stats.innerHTML = "";
  const cards = [
    { label: "Pending", num: s.pending },
    { label: "Done", num: s.done },
    { label: "Overdue", num: s.overdue, cls: "overdue" },
  ];
  for (const c of cards) {
    const div = document.createElement("div");
    div.className = `stat ${c.cls || ""}`;
    div.innerHTML = `<div class="num">${c.num}</div><div class="label">${c.label}</div>`;
    els.stats.appendChild(div);
  }
}

// --- data flow -------------------------------------------------------------
async function refresh() {
  const params = { all: els.showAll.checked, sort: els.sort.value };
  if (els.search.value.trim()) params.search = els.search.value.trim();

  const [tasks, stats] = await Promise.all([api.list(params), api.stats()]);

  els.list.innerHTML = "";
  tasks.forEach((t) => els.list.appendChild(taskNode(t)));
  els.empty.hidden = tasks.length > 0;
  renderStats(stats);
}

async function guard(fn) {
  try {
    await fn();
  } catch (err) {
    alert(err.message || "Something went wrong.");
  }
}

// --- events ----------------------------------------------------------------
els.form.addEventListener("submit", (e) => {
  e.preventDefault();
  const body = {
    text: els.text.value.trim(),
    priority: els.priority.value,
    due: els.due.value.trim() || null,
    tags: els.tags.value.split(",").map((t) => t.trim()).filter(Boolean),
  };
  if (!body.text) return;
  guard(() =>
    api.create(body).then(() => {
      els.form.reset();
      els.priority.value = "medium";
      refresh();
    })
  );
});

let searchTimer;
els.search.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(refresh, 200);
});
els.sort.addEventListener("change", refresh);
els.showAll.addEventListener("change", refresh);

refresh();
