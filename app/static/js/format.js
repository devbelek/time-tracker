// Чистые функции форматирования и работы с датами. Без DOM, поэтому покрыты тестами (tests-js/).

const pad2 = (n) => String(n).padStart(2, "0");

/** 3725 -> "1:02:05" */
export function formatDuration(totalSeconds) {
  const s = Math.max(0, Math.floor(totalSeconds));
  return `${Math.floor(s / 3600)}:${pad2(Math.floor((s % 3600) / 60))}:${pad2(s % 60)}`;
}

const DATE_TIME = { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" };
const TIME = { hour: "2-digit", minute: "2-digit" };

/**
 * Промежуток записи по местному времени: "25.10.2026, 15:00 → 15:50".
 * Если запись закончилась в другой день, дата пишется у обоих концов. Идущая: "… → идёт сейчас". Вокруг стрелки неразрывные пробелы, чтобы она не отрывалась от значений.
 */
export function formatRange(startIso, stopIso) {
  const start = new Date(startIso);
  const head = start.toLocaleString("ru-RU", DATE_TIME);
  if (!stopIso) return `${head}\u00a0→\u00a0идёт сейчас`;
  const stop = new Date(stopIso);
  const tail =
    start.toDateString() === stop.toDateString()
      ? stop.toLocaleTimeString("ru-RU", TIME)
      : stop.toLocaleString("ru-RU", DATE_TIME);
  return `${head}\u00a0→\u00a0${tail}`;
}

/** Склонение по числу: plural(2, ["запись", "записи", "записей"]) -> "записи" */
export function plural(n, [one, few, many]) {
  const lastTwo = Math.abs(n) % 100;
  const last = lastTwo % 10;
  if (lastTwo > 10 && lastTwo < 20) return many;
  if (last === 1) return one;
  if (last >= 2 && last <= 4) return few;
  return many;
}

export const entriesLabel = (n) => `${n} ${plural(n, ["запись", "записи", "записей"])}`;

/** Date -> "YYYY-MM-DD" по местному календарю (значение для <input type="date">) */
export function toDateInput(date) {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
}

/** Местная полночь дня "YYYY-MM-DD", сдвинутого на `plusDays` дней. */
function localMidnight(value, plusDays) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value ?? "");
  if (!match) throw new Error("Укажите период");
  const [year, month, day] = match.slice(1).map(Number);
  // setFullYear вместо new Date(год, ...): конструктор превращает годы 0..99 в 1900..1999
  const date = new Date(2000, 0, 1);
  date.setFullYear(year, month - 1, day);
  // «2026-02-30» не должно молча превращаться в 2 марта
  if (date.getMonth() !== month - 1 || date.getDate() !== day) throw new Error("Укажите период");
  date.setDate(date.getDate() + plusDays);
  return date;
}

/**
 * Даты из полей формы -> границы периода для API.
 *
 * Пользователь выбирает дни по своему календарю. На сервер уходят точные моменты времени:
 * начало дня «С» и начало дня, следующего за «По» (правая граница не включается).
 * Так учитываются часовой пояс и переход на летнее время: сутки бывают в 23 и 25 часов.
 */
export function dayRangeToIso(fromValue, toValue) {
  return {
    from: localMidnight(fromValue, 0).toISOString(),
    to: localMidnight(toValue, 1).toISOString(),
  };
}

/** Быстрый выбор периода: "today" | "week" (с понедельника) | "month" -> { from, to } в формате полей дат */
export function presetRange(kind, today = new Date()) {
  const y = today.getFullYear();
  const m = today.getMonth();
  const d = today.getDate();
  let from = today;
  if (kind === "week") from = new Date(y, m, d - ((today.getDay() + 6) % 7));
  if (kind === "month") from = new Date(y, m, 1);
  return { from: toDateInput(from), to: toDateInput(today) };
}

/** Доля части от целого в процентах, 0..100 */
export function percentOf(part, total) {
  return total > 0 ? Math.round((part / total) * 100) : 0;
}
