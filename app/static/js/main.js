// Точка входа: связывает список сотрудников и отчёт.

import { showMessage } from "./dom.js";
import { initEmployees, loadEmployees } from "./employees.js";
import { initReport, loadReport, setEmployeeOptions } from "./report.js";

async function refresh() {
  setEmployeeOptions(await loadEmployees());
  await loadReport();
}

initEmployees(refresh);
initReport();
refresh().catch((error) => showMessage(error.message, "danger"));
