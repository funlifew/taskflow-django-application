(() => {
  "use strict";

  const TaskFlow = window.TaskFlow = window.TaskFlow || {};
  const menus = Array.from(document.querySelectorAll("[data-notification-menu]"));
  if (!menus.length) return;

  const controllers = new Map();
  const emitChange = (detail) => {
    document.dispatchEvent(new CustomEvent("taskflow:notificationchange", { detail }));
  };

  const closeOtherMenus = (currentMenu) => {
    controllers.forEach((controller, menu) => {
      if (menu !== currentMenu) controller.close();
    });
  };

  const bindMenu = (menu) => {
    if (menu.dataset.notificationBound === "1") return;
    const toggle = menu.querySelector("[data-notification-toggle]");
    const panel = menu.querySelector("[data-notification-panel]");
    if (!toggle || !panel) return;

    menu.dataset.notificationBound = "1";
    let open = !panel.hidden && menu.classList.contains("is-open");
    let openFrame = 0;
    let focusFrame = 0;
    let transitionToken = 0;

    const finishClose = (token) => {
      if (open || token !== transitionToken) return;
      panel.hidden = true;
      panel.setAttribute("inert", "");
    };

    const close = ({ restoreFocus = false } = {}) => {
      if (!open && panel.hidden) return;
      open = false;
      transitionToken += 1;
      const token = transitionToken;
      cancelAnimationFrame(openFrame);
      menu.classList.remove("is-open");
      toggle.setAttribute("aria-expanded", "false");
      panel.setAttribute("aria-hidden", "true");
      panel.setAttribute("inert", "");

      const complete = () => finishClose(token);
      emitChange({ open: false, menu, toggle, panel, complete });
      if (typeof TaskFlow.motion?.animateNotification === "function") {
        TaskFlow.motion.animateNotification(panel, false, complete);
      } else {
        complete();
      }
      if (restoreFocus) {
        try {
          toggle.focus({ preventScroll: true });
        } catch {
          toggle.focus();
        }
      }
    };

    const show = () => {
      if (open) return;
      closeOtherMenus(menu);
      open = true;
      transitionToken += 1;
      cancelAnimationFrame(openFrame);
      panel.hidden = false;
      panel.removeAttribute("inert");
      panel.setAttribute("aria-hidden", "false");
      toggle.setAttribute("aria-expanded", "true");
      openFrame = requestAnimationFrame(() => {
        if (!open || panel.hidden) return;
        menu.classList.add("is-open");
        emitChange({ open: true, menu, toggle, panel });
        TaskFlow.motion?.animateNotification?.(panel, true);
      });
    };

    const controller = {
      get isOpen() {
        return open;
      },
      open: show,
      close,
    };
    controllers.set(menu, controller);

    toggle.addEventListener("click", (event) => {
      event.preventDefault();
      open ? close() : show();
    });

    menu.addEventListener("focusout", () => {
      cancelAnimationFrame(focusFrame);
      focusFrame = requestAnimationFrame(() => {
        if (open && !menu.contains(document.activeElement)) close();
      });
    });

    menu.querySelectorAll("[data-notification-action-form]").forEach((form) => {
      if (form.dataset.notificationFormBound === "1") return;
      form.dataset.notificationFormBound = "1";
      form.addEventListener("submit", (event) => {
        if (form.dataset.submitting === "true") {
          event.preventDefault();
          return;
        }
        form.dataset.submitting = "true";
        menu.classList.add("is-submitting");
        form.setAttribute("aria-busy", "true");
        const submitButton = event.submitter || form.querySelector('button[type="submit"]');
        if (submitButton) {
          submitButton.classList.add("is-loading");
          submitButton.setAttribute("aria-disabled", "true");
          submitButton.setAttribute("aria-busy", "true");
        }
      });
    });
  };

  menus.forEach(bindMenu);

  document.addEventListener("click", (event) => {
    controllers.forEach((controller, menu) => {
      if (controller.isOpen && !menu.contains(event.target)) controller.close();
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    const openController = Array.from(controllers.values()).find((controller) => controller.isOpen);
    if (!openController) return;
    event.preventDefault();
    openController.close({ restoreFocus: true });
  });

  document.addEventListener("taskflow:drawerchange", (event) => {
    if (!event.detail?.open) return;
    controllers.forEach((controller) => controller.close());
  });

  window.addEventListener("pageshow", (event) => {
    if (!event.persisted) return;
    menus.forEach((menu) => {
      menu.classList.remove("is-submitting");
      menu.querySelectorAll('[data-notification-action-form]').forEach((form) => {
        delete form.dataset.submitting;
        form.removeAttribute("aria-busy");
        form.querySelectorAll('[aria-busy="true"]').forEach((button) => {
          button.classList.remove("is-loading");
          button.removeAttribute("aria-disabled");
          button.removeAttribute("aria-busy");
        });
      });
    });
  });

  menus.forEach((menu) => {
    const panel = menu.querySelector("[data-notification-panel]");
    if (!panel) return;
    const open = !panel.hidden && menu.classList.contains("is-open");
    panel.setAttribute("aria-hidden", open ? "false" : "true");
    if (!open) panel.setAttribute("inert", "");
  });

  TaskFlow.notifications = {
    closeAll() {
      controllers.forEach((controller) => controller.close());
    },
  };
})();
