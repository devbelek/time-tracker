"use strict";

const $ = (selector) => document.querySelector(selector);

let clockOffsetMs = 0; // разница «часы сервера − часы браузера»
const drafts = new Map(); // employee id -> недописанное описание задачи

// ---------- вспомогательное ----------

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.detail || `Ошибка сервера (${response.status})`);
  return body;
}

function showMessage(text, isError = false) {
  const box = $("#message");
  box.textContent = text;
  box.className = isError ? "message error" : "message";
  box.hidden = !text;
}

const pad = (n) => String(n).padStart(2, "0");

function formatDuration(totalSeconds) {
  const s = Math.max(0, Math.floor(totalSeconds));
  return `${Math.floor(s / 3600)}:${pad(Math.floor((s % 3600) / 60))}:${pad(s % 60)}`;
}

function formatDateTime(iso) {
  return new Date(iso).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "medium" });
}

function toDateInput(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children);
  return node;
}

// ---------- сотрудники и таймеры ----------

async function loadEmployees() {
  const data = await api("/api/employees");
  clockOffsetMs = new Date(data.server_time).getTime() - Date.now();
  renderEmployees(data.employees);
  fillEmployeeSelect(data.employees);
}

function renderEmployees(employees) {
  const list = $("#employees");
  list.replaceChildren();
  if (employees.length === 0) {
    list.append(el("li", { className: "empty" }, "Пока никого нет. Добавьте первого сотрудника."));
    return;
  }
  for (const emp of employees) list.append(employeeCard(emp));
  tick();
}

function employeeCard(emp) {
  const card = el("li", { className: emp.running ? "card running" : "card" });
  card.append(el("div", { className: "name" }, emp.name));

  if (emp.running) {
    const stopButton = el("button", { type: "button", className: "stop" }, "Остановить");
    stopButton.addEventListener("click", () => stopTimer(emp.id));
    const timer = el("span", { className: "timer" }, "0:00:00");
    timer.dataset.started = emp.running.started_at;
    card.append(
      el("div", { className: "status" },
        el("span", { className: "badge" }, "Идёт"),
        timer,
        stopButton,
      ),
      el("div", { className: "task" }, emp.running.description),
    );
  } else {
    const form = el("form", { className: "row" });
    const input = el("input", {
      type: "text", maxLength: 300, placeholder: "Над чем работаете?",
      ariaLabel: `Задача: ${emp.name}`, autocomplete: "off",
      value: drafts.get(emp.id) ?? "",
    });
    input.addEventListener("input", () => drafts.set(emp.id, input.value));
    form.append(input, el("button", { type: "submit" }, "Старт"));
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      startTimer(emp.id, input.value);
    });
    card.append(form);
  }
  return card;
}

// живые часы: обновляем только цифры, не перерисовывая карточки (иначе сбивается ввод)
function tick() {
  const now = Date.now() + clockOffsetMs;
  for (const node of document.querySelectorAll("[data-started]")) {
    node.textContent = formatDuration((now - new Date(node.dataset.started).getTime()) / 1000);
  }
}
setInterval(tick, 1000);

async function startTimer(employeeId, description) {
  if (!description.trim()) return showMessage("Опишите задачу, прежде чем запускать таймер", true);
  try {
    await api(`/api/employees/${employeeId}/timer/start`, {
      method: "POST", body: JSON.stringify({ description }),
    });
    drafts.delete(employeeId);
    showMessage("");
  } catch (error) {
    showMessage(error.message, true);
  }
  await refresh();
}

async function stopTimer(employeeId) {
  try {
    const entry = await api(`/api/employees/${employeeId}/timer/stop`, { method: "POST" });
    showMessage(`Остановлено: «${entry.description}», ${formatDuration(entry.seconds)}`);
  } catch (error) {
    showMessage(error.message, true);
  }
  await refresh();
}

$("#employee-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = $("#employee-name");
  try {
    const emp = await api("/api/employees", { method: "POST", body: JSON.stringify({ name: input.value }) });
    input.value = "";
    showMessage(`Добавлен: ${emp.name}`);
  } catch (error) {
    showMessage(error.message, true);
  }
  await refresh();
});

