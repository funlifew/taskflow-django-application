(() => {
  "use strict";

  const menus = Array.from(
    document.querySelectorAll(
      "[data-notification-menu]"
    )
  );

  if (menus.length === 0) {
    return;
  }

  const closeMenu = (
    menu,
    {
      restoreFocus = false,
    } = {}
  ) => {
    const toggle = menu.querySelector(
      "[data-notification-toggle]"
    );

    const panel = menu.querySelector(
      "[data-notification-panel]"
    );

    if (!toggle || !panel) {
      return;
    }

    menu.classList.remove(
      "is-open"
    );

    toggle.setAttribute(
      "aria-expanded",
      "false"
    );

    panel.hidden = true;

    if (restoreFocus) {
      toggle.focus();
    }
  };

  const closeOtherMenus = (
    currentMenu
  ) => {
    menus.forEach((menu) => {
      if (menu !== currentMenu) {
        closeMenu(menu);
      }
    });
  };

  const openMenu = (menu) => {
    const toggle = menu.querySelector(
      "[data-notification-toggle]"
    );

    const panel = menu.querySelector(
      "[data-notification-panel]"
    );

    if (!toggle || !panel) {
      return;
    }

    closeOtherMenus(menu);

    panel.hidden = false;

    toggle.setAttribute(
      "aria-expanded",
      "true"
    );

    window.requestAnimationFrame(
      () => {
        menu.classList.add(
          "is-open"
        );
      }
    );
  };

  const isMenuOpen = (menu) => (
    menu.classList.contains(
      "is-open"
    )
  );

  menus.forEach((menu) => {
    const toggle = menu.querySelector(
      "[data-notification-toggle]"
    );

    const panel = menu.querySelector(
      "[data-notification-panel]"
    );

    if (!toggle || !panel) {
      return;
    }

    toggle.addEventListener(
      "click",
      (event) => {
        event.preventDefault();

        if (isMenuOpen(menu)) {
          closeMenu(menu);
          return;
        }

        openMenu(menu);
      }
    );

    menu.querySelectorAll(
      "[data-notification-action-form]"
    ).forEach((form) => {
      form.addEventListener(
        "submit",
        () => {
          menu.classList.add(
            "is-submitting"
          );

          const submitButton = (
            form.querySelector(
              'button[type="submit"]'
            )
          );

          if (submitButton) {
            submitButton.disabled = true;
          }
        }
      );
    });
  });

  document.addEventListener(
    "click",
    (event) => {
      menus.forEach((menu) => {
        if (
          isMenuOpen(menu)
          && !menu.contains(
            event.target
          )
        ) {
          closeMenu(menu);
        }
      });
    }
  );

  document.addEventListener(
    "keydown",
    (event) => {
      if (event.key !== "Escape") {
        return;
      }

      const openMenuElement = (
        menus.find(
          (menu) => isMenuOpen(menu)
        )
      );

      if (!openMenuElement) {
        return;
      }

      event.preventDefault();

      closeMenu(
        openMenuElement,
        {
          restoreFocus: true,
        }
      );
    }
  );
})();