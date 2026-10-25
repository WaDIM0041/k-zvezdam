# Визуальные дополнения к принятой редакции Пролога

Две иллюстрации созданы встроенным image_gen 25.10.2026 по прямому
поручению автора дополнить обновлённую страницу. Они иллюстрируют уже
написанные эпизоды и не назначаются новыми универсальными эталонами.

## Источники и проверка

Обе опоры фактически просмотрены перед генерацией:

- `static/prologue/Настилы уходят в бездонную шахту — v001.webp` — архитектура,
  глубина, материалы шахты.
- `static/prologue/Три целится за колонну — экипаж прикрывает друг друга — v001.webp`
  — архитектура, настил, фактура, фотографическая манера.

Архитектура, материалы и отсутствие дополнительных персонажей проверены
по результатам генерации. В первой версии теней были освещённые лампы
на дальнем плане; отдельной правкой они выключены. В итоговой версии
три бесформенных силуэта отделены от пола и не совершают осмысленных
действий. Лица и личности наблюдателей не добавлялись.

## Файлы

- `static/prologue/Технический балкон станции Гелиос-0 — v001.webp`
- `static/prologue/Три тени проступают на стене станции — v001.webp`

Мастера PNG сохранены в `chapter-work/00/медиа/` рабочей мастерской.
Веб-копии — WebP, исходная композиция и разрешение 1672×941 сохранены.

## Реестр визуального канона

После уведомления о создании общего каталога прочитаны НАЧАТЬ_ЗДЕСЬ.md,
ПРОТОКОЛ.md, СОСТОЯНИЕ.md и РЕЕСТР.json в
`D:/OneDrive/Documets/РОМАН/ФИЛЬМ/01_Общие_референсы/`.
На момент сверки revision=0, status=initializing, entities/assets пусты.
Это не отсутствие исходников: здесь использованы конкретные уже
опубликованные опоры текущего Пролога. Новые ID/stateId не назначались,
реестр хранителя не изменялся. Перед публикацией revision проверяется
повторно; результат сверки фиксируется в отчёте публикации.

## Промпты

Балкон:

```text
Use case: illustration-story. Create one cinematic photorealistic 16:9 illustration for an adult Russian science-fiction horror novel. Reference image 1 supplies the station architecture, materials, endless dark atrium and vertical depth. Reference image 2 supplies the same industrial architecture, metal grating, cables and restrained photographic visual style. Make a NEW view from a human eye height just inside an open airlock onto a narrow empty technical balcony around the colossal station atrium: steel grating in the foreground, worn iron railings, immense ribbed pillars receding into blackness, thick motionless cables along columns. A single off-camera astronaut flashlight reveals a small strip of the walkway and part of a distant column; almost all the upper hall and the chasm remain dark and unreadable. The ordinary platform is physically traversable but the surrounding space feels oppressive, empty, alienating, and impossible to survey. Dark cold graphite, worn grey metal, very restrained desaturated cyan reflections, realistic dust. Preserve the reference station's recognizable architecture; REMOVE the reference's rows of functioning electric wall lamps, since the story says no lamps are on. No people in frame, no silhouettes, no creatures, no cube, no eyes, no dramatic explosion, no text, no letters, no interface, no watermark. The horror comes only from the vast empty place. Carefully readable details in the illuminated strip, no pitch-black entire image. File concept in Russian: Технический балкон станции Гелиос-0.
```

Тени, начальная генерация:

```text
Use case: illustration-story. Create one cinematic photorealistic 16:9 illustration for an adult science-fiction horror novel. The references establish the same abandoned station: ribbed blackened metal columns, dusty steel plating, grated catwalks and immense dark industrial atrium. Show a close oblique human-eye-level view of one dusty vertical metal wall beside the walkway. Exactly THREE vague vertical black shadow-like human-sized patches hang on the wall with their lower edges about one metre ABOVE the grating, with a clearly visible unshadowed strip of ordinary metal between all patches and the floor. They are simply almost featureless dark silhouettes, not characters performing actions. Soft irregular edges, two patches opaque black, one slightly fainter with a panel seam showing through it, suggesting an unexplained flicker. No faces, no eyes, no fingers or distinct hands, no legs walking, no purposeful gestures. An offscreen flashlight grazes the wall from the side, showing panel seams, old rivets and dust; the three patches remain unnaturally vertical regardless of that side lighting. Keep the image restrained and photographic, clearly readable, psychologically disturbing. No people directly visible, no monster, no cube, no emerging body, no smoke entity, no tentacles, no colored glitch, no functioning wall lights, no text or watermark. Do not foreshadow the cube transformation. File concept in Russian: Три тени проступают на стене станции.
```

Исправление освещения теней:

```text
Edit only the small background electric lamps along the LEFT side of this station scene: switch every lamp off and remove all bright luminous white lamp faces, leaving dark unlit fixtures and dim ambient metal. The narrative explicitly says no electric lamps are operating. Retain the off-camera flashlight illumination grazing the main wall, so the three shadow patches and wall panel seams remain readable. Keep EXACTLY the same composition, framing, three vertical black shadow patches (two opaque, centre fainter), their sizes and positions with a bare metal gap above the floor, steel wall, railings and textures. No people, no text, no new objects. Change nothing else. 16:9.
```
