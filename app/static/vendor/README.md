# Сторонние файлы фронтенда

Библиотеки лежат в репозитории, а не подключаются с CDN: приложение работает без интернета, в Docker, и
политику безопасности (`Content-Security-Policy: default-src 'self'`) не приходится ослаблять.

| Что | Версия | Лицензия | Откуда |
|---|---|---|---|
| [Bootstrap](https://getbootstrap.com/) (только CSS, без JS) | 5.3.8 | MIT, `bootstrap/LICENSE` | npm `bootstrap@5.3.8`, `dist/css/bootstrap.min.css` |
| Три значка из [Bootstrap Icons](https://icons.getbootstrap.com/): `circle-half`, `play-fill`, `stop-fill` | 1.13.2 | MIT, `bootstrap-icons/LICENSE` | npm `bootstrap-icons@1.13.2`, `icons/*.svg`. Вставлены в `index.html` как SVG, шрифт иконок не подключается |
| [IBM Plex Sans](https://github.com/IBM/plex), начертания 400, 500, 600, подмножества latin и cyrillic | 5.3.0 | SIL OFL 1.1, `fonts/ibm-plex-sans/LICENSE` | npm `@fontsource/ibm-plex-sans@5.3.0`, `files/*.woff2` |

Целостность архивов npm сверена с `dist.integrity` из реестра при загрузке.

Единственное изменение: из `bootstrap.min.css` удалён завершающий комментарий `sourceMappingURL`, чтобы
инструменты разработчика не запрашивали отсутствующий `.map`-файл. Остальное побайтно как в пакете.

SHA-256 файлов в репозитории:

```
8f8173cb2d8f867274aeb0cb15328e60f490c7f272351e51a55f1dabb486e4ff  bootstrap/bootstrap.min.css
69afad88a0740b6e5647f1104c9176a261f1ad9d60202f605456a983799752e9  fonts/ibm-plex-sans/ibm-plex-sans-cyrillic-400-normal.woff2
200be3a2a6b1789fb8824a4a74c7cccb7137e83fde6200ea78d8829f99d43546  fonts/ibm-plex-sans/ibm-plex-sans-cyrillic-500-normal.woff2
730becc6f005c18c31440f14d34677f2704a85e6afffd4bee6a64d5c95f45a55  fonts/ibm-plex-sans/ibm-plex-sans-cyrillic-600-normal.woff2
3b646991d30055a93a4ecc499713d4347953a74a947ecab435ab72070cbdab0e  fonts/ibm-plex-sans/ibm-plex-sans-latin-400-normal.woff2
0717336fb31fcdcde4b8deb3675bb4a0f7f6d484864afcd6751ac29975962203  fonts/ibm-plex-sans/ibm-plex-sans-latin-500-normal.woff2
8960851d691c054ed38e259bdcf1a6190d157b4203ed5bb32c632a863fb8ec2f  fonts/ibm-plex-sans/ibm-plex-sans-latin-600-normal.woff2
```

## Как обновить

```bash
npm pack bootstrap@<версия> bootstrap-icons@<версия> @fontsource/ibm-plex-sans@<версия>
# распаковать архивы и скопировать те же файлы, затем обновить версии и хеши в этом файле
```
