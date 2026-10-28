"""Local security and reading smoke tests for the Flask preview."""
import hashlib
import io
import json
import re
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import app as site


class SiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name)
        site.app.config.update(
            TESTING=True,
            SECRET_KEY="test-only-session-key",
            DATA_DIR=str(self.data),
            DB_PATH=str(self.data / "reader.sqlite"),
            UPLOAD_DIR=str(self.data / "uploads"),
            CHAPTER_IMAGE_DIR=str(Path(site.__file__).resolve().parent / "static" / "chapter-images"),
            ADMIN_PASSWORD="пароль✓",
            PREVIEW_NOINDEX=True,
            SITE_ORIGIN="https://k-zvezdam.ru",
        )
        with site.app.app_context():
            site.init_db(Path(site.app.config["DB_PATH"]))
        self.client = site.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def csrf(self, response=None):
        if response is None:
            response = self.client.get("/admin/login")
        match = re.search(rb'<meta name="csrf-token" content="([^"]+)"', response.data)
        self.assertIsNotNone(match)
        return match.group(1).decode("ascii")

    def login(self, next_url="/admin"):
        page = self.client.get("/admin/login")
        token = self.csrf(page)
        return self.client.post("/admin/login", data={
            "_csrf_token": token,
            "password": "пароль✓",
            "next": next_url,
        }, follow_redirects=False)

    def test_public_reading_seo_and_selected_edition(self):
        for path in ("/", "/chapters", "/read/1", "/promo"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertIn("noindex", response.headers["X-Robots-Tag"])
            self.assertIn(b"rel=\"canonical\"", response.data)
        self.assertIn(b"Disallow: /", self.client.get("/robots.txt").data)
        with site.app.app_context():
            db = site.connect_db(Path(site.app.config["DB_PATH"]))
            try:
                rows = db.execute("SELECT position,title,published FROM chapters ORDER BY position").fetchall()
            finally:
                db.close()
        self.assertEqual(len(rows), 11)
        self.assertEqual([row["position"] for row in rows], list(range(11)))
        self.assertEqual([row["title"] for row in rows[1:4]], ["Синий огонь", "Призрак в кадре", "Голос из статики"])
        self.assertTrue(all(row["published"] for row in rows))

    def test_all_seeded_illustration_references_resolve(self):
        data = json.loads((Path(site.__file__).resolve().parent / "chapters_seed.json").read_text(encoding="utf-8"))
        names = set()
        for chapter in data:
            for raw in re.findall(r"\[img\](.*?)\[/img\]", chapter["body"], re.S):
                names.add(Path(raw.rsplit("/", 1)[-1]).name)
        self.assertEqual(len(names), 28)
        for name in sorted(names):
            response = self.client.get("/chapter-images/" + name)
            self.assertEqual(response.status_code, 200, name)
            self.assertEqual(response.mimetype, "image/jpeg")
            response.close()

    def test_provenance_hashes_match_bodies_and_images(self):
        root = Path(site.__file__).resolve().parent
        provenance = json.loads((root / "CONTENT-PROVENANCE.json").read_text(encoding="utf-8"))
        seed = json.loads((root / "chapters_seed.json").read_text(encoding="utf-8"))
        self.assertEqual(len(provenance["chapters"]), len(seed))
        for record, chapter in zip(provenance["chapters"], seed):
            self.assertEqual(record["position"], chapter["position"])
            self.assertEqual(record["bodySha256"], hashlib.sha256(chapter["body"].encode("utf-8")).hexdigest())
        for image in provenance["images"]:
            data = (root / "static" / "chapter-images" / image["filename"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), image["sha256"])

    def test_admin_fails_closed_without_password(self):
        site.app.config["ADMIN_PASSWORD"] = ""
        self.assertEqual(self.client.get("/admin/login").status_code, 503)
        self.assertEqual(self.client.get("/admin").status_code, 503)
        site.app.config["ADMIN_PASSWORD"] = "пароль✓"

    def test_login_csrf_unicode_password_and_safe_next(self):
        response = self.login("https://attacker.example/path")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/admin")
        self.assertEqual(self.client.get("/admin").status_code, 200)
        self.assertEqual(self.client.post("/admin/logout").status_code, 400)
        token = self.csrf(self.client.get("/admin"))
        logout = self.client.post("/admin/logout", data={"_csrf_token": token})
        self.assertEqual(logout.status_code, 302)

    def test_malformed_next_and_non_ascii_csrf_fail_safely(self):
        with site.app.test_request_context():
            self.assertEqual(site._safe_next("https://[bad"), "/admin")
            self.assertEqual(site._safe_next("//attacker.example"), "/admin")
            self.assertEqual(site._safe_next("/%5c%5cattacker.example"), "/admin")
        self.assertEqual(self.client.post("/like/1", headers={"X-CSRF-Token": "токен"}).status_code, 400)

    def test_unsafe_media_and_video_hosts_are_not_rendered(self):
        with site.app.test_request_context():
            markup = str(site.render_body("[img]javascript:alert(1)[/img]\n\n[video]https://youtube.com.attacker.test/video/abc123456[/video]"))
        self.assertNotIn("javascript:", markup.lower())
        self.assertNotIn("<iframe", markup.lower())
        self.assertIsNone(site._valid_web_url("https://[broken"))
        embed = site._video_embed("https://youtube.com.attacker.test/video/abc123456").lower()
        self.assertNotIn("youtube-nocookie.com/embed", embed)
        self.assertIn("noopener noreferrer", embed)

    def test_chapter_video_placement_and_safe_local_urls(self):
        with site.app.test_request_context():
            for body in (
                '[video]/static/video/prologue.mp4[/video]\n\nНачало главы',
                'До ролика\n\n[video]/static/video/prologue.mp4[/video]\n\nПосле ролика',
            ):
                markup = str(site.render_body(body))
                self.assertIn('controls playsinline preload="metadata"', markup)
                self.assertIn('src="/static/video/prologue.mp4"', markup)
                self.assertNotIn('autoplay', markup)
                if 'До ролика' in body:
                    self.assertLess(markup.index('До ролика'), markup.index('<video'))
                    self.assertLess(markup.index('</video>'), markup.index('После ролика'))
            for unsafe in ('javascript:alert(1)', '//attacker.test/a.mp4', '/%2e%2e/a.mp4'):
                self.assertNotIn('<video', site._video_embed(unsafe))

    def test_curated_prologue_media_and_finale(self):
        from urllib.parse import unquote
        root = Path(site.__file__).resolve().parent
        media = json.loads((root / 'content/prologue-media.json').read_text(encoding='utf-8'))
        self.assertEqual(len(media), 11)
        for item in media.values():
            for field in ('src', 'poster'):
                if field in item:
                    self.assertTrue((root / unquote(item[field]).lstrip('/')).is_file())
        page = self.client.get('/read/1').get_data(as_text=True)
        self.assertEqual(page.count('<video '), 4)
        self.assertEqual(page.count('class="scene-media'), 11)
        self.assertIn('id="scene-chapter-cover"', page)
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
        self.assertIn('— Ваад…', page)
        self.assertNotIn('«печатала»', page)
        self.assertNotIn('[scene]', page)
        self.assertNotIn('[ambient]', page)
        abyss = page.split('id="ambient-abyss"', 1)[1].split('</section>', 1)[0]
        self.assertIn('Всё пытаюсь понять, где здесь низ.', abyss)
        self.assertIn('Дальше луч терялся.', abyss)
        self.assertNotIn('У следующей колонны', abyss)
        self.assertNotIn('scene-ambient-abyss', self.client.get('/read/2').get_data(as_text=True))

    def test_upload_requires_auth_csrf_and_valid_image_bytes(self):
        page = self.client.get("/admin/login")
        token = self.csrf(page)
        unauth = self.client.post("/admin/upload", data={"file": (io.BytesIO(b"bad"), "x.jpg")}, headers={"X-CSRF-Token": token})
        self.assertEqual(unauth.status_code, 302)
        self.login()
        token = self.csrf(self.client.get("/admin"))
        bad = self.client.post("/admin/upload", data={"file": (io.BytesIO(b"not an image"), "fake.jpg")}, headers={"X-CSRF-Token": token})
        self.assertEqual(bad.status_code, 400)
        output = io.BytesIO()
        Image.new("RGB", (8, 8), color="blue").save(output, format="JPEG")
        good = self.client.post("/admin/upload", data={"file": (io.BytesIO(output.getvalue()), "cover.jpg")}, headers={"X-CSRF-Token": token})
        self.assertEqual(good.status_code, 201)
        uploaded_url = good.get_json()["url"]
        self.assertTrue(uploaded_url.startswith("/media/"))
        media_response = self.client.get(uploaded_url)
        self.assertEqual(media_response.status_code, 200)
        media_response.close()
        mismatch = self.client.post("/admin/upload", data={"file": (io.BytesIO(output.getvalue()), "cover.png")}, headers={"X-CSRF-Token": token})
        self.assertEqual(mismatch.status_code, 400)
        self.assertEqual(self.client.post("/admin/upload", data={"file": (io.BytesIO(output.getvalue()), "cover.jpg")}).status_code, 400)

    def test_admin_editor_rejects_unsafe_audio_url_and_escapes_body(self):
        self.login()
        token = self.csrf(self.client.get("/admin"))
        result = self.client.post("/admin/new", data={
            "_csrf_token": token, "kind": "Глава", "position": "11", "title": "Тест",
            "body": "<script>alert(1)</script>", "audio_url": "javascript:alert(1)", "published": "on",
        })
        self.assertEqual(result.status_code, 400)
        token = self.csrf(self.client.get("/admin"))
        result = self.client.post("/admin/new", data={
            "_csrf_token": token, "kind": "Глава", "position": "11", "title": "Тест",
            "body": "<script>alert(1)</script>", "audio_url": "", "published": "on",
        })
        self.assertEqual(result.status_code, 302)
        rows = self.client.get("/admin")
        chapter_id = max(int(value) for value in re.findall(rb'href="/admin/edit/(\d+)"', rows.data))
        rendered = self.client.get(f"/read/{chapter_id}")
        self.assertIn(b"&lt;script&gt;", rendered.data)
        self.assertNotIn(b"<script>alert(1)</script>", rendered.data)

    def test_admin_draft_edit_publish_move_delete_flow_uses_csrf(self):
        self.login()
        token = self.csrf(self.client.get("/admin"))
        created = self.client.post("/admin/new", data={
            "_csrf_token": token, "kind": "Глава", "position": "99",
            "title": "Проверочная черновая", "body": "Текст",
        }, follow_redirects=False)
        self.assertEqual(created.status_code, 302)
        with site.app.app_context():
            db = site.connect_db(Path(site.app.config["DB_PATH"]))
            try:
                row = db.execute("SELECT id,published FROM chapters WHERE title=?", ("Проверочная черновая",)).fetchone()
            finally:
                db.close()
        cid = row["id"]
        self.assertEqual(row["published"], 0)
        self.assertEqual(self.client.get(f"/read/{cid}").status_code, 404)
        admin = self.client.get("/admin")
        self.assertNotIn(f'href="/read/{cid}"'.encode(), admin.data)

        editor = self.client.get(f"/admin/edit/{cid}")
        self.assertEqual(editor.status_code, 200)
        token = self.csrf(editor)
        edited = self.client.post(f"/admin/edit/{cid}", data={
            "_csrf_token": token, "kind": "Глава", "position": "99",
            "title": "Проверочная глава", "body": "Обновлённый текст",
        })
        self.assertEqual(edited.status_code, 302)
        token = self.csrf(self.client.get("/admin"))
        published = self.client.post(f"/admin/toggle/{cid}", data={"_csrf_token": token})
        self.assertEqual(published.status_code, 302)
        self.assertEqual(self.client.get(f"/read/{cid}").status_code, 200)
        token = self.csrf(self.client.get("/admin"))
        moved = self.client.post(f"/admin/move/{cid}/up", data={"_csrf_token": token})
        self.assertEqual(moved.status_code, 302)
        token = self.csrf(self.client.get("/admin"))
        deleted = self.client.post(f"/admin/delete/{cid}", data={"_csrf_token": token})
        self.assertEqual(deleted.status_code, 302)
        self.assertEqual(self.client.get(f"/read/{cid}").status_code, 404)

if __name__ == "__main__":
    unittest.main()
