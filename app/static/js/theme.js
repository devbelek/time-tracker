// Тема оформления: по умолчанию как в системе, выбор пользователя запоминается.
// Скрипт подключён в <head> без defer, чтобы тема применилась до отрисовки (без вспышки).
(function () {
  const KEY = "theme";
  const root = document.documentElement;

  function stored() {
    try {
      return localStorage.getItem(KEY);
    } catch {
      return null; // хранилище может быть недоступно (приватный режим)
    }
  }

  function systemTheme() {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  root.dataset.bsTheme = stored() || systemTheme();

  document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("theme-toggle").addEventListener("click", () => {
      const next = root.dataset.bsTheme === "dark" ? "light" : "dark";
      root.dataset.bsTheme = next;
      try {
        localStorage.setItem(KEY, next);
      } catch {
        /* не страшно: тема просто не запомнится */
      }
    });
  });
})();
