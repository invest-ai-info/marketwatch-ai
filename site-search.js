/* site-search.js — サイト全体の記事横断検索（全ページ共通）
 *
 * 設計:
 *  - フローティング🔍ボタン＋検索オーバーレイ＋スタイルを自己注入（navバーには触らない）。
 *  - 検索データは guides.html を「単一ソース」として初回検索時に1度だけ取得・解析。
 *    索引ファイル不要・ビルド改修不要。publish_article.py 等で guides.html にカードが増えれば自動反映。
 *  - guides.html 上では DOM を直読みして再取得を省略。
 *  - 検索対象: タイトル＋説明＋カテゴリ（スペース区切りで多語 AND）。
 *  - キーボード: "/" または Ctrl/Cmd+K で開く、Esc 閉じる、↑↓ 移動、Enter 遷移。
 *  - ライト/ダーク両対応（body.dark を参照）。
 */
(function () {
  if (window.__siteSearchLoaded) return;
  window.__siteSearchLoaded = true;

  var MAX_RESULTS = 60;

  /* ---------- スタイル注入 ---------- */
  var css = ''
    + '#ss-btn{position:fixed;top:16px;right:66px;width:42px;height:42px;border-radius:50%;border:1px solid #d0d7de;background:#fff;cursor:pointer;z-index:9999;box-shadow:0 2px 8px rgba(0,0,0,.1);font-size:18px;display:flex;align-items:center;justify-content:center;padding:0}'
    + 'body.dark #ss-btn{background:#161b22;border-color:#30363d}'
    + '#ss-overlay{position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:10000;display:none;align-items:flex-start;justify-content:center;padding:64px 16px}'
    + '#ss-overlay.open{display:flex}'
    + '#ss-modal{width:100%;max-width:640px;background:#fff;border:1px solid #d0d7de;border-radius:14px;box-shadow:0 12px 40px rgba(0,0,0,.25);overflow:hidden;display:flex;flex-direction:column;max-height:80vh;font-family:inherit}'
    + 'body.dark #ss-modal{background:#0d1117;border-color:#30363d}'
    + '#ss-head{display:flex;align-items:center;gap:10px;padding:14px 16px;border-bottom:1px solid #d0d7de}'
    + 'body.dark #ss-head{border-bottom-color:#30363d}'
    + '#ss-input{flex:1;min-width:0;border:0;outline:0;font-size:1.05rem;font-family:inherit;background:transparent;color:#1f2328}'
    + 'body.dark #ss-input{color:#e6edf3}'
    + '#ss-input::placeholder{color:#8b949e}'
    + '#ss-close{flex:none;border:1px solid #d0d7de;background:transparent;font-size:.72rem;color:#57606a;cursor:pointer;padding:4px 9px;border-radius:6px}'
    + 'body.dark #ss-close{color:#8b949e;border-color:#30363d}'
    + '#ss-status{padding:11px 16px;font-size:.85rem;color:#57606a;border-bottom:1px solid #eaeef2}'
    + 'body.dark #ss-status{color:#8b949e;border-bottom-color:#21262d}'
    + '#ss-status b{color:#0969da}'
    + 'body.dark #ss-status b{color:#79c0ff}'
    + '#ss-results{overflow-y:auto;padding:6px}'
    + '.ss-item{display:block;padding:11px 13px;border-radius:9px;text-decoration:none;cursor:pointer}'
    + '.ss-item:hover,.ss-item.sel{background:#ddf4ff}'
    + 'body.dark .ss-item:hover,body.dark .ss-item.sel{background:#1c2128}'
    + '.ss-cat{font-size:.68rem;font-weight:700;color:#1f6feb;letter-spacing:.03em}'
    + 'body.dark .ss-cat{color:#79c0ff}'
    + '.ss-title{font-size:.95rem;font-weight:700;color:#1f2328;margin-top:2px;line-height:1.4}'
    + 'body.dark .ss-title{color:#e6edf3}'
    + '.ss-desc{font-size:.8rem;color:#57606a;margin-top:3px;line-height:1.5;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}'
    + 'body.dark .ss-desc{color:#8b949e}'
    + '#ss-foot{padding:8px 14px;border-top:1px solid #d0d7de;font-size:.72rem;color:#8b949e;display:flex;gap:14px;flex-wrap:wrap}'
    + 'body.dark #ss-foot{border-top-color:#30363d}'
    + '@media(max-width:600px){#ss-btn{top:14px;right:62px;width:40px;height:40px}#ss-overlay{padding:40px 10px}#ss-foot{display:none}}';
  var styleEl = document.createElement('style');
  styleEl.textContent = css;
  document.head.appendChild(styleEl);

  /* ---------- DOM 構築 ---------- */
  var btn = document.createElement('button');
  btn.id = 'ss-btn';
  btn.type = 'button';
  btn.textContent = '🔍';
  btn.title = '記事を検索（/ または Ctrl+K）';
  btn.setAttribute('aria-label', '記事を検索');

  var overlay = document.createElement('div');
  overlay.id = 'ss-overlay';
  overlay.setAttribute('role', 'dialog');
  overlay.setAttribute('aria-modal', 'true');
  overlay.setAttribute('aria-label', '記事検索');
  overlay.innerHTML =
    '<div id="ss-modal">'
    + '<div id="ss-head">'
    + '<span style="font-size:1.1rem" aria-hidden="true">🔍</span>'
    + '<input id="ss-input" type="search" placeholder="記事を検索（スペース区切りで絞り込み）" autocomplete="off" aria-label="記事を検索">'
    + '<button id="ss-close" type="button" aria-label="閉じる">Esc</button>'
    + '</div>'
    + '<div id="ss-status"></div>'
    + '<div id="ss-results"></div>'
    + '<div id="ss-foot"><span>↑↓ 移動</span><span>Enter 開く</span><span>Esc 閉じる</span></div>'
    + '</div>';

  function mount() {
    document.body.appendChild(btn);
    document.body.appendChild(overlay);
  }
  if (document.body) mount();
  else document.addEventListener('DOMContentLoaded', mount);

  var input = overlay.querySelector('#ss-input');
  var results = overlay.querySelector('#ss-results');
  var status = overlay.querySelector('#ss-status');
  var modal = overlay.querySelector('#ss-modal');

  var index = null;       // [{title,desc,cat,url,hay}]
  var loading = false;
  var loadError = false;
  var itemEls = [];       // 現在表示中の結果要素
  var sel = -1;

  /* ---------- データ取得（guides.html を単一ソースに） ---------- */
  function parseCards(root) {
    var cards = root.querySelectorAll('a.article-card');
    return Array.prototype.map.call(cards, function (c) {
      var pick = function (s) { var e = c.querySelector(s); return e ? e.textContent.trim() : ''; };
      var title = pick('.article-title');
      var desc = pick('.article-desc');
      var cat = pick('.article-badge');
      return {
        title: title, desc: desc, cat: cat,
        url: c.getAttribute('href'),
        hay: (title + ' ' + desc + ' ' + cat).toLowerCase()
      };
    });
  }

  function loadIndex() {
    if (index || loading) return;
    // guides.html 上では DOM を直読みして fetch を省略
    var local = parseCards(document);
    if (local.length > 0) { index = local; render(); return; }
    loading = true;
    render();
    fetch('guides.html', { credentials: 'same-origin' })
      .then(function (r) { if (!r.ok) throw new Error('http ' + r.status); return r.text(); })
      .then(function (html) {
        var doc = new DOMParser().parseFromString(html, 'text/html');
        index = parseCards(doc);
        loading = false;
        render();
      })
      .catch(function () {
        loading = false; loadError = true; render();
      });
  }

  /* ---------- 検索・描画 ---------- */
  function setSel(i) {
    if (itemEls.length === 0) { sel = -1; return; }
    if (i < 0) i = 0;
    if (i > itemEls.length - 1) i = itemEls.length - 1;
    if (sel >= 0 && itemEls[sel]) itemEls[sel].classList.remove('sel');
    sel = i;
    itemEls[sel].classList.add('sel');
    itemEls[sel].scrollIntoView({ block: 'nearest' });
  }

  function render() {
    if (loading && !index) { status.innerHTML = '記事を読み込み中…'; results.innerHTML = ''; itemEls = []; sel = -1; return; }
    if (loadError && !index) { status.innerHTML = '記事一覧の読み込みに失敗しました。時間をおいて再度お試しください。'; results.innerHTML = ''; itemEls = []; sel = -1; return; }

    var q = input.value.toLowerCase().trim();
    var list;
    if (!q) {
      list = index;
      status.innerHTML = '全 <b>' + index.length + '</b> 件の記事 — キーワードを入力して絞り込み';
    } else {
      var terms = q.split(/\s+/).filter(Boolean);
      list = index.filter(function (d) { return terms.every(function (t) { return d.hay.indexOf(t) !== -1; }); });
      status.innerHTML = '<b>' + list.length + '</b> 件ヒット';
    }

    results.innerHTML = '';
    itemEls = [];
    sel = -1;
    if (list.length === 0) {
      status.innerHTML = '「' + input.value.trim() + '」に一致する記事はありません。';
      return;
    }

    var frag = document.createDocumentFragment();
    list.slice(0, MAX_RESULTS).forEach(function (d) {
      var a = document.createElement('a');
      a.className = 'ss-item';
      a.href = d.url;
      a.innerHTML = '<div class="ss-cat"></div><div class="ss-title"></div><div class="ss-desc"></div>';
      a.querySelector('.ss-cat').textContent = d.cat;
      a.querySelector('.ss-title').textContent = d.title;
      a.querySelector('.ss-desc').textContent = d.desc;
      frag.appendChild(a);
      itemEls.push(a);
    });
    if (list.length > MAX_RESULTS) {
      var more = document.createElement('div');
      more.style.cssText = 'padding:10px 13px;font-size:.78rem;color:#8b949e';
      more.textContent = '… 他 ' + (list.length - MAX_RESULTS) + ' 件。キーワードで絞り込んでください。';
      frag.appendChild(more);
    }
    results.appendChild(frag);
    if (q) setSel(0);
  }

  /* ---------- 開閉 ---------- */
  function open() {
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
    loadIndex();
    if (!index && !loading) render();
    else render();
    setTimeout(function () { input.focus(); input.select(); }, 0);
  }
  function close() {
    overlay.classList.remove('open');
    document.body.style.overflow = '';
    btn.focus();
  }
  function isOpen() { return overlay.classList.contains('open'); }

  /* ---------- イベント ---------- */
  btn.addEventListener('click', open);
  overlay.querySelector('#ss-close').addEventListener('click', close);
  overlay.addEventListener('mousedown', function (e) { if (e.target === overlay) close(); });
  input.addEventListener('input', render);

  input.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowDown') { e.preventDefault(); setSel(sel + 1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setSel(sel - 1); }
    else if (e.key === 'Enter') {
      e.preventDefault();
      var target = (sel >= 0 && itemEls[sel]) ? itemEls[sel] : itemEls[0];
      if (target) window.location.href = target.href;
    } else if (e.key === 'Escape') { e.preventDefault(); close(); }
  });

  document.addEventListener('keydown', function (e) {
    var tag = (e.target && e.target.tagName) ? e.target.tagName.toLowerCase() : '';
    var typing = tag === 'input' || tag === 'textarea' || (e.target && e.target.isContentEditable);
    if (!isOpen() && (e.key === '/' ) && !typing) { e.preventDefault(); open(); }
    else if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) { e.preventDefault(); isOpen() ? close() : open(); }
    else if (e.key === 'Escape' && isOpen()) { close(); }
  });
})();
