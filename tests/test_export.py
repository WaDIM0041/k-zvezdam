"""Проверки статического экспорта: страницы, видео, отсутствие backend-действий."""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import export_static  # noqa: E402


class StaticExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.temp.name) / "dist"
        cls.code = export_static.main(["--out", str(cls.out), "--origin", "https://kzvezdam.annakam.ru"])

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def read(self, relative: str) -> str:
        return (self.out / relative).read_text(encoding="utf-8")

    def test_export_succeeds_and_has_all_pages(self):
        self.assertEqual(self.code, 0)
        for relative in ("index.html", "chapters/index.html", "promo/index.html",
                         "404.html", "robots.txt", ".htaccess", "version.json"):
            self.assertTrue((self.out / relative).is_file(), relative)
        for cid in range(1, 12):
            self.assertTrue((self.out / "read" / str(cid) / "index.html").is_file(), cid)

    def test_home_uses_subdomain_canonical_and_has_no_backend_bits(self):
        home = self.read("index.html")
        self.assertIn('rel="canonical" href="https://kzvezdam.annakam.ru/"', home)
        self.assertIn('content="noindex,nofollow,noarchive"', home)
        self.assertNotIn("csrf-token", home)
        self.assertNotIn("localhost", home)
        self.assertNotIn("127.0.0.1", home)
        self.assertEqual(home.count('href="/read/'), 12)  # 11 глав + кнопка «Начать чтение»

    def test_prologue_starts_with_opening_illustration_then_video(self):
        page = self.read("read/1/index.html")
        body_start = page.index('id="readBody">')
        self.assertLess(page.index('id="scene-chapter-cover"'), page.index('id="scene-opening"'))
        self.assertLess(page.index("<video"), page.index("<p>", body_start))
        self.assertIn('id="scene-opening"', page)
        self.assertEqual(page.count('<video '), 4)
        self.assertEqual(page.count('preload="none"'), 4)
        self.assertEqual(page.count('class="scene-media'), 16)
        self.assertIn('id="scene-chapter-cover"', page)
        self.assertIn('id="scene-gateway"', page)
        self.assertIn('id="scene-cryo"', page)
        self.assertIn('id="scene-passage"', page)
        self.assertIn('id="scene-terminal-touch"', page)
        self.assertIn('id="scene-shadow-walk"', page)
        self.assertLess(page.index('id="scene-gateway"'), page.index('Они вошли в короткий кольцевой переход'))
        self.assertIn('id="scene-balcony"', page)
        self.assertIn('id="scene-shadows"', page)
        self.assertEqual(page.count('<section id="ambient-'), 3)
        self.assertIn('id="ambient-abyss"', page)
        self.assertNotIn('scene-ambient-cable', page)
        self.assertIn('scene-ambient-shadows', page)
        self.assertIn('scene-ambient-cube', page)
        self.assertNotIn('id="ambient-cable"', page)
        self.assertIn('id="ambient-shadows"', page)
        self.assertIn('id="ambient-cube"', page)
        self.assertIn('%202.mp4', page)
        self.assertIn('id="scene-ending"', page)
        self.assertNotIn("autoplay", page)
        self.assertNotIn("[video]", page)
        self.assertNotIn("[scene]", page)
        self.assertNotIn("[ambient]", page)
        self.assertIn("— Ваад…", page)
        self.assertNotIn("«печатала»", page)
        self.assertNotIn("— Я — твое завтра. Вадим.", page)

    def test_all_illustrations_are_exported_and_reachable(self):
        images = set()
        for cid in range(1, 12):
            page = self.read(f"read/{cid}/index.html")
            images.update(re.findall(r'<img src="(/static/chapter-images/[^"]+)"', page))
            self.assertNotIn('"/chapter-images/', page)
        self.assertGreater(len(images), 0)
        for src in images:
            self.assertTrue((self.out / src.lstrip("/")).is_file(), src)
        chapter_one = self.read("read/2/index.html")
        for filename in (
            "chapter-01-opening-pulkovo-team-v003.png",
            "pulkovo-kamchatka-map-v001.png",
            "kamchatka-birches.png",
            "kamchatka-closed-door-shadow-v002.png",
            "lighter.png",
        ):
            self.assertIn(f'/static/chapter-01/{filename}', chapter_one)
            self.assertTrue((self.out / "static/chapter-01" / filename).is_file(), filename)
        self.assertNotIn('/static/chapter-01/chapter-01-cover-v002-pulkovo.png', chapter_one)
        self.assertNotIn('/static/chapter-01/pulkovo-team-briefing-v001.png', chapter_one)
        mobile_videos = (
            "pulkovo-airport-opening-v001",
            "airport-memory",
            "flight-window",
            "gravimobile-night-drive",
            "gravimobile-approach",
        )
        self.assertEqual(chapter_one.count('preload="none"'), len(mobile_videos))
        for stem in mobile_videos:
            self.assertIn(f'/static/chapter-01/{stem}-mobile.mp4', chapter_one)
            self.assertIn(f'/static/chapter-01/{stem}-mobile-poster.jpg', chapter_one)
            self.assertNotIn(f'/static/chapter-01/{stem}.mp4', chapter_one)

    def test_static_counts_and_no_backend_counters(self):
        chapters = self.read("chapters/index.html")
        self.assertNotIn("прочт.", chapters)
        self.assertEqual(chapters.count('href="/read/'), 11)
        prologue = self.read("read/1/index.html")
        self.assertNotIn("likeBtn", prologue)
        self.assertIn("shareBtn", prologue)
        version = json.loads(self.read("version.json"))
        self.assertEqual(version["chapters"], 11)
        self.assertTrue(version["noindex"])
        self.assertTrue((self.out / "static/video/prologue.mp4").is_file())
        self.assertGreater(len(list((self.out / "static/chapter-images").glob("*.jpg"))), 0)
        self.assertEqual(len(list((self.out / "static/chapter-01").glob("*.mp4"))), 12)
        for filename in (
            "pulkovo-airport-opening-v001-mobile.mp4",
            "airport-memory-mobile.mp4",
            "flight-window-mobile.mp4",
            "gravimobile-night-drive-mobile.mp4",
            "gravimobile-approach-mobile.mp4",
        ):
            self.assertTrue((self.out / "static/chapter-01" / filename).is_file(), filename)

    def test_robots_and_rewrites_are_present(self):
        self.assertIn("Disallow: /", self.read("robots.txt"))
        htaccess = self.read(".htaccess")
        self.assertIn("RewriteRule ^read/([0-9]+)/?$ read/$1/index.html", htaccess)
        self.assertIn("X-Robots-Tag", htaccess)
        self.assertIn("ErrorDocument 404 /404.html", htaccess)


if __name__ == "__main__":
    unittest.main()
