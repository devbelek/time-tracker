# Сторонние файлы фронтенда

Библиотеки лежат в репозитории, а не подключаются с CDN: приложение работает без интернета, в Docker, и
политику безопасности (`Content-Security-Policy: default-src 'self'`) не приходится ослаблять.

| Библиотека | Версия | Лицензия | Откуда |
|---|---|---|---|
| [Bootstrap](https://getbootstrap.com/) (только CSS, без JS) | 5.3.8 | MIT, `bootstrap/LICENSE` | npm `bootstrap@5.3.8`, `dist/css/bootstrap.min.css` |
| [Bootstrap Icons](https://icons.getbootstrap.com/) (CSS и шрифт woff2) | 1.13.2 | MIT, `bootstrap-icons/LICENSE` | npm `bootstrap-icons@1.13.2`, `font/` |

Целостность архивов npm сверена с `dist.integrity` из реестра при загрузке.

Единственное изменение: из `bootstrap.min.css` удалён завершающий комментарий `sourceMappingURL`, чтобы
инструменты разработчика не запрашивали отсутствующий `.map`-файл. Остальное побайтно как в пакете.

SHA-256 файлов в репозитории:

```
8f8173cb2d8f867274aeb0cb15328e60f490c7f272351e51a55f1dabb486e4ff  bootstrap/bootstrap.min.css
79c99c1a1e0e937f808a58165728b7ed00800f02ef5efcfcd10dfe71464e675d  bootstrap-icons/bootstrap-icons.min.css
2b7689746f87e0beeae25338bc021dd2515c2f6f003f3d3d064d878d380b2150  bootstrap-icons/fonts/bootstrap-icons.woff2
```

## Как обновить

```bash
npm pack bootstrap@<версия> bootstrap-icons@<версия>
# распаковать архивы и скопировать те же файлы, затем обновить версии и хеши в этом файле
```
