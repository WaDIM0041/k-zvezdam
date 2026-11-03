/* Кнопки «Поделиться» и «Добавить в закладки» в подвале сайта */
(function(){
  var KEY = 'kz_bookmarks';
  var shareBtn = document.getElementById('footerShare');
  var bmBtn = document.getElementById('footerBookmark');
  var mineBtn = document.getElementById('footerBookmarks');
  var panel = document.getElementById('kzBmPanel');
  var list = document.getElementById('kzBmList');
  var closeBtn = document.getElementById('kzBmClose');
  if (!shareBtn && !bmBtn) return;

  var star = bmBtn ? bmBtn.querySelector('.footer-act-star') : null;
  var bmText = bmBtn ? bmBtn.querySelector('.footer-act-text') : null;
  var mineCount = mineBtn ? mineBtn.querySelector('.footer-act-count') : null;

  function key(p){
    return String(p || '/').replace(/\/+$/, '') || '/';
  }
  function pageKey(){
    return key(location.pathname);
  }
  function pageTitle(){
    var t = (document.title || '').replace(/\s+/g, ' ').trim();
    t = t.replace(/\s*—\s*Через время к звёздам$/, '');
    if (!t || t === 'Через время к звёздам') t = 'Главная';
    return t;
  }
  function read(){
    var a = null;
    try { a = JSON.parse(localStorage.getItem(KEY) || '[]'); } catch (e) { a = null; }
    if (!a || typeof a.length !== 'number') return [];
    var out = [];
    for (var i = 0; i < a.length; i++) {
      var x = a[i];
      if (x && x.url && x.title) out.push({ url: String(x.url), title: String(x.title) });
    }
    return out;
  }
  function write(a){
    try { localStorage.setItem(KEY, JSON.stringify(a)); } catch (e) {}
  }
  function has(a, k){
    for (var i = 0; i < a.length; i++) if (key(a[i].url) === k) return true;
    return false;
  }

  function renderList(a){
    if (!list) return;
    while (list.firstChild) list.removeChild(list.firstChild);
    if (!a.length) {
      var empty = document.createElement('li');
      empty.className = 'kz-bm-empty';
      empty.textContent = 'Пока пусто. Откройте главу и нажмите «Добавить в закладки» — она появится здесь.';
      list.appendChild(empty);
      return;
    }
    for (var i = 0; i < a.length; i++) {
      var row = document.createElement('li');
      row.className = 'kz-bm-item';
      var link = document.createElement('a');
      link.href = a[i].url;
      link.textContent = a[i].title;
      if (key(a[i].url) === pageKey()) link.className = 'is-current';
      var del = document.createElement('button');
      del.type = 'button';
      del.className = 'kz-bm-remove';
      del.setAttribute('data-url', a[i].url);
      del.setAttribute('aria-label', 'Убрать из закладок: ' + a[i].title);
      del.textContent = '×';
      row.appendChild(link);
      row.appendChild(del);
      list.appendChild(row);
    }
  }

  function sync(){
    var a = read(), on = has(a, pageKey());
    if (bmBtn) {
      bmBtn.setAttribute('aria-pressed', on ? 'true' : 'false');
      if (on) bmBtn.classList.add('is-on'); else bmBtn.classList.remove('is-on');
      if (star) star.textContent = on ? '★' : '☆';
      if (bmText) bmText.textContent = on ? 'В закладках' : 'Добавить в закладки';
    }
    if (mineBtn) {
      mineBtn.hidden = !a.length;
      if (mineCount) mineCount.textContent = a.length;
    }
    renderList(a);
  }

  function flash(msg){
    if (!bmText) return;
    bmText.textContent = msg;
    setTimeout(sync, 1700);
  }

  if (bmBtn) bmBtn.addEventListener('click', function(){
    var a = read(), k = pageKey();
    if (has(a, k)) {
      var out = [];
      for (var i = 0; i < a.length; i++) if (key(a[i].url) !== k) out.push(a[i]);
      write(out);
      sync();
      flash('Убрано из закладок');
    } else {
      a.unshift({ url: k, title: pageTitle() });
      write(a);
      sync();
      flash('Сохранено');
    }
  });

  if (shareBtn) shareBtn.addEventListener('click', function(){
    var url = location.href;
    var title = pageTitle() + ' — Через время к звёздам';
    var original = shareBtn.textContent;
    function copied(){
      shareBtn.textContent = '✓ Ссылка скопирована';
      setTimeout(function(){ shareBtn.textContent = original; }, 2000);
    }
    function fallback(){
      window.open('https://vk.com/share.php?url=' + encodeURIComponent(url), '_blank');
    }
    if (navigator.share) {
      navigator.share({ title: title, url: url }).then(null, function(){});
      return;
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(copied, fallback);
      return;
    }
    fallback();
  });

  function openPanel(){
    if (!panel) return;
    panel.hidden = false;
    if (closeBtn) closeBtn.focus();
  }
  function closePanel(){
    if (panel) panel.hidden = true;
  }

  if (mineBtn) mineBtn.addEventListener('click', function(){
    if (panel && panel.hidden) openPanel(); else closePanel();
  });
  if (closeBtn) closeBtn.addEventListener('click', closePanel);
  document.addEventListener('keydown', function(e){
    if (e.key === 'Escape' || e.keyCode === 27) closePanel();
  });
  if (list) list.addEventListener('click', function(e){
    var t = e.target;
    if (!t || !t.classList || !t.classList.contains('kz-bm-remove')) return;
    var url = t.getAttribute('data-url'), a = read(), out = [];
    for (var i = 0; i < a.length; i++) if (a[i].url !== url) out.push(a[i]);
    write(out);
    sync();
    if (!out.length) closePanel();
  });

  sync();
})();
