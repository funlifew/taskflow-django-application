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
    element.setAttributeNS("http://www.w3.org/1999/xlink", "href", `#icon-${id}`);
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
    const canvas = $("[data-app-space]");

    if (!canvas || !window.TaskFlowSpaceScene) return;

    window.TaskFlowSpaceScene.mount(canvas, {
      count: window.innerWidth < 720 ? 115 : 245,
      spread: window.innerWidth < 720 ? 7 : 10,
      speed: 0.56,
      pointScale: window.innerWidth < 720 ? 15 : 19,
    });
  }

  function initDrawer() {
    const drawer = $("[data-drawer]");
    if (!drawer) return;

    let previousFocus = null;

    const focusableSelector = [
      "a[href]",
      "button:not([disabled])",
      "input:not([disabled])",
      "select:not([disabled])",
      "textarea:not([disabled])",
      '[tabindex]:not([tabindex="-1"])',
    ].join(",");

    function open() {
      previousFocus = document.activeElement;
      drawer.classList.add("open");
      drawer.setAttribute("aria-hidden", "false");
      document.body.classList.add("drawer-open");

      const first = $(focusableSelector, drawer);
      window.setTimeout(() => first?.focus(), 80);
    }

    function close() {
      drawer.classList.remove("open");
      drawer.setAttribute("aria-hidden", "true");
      document.body.classList.remove("drawer-open");
      previousFocus?.focus?.();
    }

    $$("[data-drawer-open]").forEach((button) => {
      button.addEventListener("click", open);
    });

    $$("[data-drawer-close]", drawer).forEach((button) => {
      button.addEventListener("click", close);
    });

    $$("a[href]", drawer).forEach((link) => {
      link.addEventListener("click", close);
    });

    document.addEventListener("keydown", (event) => {
      if (!drawer.classList.contains("open")) return;

      if (event.key === "Escape") {
        close();
        return;
      }

      if (event.key !== "Tab") return;

      const focusable = $$(focusableSelector, drawer).filter(
        (element) => element.offsetParent !== null,
      );

      if (!focusable.length) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    });
  }

  function initActiveNavigation() {
    const page = document.body.dataset.page;
    if (!page) return;

    $$("[data-nav]").forEach((item) => {
      const active = item.dataset.nav === page;
      item.classList.toggle("active", active);

      if (active && item.matches("a, button")) {
        item.setAttribute("aria-current", "page");
      }
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

  function initProgress() {
    if (reduceMotion) return;

    $$(".progress span").forEach((bar) => {
      const target = bar.style.width || "0%";
      bar.style.width = "0";

      requestAnimationFrame(() => {
        bar.style.transition =
          "width 1.15s cubic-bezier(.16,.8,.22,1)";
        bar.style.width = target;
      });
    });
  }

  function initReveal() {
    const selector = [
      "[data-reveal]",
      ".workspace-card",
      ".workspace-summary__item",
      ".stat-card",
      ".dashboard-workspace-item",
      ".roadmap-step",
    ].join(",");

    const elements = $$(selector);

    elements.forEach((element, index) => {
      element.classList.add("reveal-item");
      element.style.setProperty(
        "--reveal-delay",
        `${Math.min(index % 8, 7) * 55}ms`,
      );
    });

    if (reduceMotion || !("IntersectionObserver" in window)) {
      elements.forEach((element) => element.classList.add("is-revealed"));
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-revealed");
          observer.unobserve(entry.target);
        });
      },
      {
        threshold: 0.09,
        rootMargin: "0px 0px -5% 0px",
      },
    );

    elements.forEach((element) => observer.observe(element));
  }

  function initPointerGlow() {
    if (reduceMotion || coarsePointer) return;

    const glow = $("[data-pointer-glow]");
    if (!glow) return;

    let x = window.innerWidth / 2;
    let y = window.innerHeight / 2;
    let targetX = x;
    let targetY = y;
    let raf = 0;

    function render() {
      x += (targetX - x) * 0.1;
      y += (targetY - y) * 0.1;
      glow.style.transform = `translate3d(${x}px, ${y}px, 0)`;
      raf = requestAnimationFrame(render);
    }

    window.addEventListener(
      "pointermove",
      (event) => {
        targetX = event.clientX;
        targetY = event.clientY;
        glow.classList.add("is-visible");
      },
      { passive: true },
    );

    document.documentElement.addEventListener("mouseleave", () => {
      glow.classList.remove("is-visible");
    });

    raf = requestAnimationFrame(render);

    window.addEventListener(
      "pagehide",
      () => cancelAnimationFrame(raf),
      { once: true },
    );
  }

  function initTiltCards() {
    if (reduceMotion || coarsePointer) return;

    $$("[data-tilt]").forEach((element) => {
      let raf = 0;

      element.addEventListener("pointermove", (event) => {
        cancelAnimationFrame(raf);

        raf = requestAnimationFrame(() => {
          const rect = element.getBoundingClientRect();
          const x = (event.clientX - rect.left) / rect.width;
          const y = (event.clientY - rect.top) / rect.height;
          const rotateY = (x - 0.5) * 5;
          const rotateX = (0.5 - y) * 4;

          element.style.setProperty("--tilt-x", `${x * 100}%`);
          element.style.setProperty("--tilt-y", `${y * 100}%`);
          element.style.transform =
            `perspective(900px) rotateX(${rotateX}deg) ` +
            `rotateY(${rotateY}deg) translateY(-3px)`;
        });
      });

      element.addEventListener("pointerleave", () => {
        element.style.transform = "";
      });
    });
  }

  function initMagneticButtons() {
    if (reduceMotion || coarsePointer) return;

    $$(".btn-primary, .icon-btn").forEach((button) => {
      button.addEventListener("pointermove", (event) => {
        const rect = button.getBoundingClientRect();
        const x = event.clientX - rect.left - rect.width / 2;
        const y = event.clientY - rect.top - rect.height / 2;

        button.style.setProperty("--magnetic-x", `${x * 0.08}px`);
        button.style.setProperty("--magnetic-y", `${y * 0.08}px`);
      });

      button.addEventListener("pointerleave", () => {
        button.style.removeProperty("--magnetic-x");
        button.style.removeProperty("--magnetic-y");
      });
    });
  }

  function initParallaxScene() {
    if (reduceMotion || coarsePointer) return;

    const orbits = $$(
      ".app-orbit, .app-wire-cube, [data-dashboard-orbit]",
    );

    window.addEventListener(
      "pointermove",
      (event) => {
        const x = event.clientX / window.innerWidth - 0.5;
        const y = event.clientY / window.innerHeight - 0.5;

        orbits.forEach((element, index) => {
          const depth = (index + 1) * 5;
          element.style.setProperty("--parallax-x", `${x * depth}px`);
          element.style.setProperty("--parallax-y", `${y * depth}px`);
        });
      },
      { passive: true },
    );
  }

  function initAvatarPreview() {
    $$("[data-avatar-editor-v4], [data-avatar-uploader]").forEach(
      (editor) => {
        const input = $(
          "[data-avatar-input-v4], [data-avatar-input]",
          editor,
        );
        const image = $(
          "[data-avatar-image-v4], [data-avatar-preview]",
          editor,
        );

        if (!input || !image || input.dataset.bound === "1") return;
        input.dataset.bound = "1";

        const choose = $$("[data-avatar-choose-v4]", editor);
        const clear = $$(
          "[data-avatar-clear-v4], [data-avatar-remove]",
          editor,
        );
        const filename = $(
          "[data-avatar-filename-v4], [data-avatar-filename]",
          editor,
        );
        const original = image.getAttribute("src") || "";

        choose.forEach((button) => {
          button.addEventListener("click", (event) => {
            event.preventDefault();
            input.click();
          });
        });

        input.addEventListener("change", () => {
          const file = input.files?.[0];
          if (!file) return;

          if (
            !file.type.startsWith("image/") ||
            file.size > 5 * 1024 * 1024
          ) {
            input.value = "";
            window.TaskFlowFlash?.create(
              "تصویر باید معتبر و کوچک‌تر از ۵ مگابایت باشد.",
              "error",
            );
            return;
          }

          const reader = new FileReader();
          reader.onload = (event) => {
            image.src = event.target.result;
            image.hidden = false;
            editor.classList.add("has-image", "has-preview");
            if (filename) filename.textContent = file.name;
          };
          reader.readAsDataURL(file);
        });

        clear.forEach((button) => {
          button.addEventListener("click", (event) => {
            event.preventDefault();
            input.value = "";
            image.src = original;
            editor.classList.remove("has-image", "has-preview");
            if (filename) filename.textContent = "";
          });
        });
      },
    );
  }

  document.addEventListener(
    "DOMContentLoaded",
    () => {
      initTheme();
      initSpaceScene();
      initDrawer();
      initActiveNavigation();
      initPasswordToggles();
      initProgress();
      initReveal();
      initPointerGlow();
      initTiltCards();
      initMagneticButtons();
      initParallaxScene();
      initAvatarPreview();
    },
    { once: true },
  );
})();