// ---------- отчёт ----------

function fillEmployeeSelect(employees) {
  const select = $("#report-employee");
  const selected = select.value;
  select.replaceChildren(el("option", { value: "" }, "Все"));
  for (const emp of employees) select.append(el("option", { value: emp.id }, emp.name));
  select.value = employees.some((e) => String(e.id) === selected) ? selected : "";
}

function setRange(kind) {
  const today = new Date();
  let from = today;
  let to = today;
  if (kind === "week") {
    from = new Date(today.getFullYear(), today.getMonth(), today.getDate() - ((today.getDay() + 6) % 7));
  } else if (kind === "month") {
    from = new Date(today.getFullYear(), today.getMonth(), 1);
  }
  $("#from").value = toDateInput(from);
  $("#to").value = toDateInput(to);
}

// Даты в полях берутся по местному календарю пользователя. На сервер уходят точные моменты времени:
// начало дня «С» и начало дня, следующего за «По» (правая граница не включается).
function periodParams() {
  const [fy, fm, fd] = $("#from").value.split("-").map(Number);
  const [ty, tm, td] = $("#to").value.split("-").map(Number);
  const from = new Date(fy, fm - 1, fd);
  const to = new Date(ty, tm - 1, td + 1);
  if (Number.isNaN(from.getTime()) || Number.isNaN(to.getTime())) throw new Error("Укажите период");
  const params = new URLSearchParams({ from: from.toISOString(), to: to.toISOString() });
  if ($("#report-employee").value) params.set("employee_id", $("#report-employee").value);
  return params;
}

async function loadReport() {
  const target = $("#report");
  let params;
  try {
    params = periodParams();
  } catch (error) {
    return showMessage(error.message, true);
  }
  try {
    renderReport(await api(`/api/report?${params}`));
  } catch (error) {
    target.replaceChildren();
    showMessage(error.message, true);
  }
}

function renderReport(report) {
  const target = $("#report");
  target.replaceChildren();
  if (report.employees.length === 0) {
    target.append(el("p", { className: "empty" }, "Сотрудников пока нет, отчёт строить не из чего."));
    return;
  }

  const body = el("tbody");
  for (const emp of report.employees) {
    const details = el("details");
    details.append(el("summary", {}, emp.name));
    if (emp.entries.length === 0) {
      details.append(el("p", { className: "note" }, "Записей за период нет"));
    } else {
      const sub = el("ul", { className: "sub" });
      for (const entry of emp.entries) {
        const when = `${formatDateTime(entry.started_at)} → ${entry.stopped_at ? formatDateTime(entry.stopped_at) : "идёт сейчас"}`;
        sub.append(el("li", {},
          el("span", {}, entry.description, el("span", { className: "when" }, when)),
          el("span", { className: "num" }, formatDuration(entry.seconds)),
        ));
      }
      details.append(sub);
    }
    body.append(el("tr", {}, el("td", {}, details), el("td", { className: "num" }, formatDuration(emp.total_seconds))));
  }

  const table = el("table", {},
    el("thead", {}, el("tr", {}, el("th", {}, "Сотрудник"), el("th", { className: "num" }, "Всего"))),
    body,
    el("tfoot", {}, el("tr", {}, el("td", {}, "Итого"), el("td", { className: "num" }, formatDuration(report.total_seconds)))),
  );
  target.append(table);

  if (report.total_seconds === 0) {
    target.append(el("p", { className: "empty" }, "За выбранный период записей нет."));
  } else {
    target.append(el("p", { className: "note" }, "Если запись пересекает границу периода, считается только время внутри периода."));
  }
}

$("#report-form").addEventListener("submit", (event) => {
  event.preventDefault();
  loadReport();
});
$("#report-employee").addEventListener("change", loadReport);
for (const button of document.querySelectorAll("[data-range]")) {
  button.addEventListener("click", () => {
    setRange(button.dataset.range);
    loadReport();
  });
}

// ---------- запуск ----------

async function refresh() {
  await loadEmployees();
  await loadReport();
}

setRange("today");
refresh().catch((error) => showMessage(error.message, true));
