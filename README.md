# Через время к звёздам — локальная preview-сборка

Локальный просмотр: http://127.0.0.1:5002/ . Пролог с видео: http://127.0.0.1:5002/read/1#readBody .

Ролик «2 пролог 1 сюжет» находится в `static/video/prologue.mp4` (H.264/AAC, 28,514 с). Для добавления в существующую локальную базу выполнить `python install_prologue_video.py`: скрипт сохраняет резервную копию, находит единственный пролог по виду записи, вставляет видео перед текстом и не дублирует вставку. База и резервные копии в Git не входят. В любом месте текста поддерживается отдельный абзац `[video]/static/video/prologue.mp4[/video]`. Публикация файлов в GitHub сама по себе не обновляет k-zvezdam.ru; она обновляет preview-поддомен kzvezdam.annakam.ru (см. раздел «Публикация»).

Это Flask-читалка, собранная из переданных архивных материалов, и её текущая редакция опубликована на поддомене **https://kzvezdam.annakam.ru/** как статический экспорт. Flask/WSGI на виртуальном хостинге недоступен (нет SSH и Python), поэтому серверные функции (лайки, счётчики просмотров, админка) в публичную сборку не входят: экспорт убирает кнопку лайка и счётчики, оставляя чтение, оглавление, изображения и видео. Preview закрыт от индексации (`X-Robots-Tag: noindex` и `robots.txt`); canonical в HTML указывает на `https://kzvezdam.annakam.ru`.

## Состав редакции

По согласованному рабочему допущению включены пролог из `roman_promo_update.zip::webapp/chapters_seed.json` и главы 1–10 из разных версий. Заголовки 1–3 взяты из соответствующих root-черновиков; тексты глав не редактировались. Главы 11–19 и рабочие черновики в сборку не включены. Для каждой главы и каждой иллюстрации сохранены исходный архив/путь и SHA-256 в `CONTENT-PROVENANCE.json`. Все тела оставлены в исходном виде; отображение старых ссылок `/static/uploads/<имя>` сопоставляет их с локальными файлами `static/chapter-images/` по имени.

Сборка использует полный Flask-пакет `roman_promo_update.zip` как основу, поздний root `admin_edit.html` и `style.css` как совместимые обновления UI, и собственные изменения `app.py` для изоляции данных и проверки доступа/ввода. Старые shell-скрипты, service-конфиги, пароли и БД не включены.

## Локальный запуск

Python 3.11+ рекомендуется. Установите зависимости в виртуальное окружение командой `python -m pip install -r requirements.txt`. Скопируйте `.env.example` в локальный `.env` или задайте переменные окружения напрямую; приложение само не читает `.env`. Задайте случайный `ROMAN_SECRET` и `ROMAN_ADMIN_PASSWORD`: без пароля все маршруты админки закрыты. Для preview оставьте `PREVIEW_NOINDEX=1` и `SESSION_COOKIE_SECURE=0` при локальном HTTP. Значения секретов храните только в окружении и не добавляйте заполненный `.env` в Git.

Пути данных по умолчанию: SQLite — `instance/roman.db`, загрузки — `instance/uploads/`. Их можно изолировать переменными `ROMAN_DATA_DIR`, `ROMAN_DB` и `ROMAN_UPLOAD_DIR`; предварительно создайте доступные для записи каталоги. Первичный запуск создаёт SQLite и помещает в неё 11 выбранных записей. Если база уже существует и содержит главы, seed её не перезаписывает.

На Windows локальный WSGI-запуск: `waitress-serve --host=127.0.0.1 --port=5001 wsgi:app`. На Unix используйте Gunicorn из `requirements.txt`. Для быстрого локального запуска можно вызвать `python app.py`; встроенный сервер всегда запускается с `debug=False`.

## Проверка

