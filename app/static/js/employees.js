// Список сотрудников: добавление, запуск и остановка таймера, живой счётчик.

import { api, post } from "./api.js";
import { $, cloneTemplate, field, setText, showMessage } from "./dom.js";
import { formatDuration } from "./format.js";

const drafts = new Map(); // id сотрудника -> недописанное описание задачи (список перерисовывается)
let clockOffsetMs = 0; // разница «часы сервера минус часы браузера»
let refresh = async () => {};

export function initEmployees(onChange) {
  refresh = onChange;
  $("#employee-form").addEventListener("submit", addEmployee);
  setInterval(tick, 1000);
}

export async function loadEmployees() {
  const data = await api("/api/employees");
  clockOffsetMs = new Date(data.server_time).getTime() - Date.now();
  render(data.employees);
  return data.employees;
}

function render(employees) {
  const cards = employees.length ? employees.map(card) : [cloneTemplate("tpl-employees-empty")];
  $("#employees").replaceChildren(...cards);
  tick();
}

function card(employee) {
  return employee.running ? runningCard(employee) : idleCard(employee);
}

function idleCard(employee) {
  const li = cloneTemplate("tpl-employee-idle");
  setText(li, "name", employee.name);

  const task = field(li, "task");
  task.value = drafts.get(employee.id) ?? "";
  task.setAttribute("aria-label", `Задача: ${employee.name}`);
  task.addEventListener("input", () => drafts.set(employee.id, task.value));

  field(li, "form").addEventListener("submit", (event) => {
    event.preventDefault();
    startTimer(employee.id, task.value);
  });
  return li;
}

function runningCard(employee) {
  const li = cloneTemplate("tpl-employee-running");
  setText(li, "name", employee.name);
  setText(li, "task", employee.running.description);
  field(li, "timer").dataset.started = employee.running.started_at;
  field(li, "stop").addEventListener("click", () => stopTimer(employee.id));
  return li;
}

// Живой счётчик обновляет только цифры и не перерисовывает карточки, иначе сбивался бы ввод в соседних полях.
function tick() {
  const now = Date.now() + clockOffsetMs;
  for (const node of document.querySelectorAll("[data-started]")) {
    node.textContent = formatDuration((now - new Date(node.dataset.started).getTime()) / 1000);
  }
}

async function addEmployee(event) {
  event.preventDefault();
  const input = $("#employee-name");
  // Поле очищаем сразу, а не после ответа: иначе ответ на этот запрос затёр бы имя,
  // которое пользователь успел начать вводить следующим.
  const name = input.value;
  input.value = "";
  try {
    const employee = await post("/api/employees", { name });
    showMessage(`Добавлен: ${employee.name}`);
  } catch (error) {
    if (!input.value) input.value = name; // при ошибке возвращаем введённое, чтобы его можно было поправить
    showMessage(error.message, "danger");
  }
  await refresh();
}

async function startTimer(employeeId, description) {
  if (!description.trim()) {
    showMessage("Опишите задачу, прежде чем запускать таймер", "danger");
    return;
  }
  try {
    await post(`/api/employees/${employeeId}/timer/start`, { description });
    drafts.delete(employeeId);
    showMessage("");
  } catch (error) {
    // например, 409: таймер уже запущен в другой вкладке; обновление ниже покажет актуальное состояние
    showMessage(error.message, "danger");
  }
  await refresh();
}

async function stopTimer(employeeId) {
  try {
    const entry = await post(`/api/employees/${employeeId}/timer/stop`);
    showMessage(`Остановлено: «${entry.description}», ${formatDuration(entry.seconds)}`);
  } catch (error) {
    showMessage(error.message, "danger");
  }
  await refresh();
}
