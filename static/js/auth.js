(() => {
  "use strict";

  const TaskFlow = window.TaskFlow = window.TaskFlow || {};
  const root = document.documentElement;
  const $ = (selector, scope = document) => scope.querySelector(selector);
  const $$ = (selector, scope = document) => Array.from(scope.querySelectorAll(selector));
  const THEME_KEY = "taskflow-theme";
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const PRODUCT_COPY_PATTERN = /\b(Workspaces?|Tasks?|Boards?|Columns?)\b/gi;
  const PRODUCT_COPY = Object.freeze({
    task: "کار",
    tasks: "کارها",
    workspace: "فضای کاری",
    workspaces: "فضاهای کاری",
    board: "برد",
    boards: "بردها",
    column: "ستون",
    columns: "ستون‌ها",
  });

  const localizeProductText = (value) => String(value).replace(
    PRODUCT_COPY_PATTERN,
    (term) => PRODUCT_COPY[term.toLowerCase()] || term,
  );

  const initProductCopyLocalization = () => {
    const scopes = $$([
      "[data-localize-product-copy]",
      ".error-text",
      ".form-errors",
      ".help",
      ".field-help",
    ].join(","));
    const visited = new Set();

    scopes.forEach((scope) => {
      const walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT);
      let node = walker.nextNode();
      while (node) {
        if (!visited.has(node) && !node.parentElement?.closest("script, style, code, pre")) {
          visited.add(node);
          const localized = localizeProductText(node.nodeValue || "");
          if (localized !== node.nodeValue) node.nodeValue = localized;
        }
        node = walker.nextNode();
      }
    });

    $$("form input, form textarea, form select, form button").forEach((control) => {
      ["placeholder", "title", "aria-label"].forEach((attribute) => {
        if (!control.hasAttribute(attribute)) return;
        const current = control.getAttribute(attribute) || "";
        const localized = localizeProductText(current);
        if (localized !== current) control.setAttribute(attribute, localized);
      });
    });
  };

  const initDecorativeIcons = () => {
    $$("svg.tf-icon").forEach((icon) => {
      if (
        icon.getAttribute("role") === "img"
        || icon.hasAttribute("aria-label")
        || icon.hasAttribute("aria-labelledby")
      ) return;
      icon.setAttribute("aria-hidden", "true");
      icon.setAttribute("focusable", "false");
    });
  };

  const setUseIcon = (element, iconName) => {
    if (!element) return;
    const target = `#icon-${iconName}`;
    element.setAttribute("href", target);
    element.setAttributeNS(
      "http://www.w3.org/1999/xlink",
      "href",
      target,
    );
  };

  const createThemeController = () => {
    if (TaskFlow.theme?.taskflowThemeController) return TaskFlow.theme;

    const systemTheme = window.matchMedia("(prefers-color-scheme: dark)");
    let currentTheme = root.dataset.theme === "light" ? "light" : "dark";
    let explicitTheme = null;

    try {
      const stored = localStorage.getItem(THEME_KEY);
      explicitTheme = stored === "dark" || stored === "light" ? stored : null;
    } catch {
      explicitTheme = null;
    }

    const syncControls = () => {
      $$('[data-theme-use]').forEach((use) => {
        setUseIcon(use, currentTheme === "dark" ? "sun" : "moon");
      });
      $$('[data-theme-toggle]').forEach((button) => {
        button.dataset.themeState = currentTheme;
        button.setAttribute("aria-pressed", currentTheme === "dark" ? "true" : "false");
      });
      const themeColor = $('meta[name="theme-color"]');
      if (themeColor) {
        themeColor.content = currentTheme === "dark" ? "#070916" : "#eef2ff";
      }
    };

    const apply = (theme, { persist = false, source = "api", force = false } = {}) => {
      const nextTheme = theme === "dark" ? "dark" : "light";
      const changed = nextTheme !== currentTheme;
      currentTheme = nextTheme;
      root.dataset.theme = nextTheme;
      if (persist) {
        explicitTheme = nextTheme;
        try {
          localStorage.setItem(THEME_KEY, nextTheme);
        } catch {
          // The selected theme still applies for this page.
        }
      }
      syncControls();
      if (changed || force) {
        document.dispatchEvent(new CustomEvent("taskflow:themechange", {
          detail: { theme: nextTheme, source },
        }));
      }
      return nextTheme;
    };

    const controller = {
      taskflowThemeController: true,
      get value() {
        return currentTheme;
      },
      apply,
      syncControls,
      toggle() {
        return apply(currentTheme === "dark" ? "light" : "dark", {
          persist: true,
          source: "toggle",
        });
      },
    };

    TaskFlow.theme = controller;
    apply(explicitTheme || (systemTheme.matches ? "dark" : "light"), {
      source: explicitTheme ? "storage" : "system",
      force: true,
    });

    const onSystemChange = (event) => {
      if (!explicitTheme) {
        apply(event.matches ? "dark" : "light", { source: "system" });
      }
    };
    if (typeof systemTheme.addEventListener === "function") {
      systemTheme.addEventListener("change", onSystemChange);
    } else {
      systemTheme.addListener(onSystemChange);
    }
    window.addEventListener("storage", (event) => {
      if (event.key !== THEME_KEY) return;
      explicitTheme = event.newValue === "dark" || event.newValue === "light"
        ? event.newValue
        : null;
      apply(explicitTheme || (systemTheme.matches ? "dark" : "light"), {
        source: "storage",
      });
    });
    return controller;
  };

  const initTheme = () => {
    const theme = createThemeController();
    $$('[data-theme-toggle]').forEach((button) => {
      if (button.dataset.themeBound === "1") return;
      button.dataset.themeBound = "1";
      button.addEventListener("click", () => theme.toggle());
    });
    theme.syncControls();
  };

  const initPasswordToggles = () => {
    $$('[data-password-toggle]').forEach((button) => {
      if (button.dataset.passwordBound === "1") return;
      const input = document.getElementById(button.getAttribute("aria-controls"));
      if (!input) return;
      button.dataset.passwordBound = "1";
      const sync = () => {
        const revealed = input.type !== "password";
        button.setAttribute(
          "aria-label",
          revealed ? "پنهان کردن رمز عبور" : "نمایش رمز عبور",
        );
        button.setAttribute("aria-pressed", revealed ? "true" : "false");
        setUseIcon($("use", button), revealed ? "eye-off" : "eye");
      };
      button.addEventListener("click", () => {
        input.type = input.type === "password" ? "text" : "password";
        sync();
      });
      sync();
    });
  };

  const setFormIdle = (form) => {
    delete form.dataset.submitting;
    form.classList.remove("is-submitting");
    form.removeAttribute("aria-busy");
    $$('[data-submit-button]', form).forEach((button) => {
      button.disabled = false;
      button.classList.remove("is-loading");
      button.removeAttribute("aria-busy");
    });
  };

  const initForms = () => {
    $$('[data-auth-form]').forEach((form) => {
      if (form.dataset.submitBound === "1") return;
      form.dataset.submitBound = "1";
      form.addEventListener("submit", (event) => {
        if (form.dataset.submitting === "true") {
          event.preventDefault();
          return;
        }
        form.dataset.submitting = "true";
        form.classList.add("is-submitting");
        form.setAttribute("aria-busy", "true");
        const button = event.submitter || $('[data-submit-button]', form);
        if (button) {
          button.classList.add("is-loading");
          button.setAttribute("aria-busy", "true");
          button.disabled = true;
        }
      });
    });

    window.addEventListener("pageshow", (event) => {
      if (!event.persisted) return;
      $$('[data-auth-form]').forEach(setFormIdle);
    });
  };

  const initReveal = () => {
    const elements = $$('[data-reveal-auth], .auth-field, .auth-status > *');
    elements.forEach((element, index) => {
      element.classList.add("auth-reveal");
      element.style.setProperty(
        "--auth-reveal-delay",
        reduceMotion.matches ? "0ms" : `${Math.min(index, 8) * 45}ms`,
      );
    });

    const reveal = () => elements.forEach((element) => element.classList.add("is-visible"));
    if (reduceMotion.matches) {
      reveal();
    } else {
      requestAnimationFrame(reveal);
    }
  };

  const initInputState = () => {
    $$('.auth-input').forEach((input) => {
      const wrapper = input.closest('.auth-input-wrap');
      if (!wrapper || input.dataset.inputStateBound === "1") return;
      input.dataset.inputStateBound = "1";
      const sync = () => wrapper.classList.toggle("has-value", Boolean(input.value));
      input.addEventListener("focus", () => wrapper.classList.add("is-focused"));
      input.addEventListener("blur", () => wrapper.classList.remove("is-focused"));
      input.addEventListener("input", sync);
      sync();
    });
  };

  const init = () => {
    if (document.body?.dataset.taskflowAuthBound === "1") return;
    if (document.body) document.body.dataset.taskflowAuthBound = "1";
    initProductCopyLocalization();
    initDecorativeIcons();
    initTheme();
    initPasswordToggles();
    initForms();
    initReveal();
    initInputState();
  };

  TaskFlow.auth = { init };
  if (document.body) {
    init();
  } else {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  }
})();
