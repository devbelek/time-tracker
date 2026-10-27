// Отчёт за период: форма выбора, запрос и отрисовка.

import { api } from "./api.js";
import { $, cloneTemplate, field, setText, showMessage } from "./dom.js";
import { dayRangeToIso, entriesLabel, formatDuration, formatRange, percentOf, presetRange } from "./format.js";

export function initReport() {
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
  // ручной выбор дат снимает подсветку быстрого периода
  for (const id of ["#from", "#to"]) $(id).addEventListener("input", () => markActiveRange(null));
  setRange("today");
}

function setRange(kind) {
  const { from, to } = presetRange(kind);
  $("#from").value = from;
  $("#to").value = to;
  markActiveRange(kind);
}

function markActiveRange(kind) {
  for (const button of document.querySelectorAll("[data-range]")) {
    button.setAttribute("aria-pressed", String(button.dataset.range === kind));
  }
}

/** Обновляет выпадающий список «Сотрудник», сохраняя текущий выбор */
export function setEmployeeOptions(employees) {
  const select = $("#report-employee");
  const selected = select.value;
  select.replaceChildren(new Option("Все", ""), ...employees.map((e) => new Option(e.name, e.id)));
  select.value = employees.some((e) => String(e.id) === selected) ? selected : "";
}

export async function loadReport() {
  let params;
  try {
    params = new URLSearchParams(dayRangeToIso($("#from").value, $("#to").value));
  } catch (error) {
    showMessage(error.message, "danger");
    return;
  }
  const employeeId = $("#report-employee").value;
  if (employeeId) params.set("employee_id", employeeId);

  try {
    renderReport(await api(`/api/report?${params}`));
  } catch (error) {
    $("#report").replaceChildren();
    showMessage(error.message, "danger");
  }
}

function renderReport(report) {
  const target = $("#report");
  if (report.employees.length === 0) {
    target.replaceChildren(cloneTemplate("tpl-report-no-employees"));
    return;
  }

  const root = cloneTemplate("tpl-report");
  const rows = field(root, "rows");
  for (const employee of report.employees) {
    rows.append(reportRow(employee, report.total_seconds));
  }

  const entriesCount = report.employees.reduce((sum, e) => sum + e.entries.length, 0);
  setText(root, "total", formatDuration(report.total_seconds));
  setText(root, "entries", entriesLabel(entriesCount));
  setText(
    root,
    "note",
    entriesCount === 0
      ? "За выбранный период записей нет."
      : "Если запись пересекает границу периода, считается только время внутри периода.",
  );
  target.replaceChildren(root);
}

function reportRow(employee, totalSeconds) {
  const row = cloneTemplate("tpl-report-row");
  setText(row, "name", employee.name);
  setText(row, "total", formatDuration(employee.total_seconds));
  setText(row, "count", employee.entries.length ? entriesLabel(employee.entries.length) : "нет записей");

  const percent = percentOf(employee.total_seconds, totalSeconds);
  field(row, "progress").setAttribute("aria-valuenow", percent);
  field(row, "bar").style.width = `${percent}%`;

  const list = field(row, "entries");
  if (employee.entries.length === 0) list.append(cloneTemplate("tpl-entries-empty"));
  for (const entry of employee.entries) list.append(entryItem(entry));
  return row;
}

function entryItem(entry) {
  const item = cloneTemplate("tpl-entry");
  setText(item, "task", entry.description);
  setText(item, "when", formatRange(entry.started_at, entry.stopped_at));
  setText(item, "seconds", formatDuration(entry.seconds));
  return item;
}
