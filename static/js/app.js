(() => {
  "use strict";

  const root = document.documentElement;
  const TaskFlow = window.TaskFlow = window.TaskFlow || {};
  const $ = (selector, scope = document) => scope.querySelector(selector);
  const $$ = (selector, scope = document) => Array.from(scope.querySelectorAll(selector));
  const THEME_KEY = "taskflow-theme";
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

  const emit = (name, detail = {}) => {
    document.dispatchEvent(new CustomEvent(name, { detail }));
  };

  const addMediaListener = (query, listener) => {
    if (typeof query.addEventListener === "function") {
      query.addEventListener("change", listener);
    } else {
      query.addListener(listener);
    }
  };

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

  const readStoredTheme = () => {
    try {
      const value = localStorage.getItem(THEME_KEY);
      return value === "dark" || value === "light" ? value : null;
    } catch {
      return null;
    }
  };

  const writeStoredTheme = (theme) => {
    try {
      localStorage.setItem(THEME_KEY, theme);
      return true;
    } catch {
      return false;
    }
  };

  const createThemeController = () => {
    if (TaskFlow.theme?.taskflowThemeController) return TaskFlow.theme;

    const systemTheme = window.matchMedia("(prefers-color-scheme: dark)");
    let explicitTheme = readStoredTheme();
    let currentTheme = root.dataset.theme === "dark" ? "dark" : "light";

    const syncControls = () => {
      $$('[data-theme-use]').forEach((use) => {
        setUseIcon(use, currentTheme === "dark" ? "sun" : "moon");
      });

      $$('[data-theme-icon]').forEach((icon) => {
        icon.textContent = currentTheme === "dark" ? "☀️" : "🌙";
      });

      $$('[data-theme-toggle]').forEach((button) => {
        button.dataset.themeState = currentTheme;
        button.setAttribute("aria-pressed", currentTheme === "dark" ? "true" : "false");
      });

      const themeColor = $('meta[name="theme-color"]');
      if (themeColor) {
        themeColor.content = currentTheme === "dark" ? "#0b1020" : "#f3f5ff";
      }
    };

    const apply = (theme, { persist = false, source = "api", force = false } = {}) => {
      const nextTheme = theme === "dark" ? "dark" : "light";
      const changed = nextTheme !== currentTheme;
      currentTheme = nextTheme;
      root.dataset.theme = nextTheme;

      if (persist) {
        explicitTheme = nextTheme;
        writeStoredTheme(nextTheme);
      }

      syncControls();
      if (changed || force) {
        emit("taskflow:themechange", { theme: nextTheme, source });
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

    addMediaListener(systemTheme, (event) => {
      if (!explicitTheme) {
        apply(event.matches ? "dark" : "light", { source: "system" });
      }
    });

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

  const createMotionQuality = () => {
    if (TaskFlow.motionQuality?.taskflowMotionQuality) {
      return TaskFlow.motionQuality;
    }

    const reduceQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const coarseQuery = window.matchMedia("(pointer: coarse)");
    const compactQuery = window.matchMedia("(max-width: 720px)");
    const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    let quality = "full";

    const resolve = () => {
      if (reduceQuery.matches) return "static";
      if (
        connection?.saveData
        || coarseQuery.matches
        || compactQuery.matches
        || (window.devicePixelRatio || 1) > 2
        || root.dataset.webgl === "fallback"
        || !("WebGLRenderingContext" in window || "WebGL2RenderingContext" in window)
        || (navigator.deviceMemory && navigator.deviceMemory <= 4)
        || (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 4)
      ) {
        return "reduced";
      }
      return "full";
    };

    const refresh = ({ force = false } = {}) => {
      const nextQuality = resolve();
      const changed = nextQuality !== quality;
      quality = nextQuality;
      root.dataset.motionQuality = nextQuality;
      if (changed || force) {
        emit("taskflow:motionchange", { quality: nextQuality });
      }
      return quality;
    };

    const controller = {
      taskflowMotionQuality: true,
      get value() {
        return quality;
      },
      get isStatic() {
        return quality === "static";
      },
      get isReduced() {
        return quality !== "full";
      },
      refresh,
    };

    TaskFlow.motionQuality = controller;
    [reduceQuery, coarseQuery, compactQuery].forEach((query) => {
      addMediaListener(query, () => refresh());
    });
    connection?.addEventListener?.("change", () => refresh());
    let resizeFrame = 0;
    window.addEventListener("resize", () => {
      if (resizeFrame) return;
      resizeFrame = requestAnimationFrame(() => {
        resizeFrame = 0;
        refresh();
      });
    }, { passive: true });
    refresh({ force: true });
    return controller;
  };

  const theme = createThemeController();
  const motionQuality = createMotionQuality();

  const initThemeToggles = () => {
    $$('[data-theme-toggle]').forEach((button) => {
      if (button.dataset.themeBound === "1") return;
      button.dataset.themeBound = "1";
      button.addEventListener("click", () => theme.toggle());
    });
    theme.syncControls();
  };

  const initDrawer = () => {
    const drawer = $('[data-drawer]');
    if (!drawer || drawer.dataset.drawerBound === "1") return;

    const panel = $('[data-drawer-panel]', drawer);
    if (!panel) return;
    drawer.dataset.drawerBound = "1";

    const appShell = $('[data-app-shell]');
    const openButtons = $$('[data-drawer-open]');
    const closeButtons = $$('[data-drawer-close]', drawer);
    const initialFocus = $('[data-drawer-initial-focus]', panel);
    const focusableSelector = [
      "a[href]",
      "button:not([disabled])",
      "input:not([disabled])",
      "select:not([disabled])",
      "textarea:not([disabled])",
      '[tabindex]:not([tabindex="-1"])',
    ].join(",");

    let isOpen = false;
    let previousFocus = null;
    let scrollPosition = { x: 0, y: 0 };
    let shellState = null;
    let bodyState = null;
    let visualToken = 0;
    let closeFallbackTimer = 0;

    const safeFocus = (element) => {
      if (!element || typeof element.focus !== "function") return false;
      try {
        element.focus({ preventScroll: true });
      } catch {
        element.focus();
      }
      return document.activeElement === element;
    };

    const isFocusable = (element) => {
      if (!(element instanceof HTMLElement) || !element.isConnected) return false;
      if (element.closest('[hidden], [inert], [aria-hidden="true"]')) return false;
      const style = window.getComputedStyle(element);
      return style.display !== "none"
        && style.visibility !== "hidden"
        && element.getClientRects().length > 0;
    };

    const getFocusableElements = () => (
      $$(focusableSelector, panel).filter(isFocusable)
    );

    const setExpanded = (expanded) => {
      openButtons.forEach((button) => {
        button.setAttribute("aria-expanded", expanded ? "true" : "false");
      });
    };

    const lockPageScroll = () => {
      if (bodyState) return;
      scrollPosition = {
        x: window.scrollX || window.pageXOffset || 0,
        y: window.scrollY || window.pageYOffset || 0,
      };
      bodyState = {
        position: document.body.style.position,
        top: document.body.style.top,
        right: document.body.style.right,
        left: document.body.style.left,
        width: document.body.style.width,
        overflow: document.body.style.overflow,
      };

      root.classList.add("drawer-open");
      document.body.classList.add("drawer-open");
      Object.assign(document.body.style, {
        position: "fixed",
        top: `-${scrollPosition.y}px`,
        right: "0",
        left: "0",
        width: "100%",
        overflow: "hidden",
      });
    };

    const unlockPageScroll = ({ restorePosition = true } = {}) => {
      root.classList.remove("drawer-open");
      document.body.classList.remove("drawer-open");
      if (bodyState) Object.assign(document.body.style, bodyState);
      if (restorePosition) {
        window.scrollTo(scrollPosition.x, scrollPosition.y);
      }
      bodyState = null;
    };

    const isolateAppShell = () => {
      if (!appShell) return;
      shellState = {
        hadInert: appShell.hasAttribute("inert"),
        ariaHidden: appShell.getAttribute("aria-hidden"),
      };
      appShell.setAttribute("inert", "");
      appShell.setAttribute("aria-hidden", "true");
    };

    const restoreAppShell = () => {
      if (!appShell || !shellState) return;
      if (!shellState.hadInert) appShell.removeAttribute("inert");
      if (shellState.ariaHidden === null) {
        appShell.removeAttribute("aria-hidden");
      } else {
        appShell.setAttribute("aria-hidden", shellState.ariaHidden);
      }
      shellState = null;
    };

    const dispatchDrawerChange = (open, opener = null, complete = null) => {
      emit("taskflow:drawerchange", {
        open,
        drawer,
        panel,
        backdrop: $('.drawer-backdrop', drawer),
        opener,
        complete,
      });
    };

    const openDrawer = (event) => {
      if (isOpen) return;
      isOpen = true;
      visualToken += 1;
      window.clearTimeout(closeFallbackTimer);
      previousFocus = event?.currentTarget || document.activeElement;
      lockPageScroll();
      drawer.removeAttribute("inert");
      drawer.setAttribute("aria-hidden", "false");
      drawer.classList.add("open");
      setExpanded(true);
      safeFocus(initialFocus || getFocusableElements()[0] || panel);
      isolateAppShell();
      dispatchDrawerChange(true, previousFocus);
    };

    const closeDrawer = ({ restoreFocus = true, restoreScroll = true } = {}) => {
      if (!isOpen) return;
      isOpen = false;
      const token = ++visualToken;
      restoreAppShell();

      const fallbackOpener = openButtons.find(isFocusable);
      const focusTarget = restoreFocus && isFocusable(previousFocus)
        ? previousFocus
        : (restoreFocus ? fallbackOpener : null);
      if (!safeFocus(focusTarget) && drawer.contains(document.activeElement)) {
        document.activeElement.blur?.();
      }

      drawer.setAttribute("inert", "");
      drawer.setAttribute("aria-hidden", "true");
      setExpanded(false);
      const finishVisualClose = () => {
        if (isOpen || token !== visualToken) return;
        window.clearTimeout(closeFallbackTimer);
        drawer.classList.remove("open");
        unlockPageScroll({ restorePosition: restoreScroll });
      };
      dispatchDrawerChange(false, previousFocus, finishVisualClose);
      if (
        typeof TaskFlow.motion?.animateDrawer !== "function"
        || motionQuality.isStatic
        || !window.gsap
      ) {
        finishVisualClose();
      } else {
        closeFallbackTimer = window.setTimeout(finishVisualClose, 400);
      }
      previousFocus = null;
    };

    openButtons.forEach((button) => button.addEventListener("click", openDrawer));
    closeButtons.forEach((button) => {
      button.addEventListener("click", () => closeDrawer());
    });
    $$('a[href]', drawer).forEach((link) => {
      link.addEventListener("click", () => closeDrawer({ restoreFocus: false }));
    });

    document.addEventListener("keydown", (event) => {
      if (!isOpen) return;
      if (event.key === "Escape") {
        event.preventDefault();
        closeDrawer();
        return;
      }
      if (event.key !== "Tab") return;

      const focusable = getFocusableElements();
      if (!focusable.length) {
        event.preventDefault();
        safeFocus(panel);
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (!panel.contains(document.activeElement)) {
        event.preventDefault();
        safeFocus(event.shiftKey ? last : first);
      } else if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        safeFocus(last);
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        safeFocus(first);
      }
    });

    const desktopQuery = window.matchMedia("(min-width: 880px)");
    addMediaListener(desktopQuery, (event) => {
      if (event.matches) closeDrawer({ restoreFocus: false });
    });

    window.addEventListener("pagehide", () => {
      if (!isOpen && !bodyState) return;
      visualToken += 1;
      window.clearTimeout(closeFallbackTimer);
      restoreAppShell();
      drawer.classList.remove("open");
      drawer.setAttribute("inert", "");
      drawer.setAttribute("aria-hidden", "true");
      setExpanded(false);
      unlockPageScroll({ restorePosition: false });
      isOpen = false;
    });

    drawer.setAttribute("inert", "");

    TaskFlow.drawer = {
      get isOpen() {
        return isOpen;
      },
      open: openDrawer,
      close: closeDrawer,
    };
  };

  const initActiveNavigation = () => {
    const page = (document.body?.dataset.page || "").trim();
    if (document.body) document.body.dataset.page = page;
    $$('[data-nav]').forEach((item) => {
      const active = Boolean(page) && item.dataset.nav === page;
      item.classList.toggle("active", active);
      if (active && item.matches("a, button")) {
        item.setAttribute("aria-current", "page");
      } else {
        item.removeAttribute("aria-current");
      }
    });
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

  const initProgress = () => {
    $$('.progress span').forEach((bar) => {
      if (bar.dataset.progressReady === "1") return;
      bar.dataset.progressReady = "1";
      const target = bar.style.width || bar.dataset.progress || "0%";
      bar.dataset.progressTarget = target;
      if (motionQuality.isStatic || window.gsap) {
        bar.style.width = target;
        return;
      }
      bar.style.width = "0";
      requestAnimationFrame(() => {
        bar.style.transition = "width .55s cubic-bezier(.22, 1, .36, 1)";
        bar.style.width = target;
      });
    });
  };

  const initReveal = () => {
    const elements = $$('[data-reveal]');
    if (!elements.length || window.gsap) return;

    elements.forEach((element, index) => {
      element.classList.add("reveal-item");
      element.style.setProperty("--reveal-delay", `${Math.min(index, 4) * 35}ms`);
    });

    if (motionQuality.isStatic || !("IntersectionObserver" in window)) {
      elements.forEach((element) => element.classList.add("is-revealed"));
      return;
    }

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-revealed");
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.04, rootMargin: "0px 0px -2% 0px" });
    elements.forEach((element) => observer.observe(element));
  };

  const initAvatarPreview = () => {
    $$('[data-avatar-editor-v4], [data-avatar-uploader]').forEach((editor) => {
      const input = $('[data-avatar-input-v4], [data-avatar-input], input[type="file"]', editor);
      const image = $('[data-avatar-image-v4], [data-avatar-preview]', editor);
      if (!input || !image || input.dataset.avatarBound === "1") return;
      input.dataset.avatarBound = "1";

      const filename = $('[data-avatar-filename-v4], [data-avatar-filename]', editor);
      const errorElement = $('[data-avatar-error-v4]', editor);
      const originalSource = image.getAttribute("src") || "";
      const hadOriginal = Boolean(originalSource);

      $$('[data-avatar-choose-v4]', editor).forEach((button) => {
        button.addEventListener("click", (event) => {
          event.preventDefault();
          input.click();
        });
      });

      input.addEventListener("change", () => {
        const file = input.files?.[0];
        if (!file) return;
        const valid = file.type.startsWith("image/") && file.size <= 5 * 1024 * 1024;
        if (!valid) {
          input.value = "";
          if (errorElement) {
            errorElement.textContent = "تصویر باید معتبر و کوچک‌تر از ۵ مگابایت باشد.";
          }
          TaskFlowFlashSafe("تصویر باید معتبر و کوچک‌تر از ۵ مگابایت باشد.", "error");
          return;
        }

        if (errorElement) errorElement.textContent = "";
        const reader = new FileReader();
        reader.addEventListener("load", (event) => {
          if (typeof event.target?.result !== "string") return;
          image.src = event.target.result;
          image.hidden = false;
          editor.classList.add("has-image", "has-preview");
          if (filename) filename.textContent = file.name;
        });
        reader.readAsDataURL(file);
      });

      $$('[data-avatar-clear-v4], [data-avatar-remove]', editor).forEach((button) => {
        button.addEventListener("click", (event) => {
          event.preventDefault();
          input.value = "";
          if (hadOriginal) {
            image.src = originalSource;
          } else {
            image.removeAttribute("src");
          }
          image.hidden = !hadOriginal;
          editor.classList.toggle("has-image", hadOriginal);
          editor.classList.remove("has-preview");
          if (filename) filename.textContent = "";
          if (errorElement) errorElement.textContent = "";
        });
      });
    });
  };

  const TaskFlowFlashSafe = (message, type) => {
    if (typeof window.TaskFlowFlash?.create === "function") {
      window.TaskFlowFlash.create(message, type);
    } else if (type === "error") {
      window.alert(message);
    }
  };

  const initForms = () => {
    $$('form:not([data-notification-action-form])').forEach((form) => {
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
        const submitter = event.submitter;
        submitter?.classList.add("is-loading");
        submitter?.setAttribute("aria-disabled", "true");
      });
    });

    window.addEventListener("pageshow", (event) => {
      if (!event.persisted) return;
      $$('form[data-submitting="true"]').forEach((form) => {
        delete form.dataset.submitting;
        form.classList.remove("is-submitting");
        form.removeAttribute("aria-busy");
        $$('[aria-disabled="true"].is-loading', form).forEach((button) => {
          button.classList.remove("is-loading");
          button.removeAttribute("aria-disabled");
        });
      });
    });
  };

  const init = () => {
    if (document.body?.dataset.taskflowAppBound === "1") return;
    if (document.body) document.body.dataset.taskflowAppBound = "1";
    initProductCopyLocalization();
    initDecorativeIcons();
    initThemeToggles();
    initDrawer();
    initActiveNavigation();
    initPasswordToggles();
    initProgress();
    initReveal();
    initAvatarPreview();
    initForms();
    emit("taskflow:appready", {
      theme: theme.value,
      motionQuality: motionQuality.value,
    });
  };

  TaskFlow.app = { init, setUseIcon };
  if (document.body) {
    init();
  } else {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  }
})();
