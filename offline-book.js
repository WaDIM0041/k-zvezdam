(function () {
  var button = document.getElementById('offlineSave');
  var status = document.getElementById('offlineStatus');
  if (!button || !status) return;
  if (!('serviceWorker' in navigator) || !('caches' in window)) {
    button.disabled = true;
    status.textContent = 'Этот браузер не поддерживает сохранение книги.';
    return;
  }
  var root = new URL('./', document.baseURI);
  var cacheName = 'kzvezdam-book-v1';

  button.addEventListener('click', async function () {
    button.disabled = true;
    status.textContent = 'Подготавливаем книгу…';
    var tempName = cacheName + '-download';
    try {
      await navigator.serviceWorker.register(new URL('book-worker.js', root), {scope: root.pathname});
      await navigator.serviceWorker.ready;
      await caches.delete(tempName);
      var cache = await caches.open(tempName);
      var paths = [root.href, new URL('chapters/', root).href];
      document.querySelectorAll('a.chapter-preview[href]').forEach(function (link) {
        paths.push(new URL(link.href).href);
      });
      var uniquePages = Array.from(new Set(paths));
      if (uniquePages.length < 3) throw new Error('Главы не найдены');
      var assets = new Set();
      for (var i = 0; i < uniquePages.length; i++) {
        status.textContent = 'Сохраняем страницы: ' + (i + 1) + ' из ' + uniquePages.length + '…';
        var response = await fetch(uniquePages[i]);
        if (!response.ok) throw new Error('Не удалось загрузить страницу');
        await cache.put(uniquePages[i], response.clone());
        var page = new DOMParser().parseFromString(await response.text(), 'text/html');
        page.querySelectorAll('img[src],video[poster],link[rel="stylesheet"][href],script[src]').forEach(function (element) {
          var reference = element.tagName === 'VIDEO' ? element.getAttribute('poster') : (element.getAttribute('src') || element.getAttribute('href'));
          var url = new URL(reference, response.url);
          if (url.origin === root.origin && url.pathname.startsWith(root.pathname)) assets.add(url.href);
        });
      }
      var items = Array.from(assets);
      for (var n = 0; n < items.length; n++) {
        status.textContent = 'Сохраняем оформление и изображения: ' + (n + 1) + ' из ' + items.length + '…';
        var asset = await fetch(items[n]);
        if (!asset.ok) throw new Error('Не удалось загрузить изображение или оформление');
        await cache.put(items[n], asset);
      }
      var old = await caches.open(cacheName);
      var requests = await cache.keys();
      for (var j = 0; j < requests.length; j++) await old.put(requests[j], await cache.match(requests[j]));
      await caches.delete(tempName);
      status.textContent = 'Книга сохранена. Теперь её можно читать без интернета на этом устройстве.';
      button.textContent = '↻ Обновить сохранённую книгу';
    } catch (error) {
      await caches.delete(tempName);
      status.textContent = 'Не удалось сохранить книгу. Проверьте интернет и свободное место, затем попробуйте ещё раз.';
    } finally {
      button.disabled = false;
    }
  });
})();
