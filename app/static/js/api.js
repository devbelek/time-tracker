// Обёртка над fetch: ошибки API приходят как {"detail": "понятный текст"}, показываем текст как есть.

export async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.detail || `Ошибка сервера (${response.status})`);
  return body;
}

export const post = (path, data) =>
  api(path, { method: "POST", body: data === undefined ? undefined : JSON.stringify(data) });
