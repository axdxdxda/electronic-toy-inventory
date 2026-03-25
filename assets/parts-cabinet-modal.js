/**
 * 在功課頁以浮層 iframe 開啟 parts-cabinet.html，避免整頁跳轉。
 * - body 可設 data-cabinet-modal-url（預設 ../parts-cabinet.html）
 * - data-parts-cabinet-fab="0" 可隱藏右下角按鈕
 * - 連結加 class cabinet-modal-link 則改為開浮層（Ctrl/⌘ 點擊仍開新分頁）
 */
(function () {
  var MODAL_ID = "partsCabinetModal";
  var DEFAULT_URL = "../parts-cabinet.html";

  function cabinetUrlFromBody() {
    var u = document.body && document.body.getAttribute("data-cabinet-modal-url");
    return u && u.trim() ? u.trim() : DEFAULT_URL;
  }

  var lastUrl = "";

  function ensureModal() {
    var el = document.getElementById(MODAL_ID);
    if (el) return el;

    el = document.createElement("div");
    el.id = MODAL_ID;
    el.className = "parts-cabinet-modal";
    el.setAttribute("role", "dialog");
    el.setAttribute("aria-modal", "true");
    el.setAttribute("aria-hidden", "true");
    el.setAttribute("aria-label", "零件收納櫃");
    el.innerHTML =
      '<div class="parts-cabinet-modal__backdrop" data-close="1"></div>' +
      '<div class="parts-cabinet-modal__dialog">' +
      '<header class="parts-cabinet-modal__header">' +
      "<div>" +
      "<strong>零件收納櫃</strong>" +
      '<span class="parts-cabinet-modal__sub">關閉後仍在原功課頁，不用重新找進度</span>' +
      "</div>" +
      '<div class="parts-cabinet-modal__actions">' +
      '<button type="button" class="parts-cabinet-modal__newtab">新分頁開啟</button>' +
      '<button type="button" class="parts-cabinet-modal__close" aria-label="關閉收納櫃">✕</button>' +
      "</div>" +
      "</header>" +
      '<iframe class="parts-cabinet-modal__iframe" title="零件收納櫃導覽"></iframe>' +
      "</div>";

    document.body.appendChild(el);

    var iframe = el.querySelector("iframe");
    var closeBtn = el.querySelector(".parts-cabinet-modal__close");
    var newTabBtn = el.querySelector(".parts-cabinet-modal__newtab");
    var backdrop = el.querySelector(".parts-cabinet-modal__backdrop");

    function onDocumentEscape(e) {
      if (e.key === "Escape" && el.classList.contains("is-open")) close();
    }

    function close() {
      el.classList.remove("is-open");
      el.setAttribute("aria-hidden", "true");
      document.body.classList.remove("parts-cabinet-modal--open");
      document.removeEventListener("keydown", onDocumentEscape);
      if (iframe) iframe.src = "about:blank";
    }

    el._partsCabinetOnEscape = onDocumentEscape;

    closeBtn.addEventListener("click", close);
    backdrop.addEventListener("click", close);
    newTabBtn.addEventListener("click", function () {
      if (lastUrl) window.open(lastUrl, "_blank", "noopener,noreferrer");
    });

    return el;
  }

  function openModal(url) {
    var el = ensureModal();
    var iframe = el.querySelector("iframe");
    /* ensureModal 內 closure：透過自訂屬性取得 close / onDocumentEscape */
    var onDocumentEscape = el._partsCabinetOnEscape;
    if (onDocumentEscape) {
      document.removeEventListener("keydown", onDocumentEscape);
    }
    lastUrl = url;
    if (iframe) iframe.src = url;
    el.classList.add("is-open");
    el.setAttribute("aria-hidden", "false");
    document.body.classList.add("parts-cabinet-modal--open");
    if (onDocumentEscape) document.addEventListener("keydown", onDocumentEscape);
    var closeBtn = el.querySelector(".parts-cabinet-modal__close");
    if (closeBtn) closeBtn.focus();
  }

  function shouldIgnoreClick(e) {
    if (e.defaultPrevented) return true;
    if (e.button !== 0) return true;
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return true;
    return false;
  }

  function init() {
    document.addEventListener("click", function (e) {
      var a = e.target.closest && e.target.closest("a.cabinet-modal-link");
      if (!a || !a.getAttribute("href")) return;
      if (shouldIgnoreClick(e)) return;
      e.preventDefault();
      openModal(a.getAttribute("href"));
    });

    if (document.body.getAttribute("data-parts-cabinet-fab") === "0") return;

    var fab = document.createElement("button");
    fab.type = "button";
    fab.className = "parts-cabinet-fab";
    fab.setAttribute("aria-label", "在畫面中開啟零件收納櫃（不離開本頁）");
    fab.innerHTML =
      '<span class="parts-cabinet-fab__icon" aria-hidden="true">🗄️</span>' +
      '<span class="parts-cabinet-fab__text">收納櫃</span>';
    fab.title = "對照零件櫃位（不跳轉頁面）";
    fab.addEventListener("click", function () {
      openModal(cabinetUrlFromBody());
    });
    document.body.appendChild(fab);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
