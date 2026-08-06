(() => {
  "use strict";

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const controllers = new Map();

  const closeFlash = (item) => {
    if (!item || item.dataset.closing === "1") return;
    item.dataset.closing = "1";
    controllers.get(item)?.stop();
    item.classList.add("is-leaving");
    window.setTimeout(() => {
      controllers.delete(item);
      item.remove();
    }, reduceMotion.matches ? 0 : 330);
  };

  const bindFlash = (item) => {
    if (item.dataset.flashBound === "1") return;
    item.dataset.flashBound = "1";

    const closeButton = item.querySelector("[data-flash-close]");
    const progress = item.querySelector("[data-flash-progress]");
    const requestedTimeout = Number(item.dataset.timeout || 6500);
    const timeout = Number.isFinite(requestedTimeout) ? Math.max(0, requestedTimeout) : 6500;
    const pauseReasons = new Set();
    let timer = null;
    let startedAt = 0;
    let remaining = timeout;
    let progressStarted = false;

    const freezeProgress = () => {
      if (!progress || reduceMotion.matches) return;
      const current = getComputedStyle(progress).transform;
      progress.style.transition = "none";
      progress.style.transform = current === "none" ? "scaleX(1)" : current;
    };

    const stop = () => {
      if (timer !== null) window.clearTimeout(timer);
      timer = null;
    };

    const start = () => {
      stop();
      if (pauseReasons.size || item.dataset.closing === "1") return;
      if (remaining <= 0) {
        closeFlash(item);
        return;
      }

      startedAt = performance.now();
      if (progress && !reduceMotion.matches) {
        if (!progressStarted) {
          progress.style.transition = "none";
          progress.style.transform = "scaleX(1)";
          progressStarted = true;
        }
        requestAnimationFrame(() => {
          if (pauseReasons.size || item.dataset.closing === "1") return;
          progress.style.transition = `transform ${remaining}ms linear`;
          progress.style.transform = "scaleX(0)";
        });
      }
      timer = window.setTimeout(() => closeFlash(item), remaining);
    };

    const pause = (reason) => {
      const wasPaused = pauseReasons.size > 0;
      pauseReasons.add(reason);
      if (wasPaused || timer === null) return;
      remaining = Math.max(0, remaining - (performance.now() - startedAt));
      stop();
      freezeProgress();
    };

    const resume = (reason) => {
      if (!pauseReasons.delete(reason)) return;
      if (!pauseReasons.size) start();
    };

    if (document.hidden) pauseReasons.add("document");
    controllers.set(item, { stop, pause, resume });
    closeButton?.addEventListener("click", () => closeFlash(item));
    item.addEventListener("mouseenter", () => pause("pointer"));
    item.addEventListener("mouseleave", () => resume("pointer"));
    item.addEventListener("focusin", () => pause("focus"));
    item.addEventListener("focusout", (event) => {
      if (event.relatedTarget && item.contains(event.relatedTarget)) return;
      resume("focus");
    });
    start();
  };

  const initFlashMessages = (scope = document) => {
    scope.querySelectorAll("[data-flash]").forEach(bindFlash);
  };

  const allowedTypes = new Set(["success", "error", "warning", "info"]);
  window.TaskFlowFlash = {
    create(message, requestedType = "info", timeout = 5000) {
      const type = allowedTypes.has(requestedType) ? requestedType : "info";
      let stack = document.querySelector("[data-flash-stack]");
      if (!stack) {
        stack = document.createElement("div");
        stack.className = "flash-stack";
        stack.dataset.flashStack = "";
        stack.setAttribute("aria-live", "polite");
        stack.setAttribute("aria-atomic", "false");
        document.body.appendChild(stack);
      }

      const icon = type === "success"
        ? "check"
        : (type === "error" || type === "warning" ? "alert" : "info");
      const title = type === "success"
        ? "عملیات موفق"
        : (type === "error" ? "خطا" : (type === "warning" ? "توجه" : "TaskFlow"));
      const item = document.createElement("article");
      item.className = `flash-message flash-message--${type}`;
      item.dataset.flash = "";
      const requestedTimeout = Number(timeout);
      item.dataset.timeout = String(
        Number.isFinite(requestedTimeout) ? Math.max(0, requestedTimeout) : 5000,
      );
      item.setAttribute("role", type === "error" ? "alert" : "status");
      item.innerHTML = `<div class="flash-message__glow"></div><span class="flash-message__icon"><svg class="tf-icon" aria-hidden="true" focusable="false"><use href="#icon-${icon}"></use></svg></span><div class="flash-message__body"><strong>${title}</strong><p></p></div><button class="flash-message__close" type="button" data-flash-close aria-label="بستن پیام"><svg class="tf-icon" aria-hidden="true" focusable="false"><use href="#icon-x"></use></svg></button><span class="flash-message__progress" data-flash-progress></span>`;
      item.querySelector("p").textContent = String(message ?? "");
      stack.appendChild(item);
      bindFlash(item);
    },
    close: closeFlash,
  };

  document.addEventListener("visibilitychange", () => {
    controllers.forEach((controller) => {
      if (document.hidden) {
        controller.pause("document");
      } else {
        controller.resume("document");
      }
    });
  });

  if (document.body) {
    initFlashMessages();
  } else {
    document.addEventListener("DOMContentLoaded", () => initFlashMessages(), { once: true });
  }
})();
