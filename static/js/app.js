(() => {
  "use strict";
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const THEME_KEY = "taskflow-theme";

  function setUseIcon(element, id) {
    if (!element) return;
    element.setAttribute("href", `#icon-${id}`);
    element.setAttributeNS("http://www.w3.org/1999/xlink", "href", `#icon-${id}`);
  }

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(THEME_KEY, theme);
    $$('[data-theme-use]').forEach((use) => setUseIcon(use, theme === "dark" ? "sun" : "moon"));
  }

  function initTheme() {
    const saved = localStorage.getItem(THEME_KEY);
    const preferred = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    applyTheme(saved || preferred);
    $$('[data-theme-toggle]').forEach((button) => button.addEventListener("click", () => applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark")));
  }

  function initDrawer() {
    const drawer = $('[data-drawer]');
    if (!drawer) return;
    const open = () => { drawer.classList.add("open"); drawer.setAttribute("aria-hidden", "false"); document.body.style.overflow = "hidden"; };
    const close = () => { drawer.classList.remove("open"); drawer.setAttribute("aria-hidden", "true"); document.body.style.overflow = ""; };
    $$('[data-drawer-open]').forEach((button) => button.addEventListener("click", open));
    $$('[data-drawer-close]', drawer).forEach((button) => button.addEventListener("click", close));
    document.addEventListener("keydown", (event) => { if (event.key === "Escape") close(); });
  }

  function initActiveNavigation() {
    const page = document.body.dataset.page;
    if (!page) return;
    $$(`[data-nav="${CSS.escape(page)}"]`).forEach((link) => link.classList.add("active"));
  }

  function initPasswordToggles() {
    $$('[data-password-toggle]').forEach((button) => button.addEventListener("click", () => {
      const input = document.getElementById(button.getAttribute("aria-controls"));
      if (!input) return;
      const reveal = input.type === "password";
      input.type = reveal ? "text" : "password";
      setUseIcon($("use", button), reveal ? "eye-off" : "eye");
    }));
  }

  function initProgress() {
    if (reduceMotion) return;
    $$('.progress span').forEach((bar) => {
      const target = bar.style.width || "0%";
      bar.style.width = "0";
      requestAnimationFrame(() => { bar.style.transition = "width .9s cubic-bezier(.16,.8,.22,1)"; bar.style.width = target; });
    });
  }

  function initAvatarPreview() {
    $$('[data-avatar-editor-v4], [data-avatar-uploader]').forEach((editor) => {
      const input = $('[data-avatar-input-v4], [data-avatar-input]', editor);
      const image = $('[data-avatar-image-v4], [data-avatar-preview]', editor);
      if (!input || !image || input.dataset.bound === "1") return;
      input.dataset.bound = "1";
      const choose = $$('[data-avatar-choose-v4]', editor);
      const clear = $$('[data-avatar-clear-v4], [data-avatar-remove]', editor);
      const filename = $('[data-avatar-filename-v4], [data-avatar-filename]', editor);
      const original = image.getAttribute("src") || "";
      choose.forEach((button) => button.addEventListener("click", (event) => { event.preventDefault(); input.click(); }));
      input.addEventListener("change", () => {
        const file = input.files?.[0];
        if (!file) return;
        if (!file.type.startsWith("image/") || file.size > 5 * 1024 * 1024) {
          input.value = "";
          window.TaskFlowFlash?.create("تصویر باید معتبر و کوچک‌تر از ۵ مگابایت باشد.", "error");
          return;
        }
        const reader = new FileReader();
        reader.onload = (event) => { image.src = event.target.result; image.hidden = false; editor.classList.add("has-image", "has-preview"); if (filename) filename.textContent = file.name; };
        reader.readAsDataURL(file);
      });
      clear.forEach((button) => button.addEventListener("click", (event) => { event.preventDefault(); input.value = ""; image.src = original; editor.classList.remove("has-image", "has-preview"); if (filename) filename.textContent = ""; }));
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initTheme(); initDrawer(); initActiveNavigation(); initPasswordToggles(); initProgress(); initAvatarPreview();
  }, { once: true });
})();
