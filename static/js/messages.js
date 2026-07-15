(() => {
  "use strict";
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function closeFlash(item) {
    if (!item || item.dataset.closing === "1") return;
    item.dataset.closing = "1";
    item.classList.add("is-leaving");
    const delay = reduceMotion ? 0 : 320;
    window.setTimeout(() => item.remove(), delay);
  }

  function initFlashMessages() {
    document.querySelectorAll("[data-flash]").forEach((item) => {
      if (item.dataset.flashBound === "1") return;
      item.dataset.flashBound = "1";
      const closeButton = item.querySelector("[data-flash-close]");
      const progress = item.querySelector("[data-flash-progress]");
      const timeout = Number(item.dataset.timeout || 6500);
      let timer = null;
      let startedAt = performance.now();
      let remaining = timeout;

      const start = () => {
        if (reduceMotion) return;
        startedAt = performance.now();
        if (progress) {
          progress.style.transition = "none";
          progress.style.transform = "scaleX(1)";
          requestAnimationFrame(() => {
            progress.style.transition = `transform ${remaining}ms linear`;
            progress.style.transform = "scaleX(0)";
          });
        }
        timer = window.setTimeout(() => closeFlash(item), remaining);
      };

      const pause = () => {
        if (timer) window.clearTimeout(timer);
        remaining -= performance.now() - startedAt;
        if (progress) {
          const current = getComputedStyle(progress).transform;
          progress.style.transition = "none";
          progress.style.transform = current === "none" ? "scaleX(1)" : current;
        }
      };

      closeButton?.addEventListener("click", () => closeFlash(item));
      item.addEventListener("mouseenter", pause);
      item.addEventListener("mouseleave", start);
      item.addEventListener("focusin", pause);
      item.addEventListener("focusout", start);
      start();
    });
  }

  window.TaskFlowFlash = {
    create(message, type = "info", timeout = 5000) {
      let stack = document.querySelector("[data-flash-stack]");
      if (!stack) {
        stack = document.createElement("div");
        stack.className = "flash-stack";
        stack.dataset.flashStack = "";
        stack.setAttribute("aria-live", "polite");
        document.body.appendChild(stack);
      }
      const icon = type === "success" ? "check" : (type === "error" || type === "warning") ? "alert" : "info";
      const title = type === "success" ? "عملیات موفق" : type === "error" ? "خطا" : type === "warning" ? "توجه" : "TaskFlow";
      const item = document.createElement("article");
      item.className = `flash-message flash-message--${type}`;
      item.dataset.flash = "";
      item.dataset.timeout = String(timeout);
      item.innerHTML = `<div class="flash-message__glow"></div><span class="flash-message__icon"><svg class="tf-icon"><use href="#icon-${icon}"></use></svg></span><div class="flash-message__body"><strong>${title}</strong><p></p></div><button class="flash-message__close" type="button" data-flash-close aria-label="بستن پیام"><svg class="tf-icon"><use href="#icon-x"></use></svg></button><span class="flash-message__progress" data-flash-progress></span>`;
      item.querySelector("p").textContent = message;
      stack.appendChild(item);
      initFlashMessages();
    }
  };

  document.addEventListener("DOMContentLoaded", initFlashMessages, { once: true });
})();
