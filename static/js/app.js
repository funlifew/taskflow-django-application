/* TaskFlow UI V2 — Vanilla JS, no API dependency */

const qs = (s, root = document) => root.querySelector(s);
const qsa = (s, root = document) => [...root.querySelectorAll(s)];

const THEME_KEY = "taskflow-ui-v2-theme";

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem(THEME_KEY, theme);
  qsa("[data-theme-label]").forEach(el => el.textContent = theme === "dark" ? "روشن" : "تاریک");
  qsa("[data-theme-icon]").forEach(el => el.textContent = theme === "dark" ? "☀️" : "🌙");
}

function initTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  const preferred = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  setTheme(saved || preferred);

  qsa("[data-theme-toggle]").forEach(btn => {
    btn.addEventListener("click", () => {
      const current = document.documentElement.dataset.theme || "light";
      setTheme(current === "dark" ? "light" : "dark");
      toast(`تم ${current === "dark" ? "روشن" : "تاریک"} فعال شد.`);
    });
  });
}

function initDrawer() {
  const drawer = qs("[data-drawer]");
  if (!drawer) return;

  qsa("[data-drawer-open]").forEach(btn => btn.addEventListener("click", () => drawer.classList.add("open")));
  qsa("[data-drawer-close]").forEach(btn => btn.addEventListener("click", () => drawer.classList.remove("open")));
  qs(".drawer-backdrop", drawer)?.addEventListener("click", () => drawer.classList.remove("open"));
}

function initActiveNav() {
  const page = document.body.dataset.page;
  if (!page) return;
  qsa(`[data-nav="${page}"]`).forEach(link => link.classList.add("active"));
}

function toast(message) {
  let wrap = qs(".toast-wrap");
  if (!wrap) {
    wrap = document.createElement("div");
    wrap.className = "toast-wrap";
    document.body.appendChild(wrap);
  }

  const item = document.createElement("div");
  item.className = "toast";
  item.innerHTML = `<strong>TaskFlow</strong><div class="muted" style="margin-top:4px;line-height:1.7">${message}</div>`;
  wrap.appendChild(item);

  setTimeout(() => {
    item.style.opacity = "0";
    item.style.transform = "translateY(-8px)";
    setTimeout(() => item.remove(), 220);
  }, 2600);
}

function initFakeButtons() {
  qsa("[data-toast]").forEach(btn => {
    btn.addEventListener("click", () => toast(btn.dataset.toast));
  });
}

function initProgressAnimation() {
  qsa(".progress span").forEach(span => {
    const width = span.style.width || "0%";
    span.style.width = "0%";
    requestAnimationFrame(() => {
      span.style.transition = "width .9s cubic-bezier(.22, 1, .36, 1)";
      span.style.width = width;
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initDrawer();
  initActiveNav();
  initFakeButtons();
  initProgressAnimation();
});


/* ---------- Avatar upload preview ---------- */

function initAvatarUpload() {
  qsa("[data-avatar-uploader]").forEach((uploader) => {
    const input = qs("[data-avatar-input]", uploader);
    const img = qs("[data-avatar-preview]", uploader);
    const initials = qs("[data-avatar-initials]", uploader);
    const metaTargetSelector = uploader.dataset.avatarMetaTarget;
    const meta = metaTargetSelector ? qs(metaTargetSelector) : null;
    const remove = meta ? qs("[data-avatar-remove]", meta) : null;
    const metaName = meta ? qs("[data-avatar-filename]", meta) : null;

    if (!input || !img) return;

    const defaultSrc = img.getAttribute("src") || "";
    const defaultAlt = img.getAttribute("alt") || "Avatar";

    input.addEventListener("change", () => {
      const file = input.files && input.files[0];
      if (!file) return;

      if (!file.type.startsWith("image/")) {
        toast("لطفاً فقط فایل تصویر انتخاب کن.");
        input.value = "";
        return;
      }

      if (file.size > 2 * 1024 * 1024) {
        toast("حجم تصویر بهتر است کمتر از ۲ مگابایت باشد.");
      }

      const reader = new FileReader();
      reader.onload = (event) => {
        img.src = event.target.result;
        img.alt = file.name;
        img.hidden = false;
        if (initials) initials.hidden = true;
        uploader.classList.add("has-preview");

        if (meta) {
          meta.classList.add("is-visible");
          if (metaName) metaName.textContent = file.name;
        }

        toast("پیش‌نمایش آواتار آماده شد.");
      };

      reader.readAsDataURL(file);
    });

    if (remove) {
      remove.addEventListener("click", (event) => {
        event.preventDefault();
        input.value = "";
        img.src = defaultSrc;
        img.alt = defaultAlt;
        uploader.classList.remove("has-preview");

        if (!defaultSrc && initials) {
          img.hidden = true;
          initials.hidden = false;
        }

        if (meta) {
          meta.classList.remove("is-visible");
          if (metaName) metaName.textContent = "";
        }

        toast("پیش‌نمایش آواتار حذف شد.");
      });
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initAvatarUpload();
});


/* ---------- V4 Fixed Avatar Editor ---------- */

function initAvatarEditorsV4() {
  qsa("[data-avatar-editor-v4]").forEach((editor) => {
    if (editor.dataset.avatarBound === "1") return;
    editor.dataset.avatarBound = "1";

    const input = qs("[data-avatar-input-v4]", editor);
    const image = qs("[data-avatar-image-v4]", editor);
    const chooseButtons = qsa("[data-avatar-choose-v4]", editor);
    const clearButtons = qsa("[data-avatar-clear-v4]", editor);
    const filename = qs("[data-avatar-filename-v4]", editor);
    const meta = qs("[data-avatar-meta-v4]", editor);
    const error = qs("[data-avatar-error-v4]", editor);

    if (!input || !image) return;

    function showError(message) {
      if (error) {
        error.textContent = message;
        error.classList.add("is-visible");
      }
      toast(message);
    }

    function clearError() {
      if (error) {
        error.textContent = "";
        error.classList.remove("is-visible");
      }
    }

    function openPicker(event) {
      event.preventDefault();
      input.click();
    }

    chooseButtons.forEach((btn) => btn.addEventListener("click", openPicker));

    input.addEventListener("change", () => {
      clearError();

      const file = input.files && input.files[0];
      if (!file) return;

      if (!file.type || !file.type.startsWith("image/")) {
        input.value = "";
        showError("فقط فایل تصویر انتخاب کن.");
        return;
      }

      const maxSize = 2 * 1024 * 1024;
      if (file.size > maxSize) {
        input.value = "";
        showError("حجم تصویر باید کمتر از ۲ مگابایت باشد.");
        return;
      }

      const reader = new FileReader();
      reader.onload = (event) => {
        image.src = event.target.result;
        image.alt = file.name;
        editor.classList.add("has-image");

        if (filename) filename.textContent = file.name;
        if (meta) meta.classList.add("is-visible");

        toast("پیش‌نمایش آواتار آماده شد.");
      };
      reader.readAsDataURL(file);
    });

    clearButtons.forEach((btn) => {
      btn.addEventListener("click", (event) => {
        event.preventDefault();
        input.value = "";
        image.removeAttribute("src");
        image.alt = "";
        editor.classList.remove("has-image");
        if (filename) filename.textContent = "";
        if (meta) meta.classList.remove("is-visible");
        clearError();
        toast("پیش‌نمایش حذف شد.");
      });
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initAvatarEditorsV4();
});
