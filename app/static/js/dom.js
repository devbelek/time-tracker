// Мелкие помощники для работы с DOM и шаблонами из index.html.

export const $ = (selector, root = document) => root.querySelector(selector);

/** Копия корневого элемента шаблона `<template id="...">` */
export function cloneTemplate(id) {
  return document.getElementById(id).content.firstElementChild.cloneNode(true);
}

/** Элемент с атрибутом data-field="name" внутри `root` */
export function field(root, name) {
  return root.querySelector(`[data-field="${name}"]`);
}

/** Текст пользователя вставляется только через textContent, поэтому HTML в именах не выполняется */
export function setText(root, name, text) {
  field(root, name).textContent = text;
}

let hideTimer;
const box = () => $("#message");

function hideMessage() {
  box().classList.add("d-none");
}

/** Сообщение поверх страницы. Успех гаснет сам, ошибка висит до следующего действия или клика по ней. */
export function showMessage(text, kind = "success") {
  clearTimeout(hideTimer);
  if (!text) {
    hideMessage();
    return;
  }
  box().textContent = text;
  box().className = `alert alert-${kind} toast-msg`;
  if (kind === "success") hideTimer = setTimeout(hideMessage, 6000);
}

box().addEventListener("click", hideMessage);
