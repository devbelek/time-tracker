import assert from "node:assert/strict";
import { test } from "node:test";

import {
  dayRangeToIso,
  formatDuration,
  percentOf,
  presetRange,
  toDateInput,
} from "../app/static/js/format.js";

/** Выполняет `fn` в заданном часовом поясе (Node подхватывает смену TZ на лету). */
function inTimezone(tz, fn) {
  const previous = process.env.TZ;
  process.env.TZ = tz;
  try {
    return fn();
  } finally {
    if (previous === undefined) delete process.env.TZ;
    else process.env.TZ = previous;
  }
}

const hoursBetween = ({ from, to }) => (Date.parse(to) - Date.parse(from)) / 3_600_000;

test("formatDuration: обычные значения", () => {
  assert.equal(formatDuration(0), "0:00:00");
  assert.equal(formatDuration(59), "0:00:59");
  assert.equal(formatDuration(60), "0:01:00");
  assert.equal(formatDuration(3599), "0:59:59");
  assert.equal(formatDuration(3725), "1:02:05");
  assert.equal(formatDuration(100 * 3600), "100:00:00");
});

test("formatDuration: дробные и отрицательные значения не ломают вывод", () => {
  assert.equal(formatDuration(61.9), "0:01:01");
  assert.equal(formatDuration(-5), "0:00:00");
});

test("dayRangeToIso: сутки в Бишкеке (UTC+6) начинаются в 18:00 UTC предыдущего дня", () => {
  const range = inTimezone("Asia/Bishkek", () => dayRangeToIso("2026-10-28", "2026-10-28"));
  assert.deepEqual(range, { from: "2026-10-27T18:00:00.000Z", to: "2026-10-28T18:00:00.000Z" });
});

test("dayRangeToIso: правая граница это начало дня после «По»", () => {
  const range = inTimezone("UTC", () => dayRangeToIso("2026-10-26", "2026-10-28"));
  assert.deepEqual(range, { from: "2026-10-26T00:00:00.000Z", to: "2026-10-29T00:00:00.000Z" });
});

test("dayRangeToIso: в день перехода на летнее время в США 23 часа, при обратном переходе 25", () => {
  inTimezone("America/New_York", () => {
    assert.equal(hoursBetween(dayRangeToIso("2026-03-08", "2026-03-08")), 23);
    assert.equal(hoursBetween(dayRangeToIso("2026-11-01", "2026-11-01")), 25);
    assert.equal(hoursBetween(dayRangeToIso("2026-06-15", "2026-06-15")), 24);
  });
});

test("dayRangeToIso: конец месяца и года переходит корректно", () => {
  const range = inTimezone("UTC", () => dayRangeToIso("2026-12-31", "2026-12-31"));
  assert.equal(range.to, "2027-01-01T00:00:00.000Z");
});

test("dayRangeToIso: пустые и неверные значения дают понятную ошибку", () => {
  for (const bad of ["", null, undefined, "28.10.2026", "2026-1-5", "abc", "2026-02-30", "2026-13-01"]) {
    assert.throws(() => dayRangeToIso(bad, "2026-10-28"), { message: "Укажите период" }, `from=${bad}`);
    assert.throws(() => dayRangeToIso("2026-10-28", bad), { message: "Укажите период" }, `to=${bad}`);
  }
});

test("dayRangeToIso: год 0026 не превращается в 1926 (сервер сам отклонит такой период)", () => {
  const range = inTimezone("UTC", () => dayRangeToIso("0026-10-01", "0026-10-02"));
  assert.ok(range.from.startsWith("0026-10-01"), range.from);
});

test("presetRange: сегодня, неделя с понедельника, месяц", () => {
  const wednesday = new Date(2026, 9, 28); // 28 октября 2026, среда
  assert.deepEqual(presetRange("today", wednesday), { from: "2026-10-28", to: "2026-10-28" });
  assert.deepEqual(presetRange("week", wednesday), { from: "2026-10-26", to: "2026-10-28" });
  assert.deepEqual(presetRange("month", wednesday), { from: "2026-10-01", to: "2026-10-28" });
});

test("presetRange: понедельник начинает неделю сам, воскресенье относится к прошедшей неделе", () => {
  assert.equal(presetRange("week", new Date(2026, 9, 26)).from, "2026-10-26"); // понедельник
  assert.equal(presetRange("week", new Date(2026, 10, 1)).from, "2026-10-26"); // воскресенье 1 ноября
});

test("presetRange: неделя может начаться в прошлом месяце", () => {
  assert.equal(presetRange("week", new Date(2026, 10, 3)).from, "2026-11-02");
  assert.equal(presetRange("week", new Date(2026, 4, 1)).from, "2026-04-27"); // пятница 1 мая
});

test("toDateInput: ведущие нули", () => {
  assert.equal(toDateInput(new Date(2026, 0, 5)), "2026-01-05");
});

test("percentOf: деление на ноль и округление", () => {
  assert.equal(percentOf(0, 0), 0);
  assert.equal(percentOf(1, 3), 33);
  assert.equal(percentOf(2, 3), 67);
  assert.equal(percentOf(5, 5), 100);
});
