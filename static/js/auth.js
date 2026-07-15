(() => {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const coarsePointer = window.matchMedia("(pointer: coarse)").matches;
  const THEME_KEY = "taskflow-theme";

  function setUseIcon(element, id) {
    if (!element) return;
    element.setAttribute("href", `#icon-${id}`);
    element.setAttributeNS(
      "http://www.w3.org/1999/xlink",
      "href",
      `#icon-${id}`,
    );
  }

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(THEME_KEY, theme);

    $$("[data-theme-use]").forEach((use) => {
      setUseIcon(use, theme === "dark" ? "sun" : "moon");
    });
  }

  function initTheme() {
    const saved = localStorage.getItem(THEME_KEY);
    const preferred = window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";

    applyTheme(saved || preferred);

    $$("[data-theme-toggle]").forEach((button) => {
      button.addEventListener("click", () => {
        applyTheme(
          document.documentElement.dataset.theme === "dark"
            ? "light"
            : "dark",
        );
      });
    });
  }

  function initSpaceScene() {
    const canvas = $("[data-auth-space]");
    if (!canvas || !window.TaskFlowSpaceScene) return;

    window.TaskFlowSpaceScene.mount(canvas, {
      count: window.innerWidth < 720 ? 145 : 310,
      spread: window.innerWidth < 720 ? 7.4 : 11,
      speed: 0.92,
      pointScale: window.innerWidth < 720 ? 18 : 24,
    });
  }

  function initPasswordToggles() {
    $$("[data-password-toggle]").forEach((button) => {
      button.addEventListener("click", () => {
        const input = document.getElementById(
          button.getAttribute("aria-controls"),
        );

        if (!input) return;

        const reveal = input.type === "password";
        input.type = reveal ? "text" : "password";
        button.setAttribute(
          "aria-label",
          reveal ? "پنهان کردن رمز عبور" : "نمایش رمز عبور",
        );
        setUseIcon($("use", button), reveal ? "eye-off" : "eye");
      });
    });
  }

  function initForms() {
    $$("[data-auth-form]").forEach((form) => {
      form.addEventListener("submit", () => {
        const button = $("[data-submit-button]", form);

        if (!button || button.classList.contains("is-loading")) return;

        button.classList.add("is-loading");
        button.disabled = true;
        button.setAttribute("aria-busy", "true");
      });
    });
  }

  function initCardTilt() {
    if (reduceMotion || coarsePointer) return;

    const card = $("[data-tilt-card]");
    if (!card) return;

    let frame = 0;

    card.addEventListener("pointermove", (event) => {
      cancelAnimationFrame(frame);

      frame = requestAnimationFrame(() => {
        const rect = card.getBoundingClientRect();
        const x = (event.clientX - rect.left) / rect.width;
        const y = (event.clientY - rect.top) / rect.height;

        card.style.setProperty("--shine-x", `${x * 100}%`);
        card.style.setProperty("--shine-y", `${y * 100}%`);
        card.style.setProperty("--card-rx", `${(0.5 - y) * 5.5}deg`);
        card.style.setProperty("--card-ry", `${(x - 0.5) * 7}deg`);
      });
    });

    card.addEventListener("pointerleave", () => {
      card.style.setProperty("--card-rx", "0deg");
      card.style.setProperty("--card-ry", "0deg");
    });
  }

  function initDepthScene() {
    if (reduceMotion || coarsePointer) return;

    const elements = $$("[data-depth]");
    const cursorLight = $("[data-auth-cursor-light]");

    let x = 0;
    let y = 0;
    let targetX = 0;
    let targetY = 0;
    let lightX = window.innerWidth / 2;
    let lightY = window.innerHeight / 2;
    let targetLightX = lightX;
    let targetLightY = lightY;
    let raf = 0;

    function render() {
      x += (targetX - x) * 0.055;
      y += (targetY - y) * 0.055;
      lightX += (targetLightX - lightX) * 0.1;
      lightY += (targetLightY - lightY) * 0.1;

      elements.forEach((element) => {
        const depth = Number(element.dataset.depth || 1);
        element.style.setProperty(
          "--depth-x",
          `${x * 18 * depth}px`,
        );
        element.style.setProperty(
          "--depth-y",
          `${y * 13 * depth}px`,
        );
      });

      if (cursorLight) {
        cursorLight.style.transform =
          `translate3d(${lightX}px, ${lightY}px, 0)`;
      }

      raf = requestAnimationFrame(render);
    }

    window.addEventListener(
      "pointermove",
      (event) => {
        targetX = event.clientX / window.innerWidth - 0.5;
        targetY = event.clientY / window.innerHeight - 0.5;
        targetLightX = event.clientX;
        targetLightY = event.clientY;
        cursorLight?.classList.add("is-visible");
      },
      { passive: true },
    );

    document.documentElement.addEventListener("mouseleave", () => {
      cursorLight?.classList.remove("is-visible");
    });

    raf = requestAnimationFrame(render);

    window.addEventListener(
      "pagehide",
      () => cancelAnimationFrame(raf),
      { once: true },
    );
  }

  function initReveal() {
    const elements = $$("[data-reveal-auth], .auth-field, .auth-status > *");

    elements.forEach((element, index) => {
      element.classList.add("auth-reveal");
      element.style.setProperty(
        "--auth-reveal-delay",
        `${Math.min(index, 12) * 65}ms`,
      );
    });

    requestAnimationFrame(() => {
      elements.forEach((element) => element.classList.add("is-visible"));
    });
  }

  function initInputMotion() {
    $$(".auth-input").forEach((input) => {
      const wrapper = input.closest(".auth-input-wrap");

      input.addEventListener("focus", () => {
        wrapper?.classList.add("is-focused");
      });

      input.addEventListener("blur", () => {
        wrapper?.classList.remove("is-focused");
      });

      input.addEventListener("input", () => {
        wrapper?.classList.toggle("has-value", Boolean(input.value));
      });

      wrapper?.classList.toggle("has-value", Boolean(input.value));
    });
  }

  function initMagneticActions() {
    if (reduceMotion || coarsePointer) return;

    $$(".auth-submit, .auth-theme-toggle").forEach((element) => {
      element.addEventListener("pointermove", (event) => {
        const rect = element.getBoundingClientRect();
        const x = event.clientX - rect.left - rect.width / 2;
        const y = event.clientY - rect.top - rect.height / 2;

        element.style.setProperty("--magnetic-x", `${x * 0.09}px`);
        element.style.setProperty("--magnetic-y", `${y * 0.09}px`);
      });

      element.addEventListener("pointerleave", () => {
        element.style.removeProperty("--magnetic-x");
        element.style.removeProperty("--magnetic-y");
      });
    });
  }

  document.addEventListener(
    "DOMContentLoaded",
    () => {
      initTheme();
      initSpaceScene();
      initPasswordToggles();
      initForms();
      initCardTilt();
      initDepthScene();
      initReveal();
      initInputMotion();
      initMagneticActions();
    },
    { once: true },
  );
})();
