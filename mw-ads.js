/* mw-ads.js — 記事末の広告枠に、候補からランダムに1つだけ描画する。
 *
 * 🚨 「1つだけ描く」ことが要点。旧方式は PC/SP 両方を HTML に書いて CSS で隠していたが、
 *    ブラウザは display:none の <img> も読み込むため、見えていない側の 1x1 計測gif まで
 *    毎回飛び、表示回数が実際の約2倍で記録されていた（2026-09-10 Chromium 実測）。
 *
 * ⚠️ このファイルは inject_ads.py が CREATIVES から自動生成する。直接編集しないこと。
 */
(function () {
  var C = {
  "kabu": {
    "alt": "DMM株",
    "pc": {
      "href": "https://px.a8.net/svt/ejp?a8mat=4B5R09+7CXWZ6+1WP2+15Q22P",
      "img": "https://www27.a8.net/svt/bgt?aid=260608761445&wid=001&eno=01&mid=s00000008903007008000&mc=1",
      "gif": "https://www15.a8.net/0.gif?a8mat=4B5R09+7CXWZ6+1WP2+15Q22P",
      "w": 468,
      "h": 60
    },
    "sp": {
      "href": "https://px.a8.net/svt/ejp?a8mat=4B5R09+7CXWZ6+1WP2+15PUCX",
      "img": "https://www26.a8.net/svt/bgt?aid=260608761445&wid=001&eno=01&mid=s00000008903007007000&mc=1",
      "gif": "https://www16.a8.net/0.gif?a8mat=4B5R09+7CXWZ6+1WP2+15PUCX",
      "w": 320,
      "h": 50
    }
  },
  "cfd": {
    "alt": "DMM CFD",
    "pc": {
      "href": "https://px.a8.net/svt/ejp?a8mat=4B5R09+79YQYA+1WP2+NY1Y9",
      "img": "https://www25.a8.net/svt/bgt?aid=260608761440&wid=001&eno=01&mid=s00000008903004022000&mc=1",
      "gif": "https://www15.a8.net/0.gif?a8mat=4B5R09+79YQYA+1WP2+NY1Y9",
      "w": 468,
      "h": 60
    },
    "sp": {
      "href": "https://px.a8.net/svt/ejp?a8mat=4B5R09+79YQYA+1WP2+NX735",
      "img": "https://www27.a8.net/svt/bgt?aid=260608761440&wid=001&eno=01&mid=s00000008903004018000&mc=1",
      "gif": "https://www16.a8.net/0.gif?a8mat=4B5R09+79YQYA+1WP2+NX735",
      "w": 234,
      "h": 60
    }
  },
  "fx": {
    "alt": "JFX株式会社",
    "pc": {
      "href": "https://px.a8.net/svt/ejp?a8mat=4BC736+9U8XPU+25B2+61JSH",
      "img": "https://www23.a8.net/svt/bgt?aid=260909538595&wid=001&eno=01&mid=s00000010019001015000&mc=1",
      "gif": "https://www16.a8.net/0.gif?a8mat=4BC736+9U8XPU+25B2+61JSH",
      "w": 468,
      "h": 60
    },
    "sp": {
      "href": "https://px.a8.net/svt/ejp?a8mat=4BC736+9U8XPU+25B2+61C2P",
      "img": "https://www21.a8.net/svt/bgt?aid=260909538595&wid=001&eno=01&mid=s00000010019001014000&mc=1",
      "gif": "https://www10.a8.net/0.gif?a8mat=4BC736+9U8XPU+25B2+61C2P",
      "w": 234,
      "h": 60
    }
  }
};
  var SP = "(max-width:520px)";

  function el(tag, attrs) {
    var e = document.createElement(tag);
    for (var k in attrs) { if (attrs[k] !== null) e.setAttribute(k, attrs[k]); }
    return e;
  }

  function render(box) {
    var slot = box.querySelector(".mw-ad-slot");
    if (!slot || slot.getAttribute("data-mw-done")) { return; }
    var keys = (box.getAttribute("data-mw-ads") || "").split(",").filter(function (k) { return C[k]; });
    if (!keys.length) { return; }
    var c = C[keys[Math.floor(Math.random() * keys.length)]];
    var v = (window.matchMedia && window.matchMedia(SP).matches) ? c.sp : c.pc;

    var a = el("a", {href: v.href, rel: "nofollow noopener", target: "_blank"});
    a.appendChild(el("img", {src: v.img, width: v.w, height: v.h, alt: c.alt, border: "0"}));
    slot.appendChild(a);
    slot.appendChild(el("img", {src: v.gif, width: 1, height: 1, alt: "", border: "0"}));
    slot.setAttribute("data-mw-done", "1");
  }

  function run() {
    var boxes = document.querySelectorAll(".mw-ad[data-mw-ads]");
    for (var i = 0; i < boxes.length; i++) { render(boxes[i]); }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();
