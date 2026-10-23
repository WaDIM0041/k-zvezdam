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

    def test_prologue_starts_with_video_player(self):
        page = self.read("read/1/index.html")
        body_start = page.index('id="readBody">')
        self.assertLess(page.index("<video"), page.index("<p>", body_start))
        self.assertIn('<video src="/static/video/prologue.mp4" controls playsinline preload="metadata"', page)
        self.assertNotIn("autoplay", page)
        self.assertIn("Открыть видео отдельно", page)
        self.assertNotIn("[video]", page)

    def test_all_illustrations_are_exported_and_reachable(self):
        images = set()
        for cid in range(1, 12):
            page = self.read(f"read/{cid}/index.html")
            images.update(re.findall(r'<img src="(/static/chapter-images/[^"]+)"', page))
            self.assertNotIn('"/chapter-images/', page)
        self.assertEqual(len(images), 28)
        for src in images:
            self.assertTrue((self.out / src.lstrip("/")).is_file(), src)

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
        self.assertEqual(len(list((self.out / "static/chapter-images").glob("*.jpg"))), 28)

    def test_robots_and_rewrites_are_present(self):
        self.assertIn("Disallow: /", self.read("robots.txt"))
        htaccess = self.read(".htaccess")
        self.assertIn("RewriteRule ^read/([0-9]+)/?$ read/$1/index.html", htaccess)
        self.assertIn("X-Robots-Tag", htaccess)
        self.assertIn("ErrorDocument 404 /404.html", htaccess)


if __name__ == "__main__":
    unittest.main()