Запустите тесты: `python -m unittest discover -s tests -v`. Набор проверяет публичное чтение, SEO/noindex, CSRF, закрытую админку без пароля, безопасные редиректы, фильтрацию URL, проверку загружаемых изображений, а также статический экспорт (11 глав, 28 иллюстраций, видео в прологе, отсутствие серверных действий). Это локальные тесты Flask test client; они не подтверждают работу DNS, внешнего домена, TLS, production-хостинга или почтовых/социальных ссылок.

## Публикация на kzvezdam.annakam.ru

Хостинг виртуальный (ISPmanager/Hostiman): SSH и Python отсутствуют, поэтому публикуется не Flask-приложение, а готовые файлы.

```bash
python tools/export_static.py --out dist --origin https://kzvezdam.annakam.ru   # сборка
FTP_HOST=... FTP_USER=... FTP_PASSWORD=... FTP_REMOTE_DIR=/kzvezdam.annakam.ru \
  python tools/deploy_ftp.py --src dist                                          # выгрузка
python tools/verify_site.py --base https://kzvezdam.annakam.ru --expect-sha <sha> # проверка
```

Экспорт работает на копии базы во временном каталоге, поэтому локальная `instance/roman.db` не меняется. Если базы нет (в CI), она создаётся из `chapters_seed.json`, и в пролог идемпотентно добавляется блок `[video]`. Получаются адреса `/`, `/chapters`, `/read/<id>`, `/promo` (файлы `index.html` в каталогах плюс правила в `.htaccess`), каталог `static/` и `404.html`. Счётчики просмотров и кнопка лайка вырезаются, `meta csrf-token` не выводится.

Автоматическая публикация: `.github/workflows/deploy.yml` — на каждый push в `main` прогоняет тесты, собирает экспорт и выгружает его по FTPS в `/kzvezdam.annakam.ru`. Секреты репозитория: `FTP_HOST`, `FTP_PORT`, `FTP_USER`, `FTP_PASSWORD`, `FTP_REMOTE_DIR`. В `dist/version.json` записывается SHA релиза.

Откат: вернуть предыдущий коммит (`git revert <sha>` и push в `main` — workflow пересоберёт сайт) либо выгрузить сохранённую копию каталога вручную. Скрипт выгрузки не удаляет файлы на сервере и отказывается работать с каталогом, отличным от `/kzvezdam.annakam.ru`.


## Безопасность и пределы

Сессии используют HttpOnly/SameSite cookies; все state-changing POST требуют CSRF token; logout — POST. Upload принимает только декодируемые JPEG/PNG/GIF/WEBP до 5 MiB с соответствующим расширением и случайным именем. Медиа и SQLite находятся в локальных каталогах. Content Security Policy включена в режиме Report-Only для наблюдения за существующими inline-скриптами и стилями; она пока не является блокирующей политикой. Всё перечисленное относится к локальному Flask-приложению: публичная статическая сборка не принимает POST, не хранит сессии и не содержит админки, поэтому эти риски на поддомен не переносятся.

## Редакция пролога для GitHub Pages — 24.10.2026

Полный текст: `content/prologue.txt`; размещение медиа: `content/prologue-media.json`.
Новая редакция синхронизирована с записью пролога в `chapters_seed.json`.
Четыре ролика и три иллюстрации размещены по ходу текста, видео запускаются по нажатию.

Исходная ветка: `prologue-horror-preview` в закрытом репозитории приложения.
Публичный репозиторий готового сайта: https://github.com/WaDIM0041/k-zvezdam-prologue-preview .
Предпросмотр: https://wadim0041.github.io/k-zvezdam-prologue-preview/read/1/ .
GitHub Pages закрытого репозитория недоступен на текущем тарифе; публичная версия содержит только готовый экспорт.
Автодеплой main на kzvezdam.annakam.ru в рамках этой работы не запускать: автор переносит обновление самостоятельно.

Сборка для GitHub Pages:
`python tools/export_static.py --out ../publication/k-zvezdam-prologue-preview --origin https://wadim0041.github.io/k-zvezdam-prologue-preview --base-path /k-zvezdam-prologue-preview`

Сборка для корня домена:
`python tools/export_static.py --out ../publication/hosting --origin https://kzvezdam.annakam.ru`
