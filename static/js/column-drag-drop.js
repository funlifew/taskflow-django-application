(() => {
  "use strict";

  const board = document.querySelector(
    (
      "[data-column-board]"
      + '[data-column-drag-enabled="true"]'
    )
  );

  if (!board) {
    return;
  }

  const interactionRoot = (
    board.closest(
      "[data-board-interactions]"
    )
    || board
  );

  const statusElement = (
    interactionRoot.querySelector(
      "[data-column-drag-status]"
    )
  );

  const showMessage = (
    message,
    type = "info"
  ) => {
    if (
      window.TaskFlowFlash
      && typeof (
        window.TaskFlowFlash.create
      ) === "function"
    ) {
      window.TaskFlowFlash.create(
        message,
        type
      );

      return;
    }

    if (type === "error") {
      window.alert(message);
    }
  };

  if (
    typeof window.Sortable
    !== "function"
  ) {
    showMessage(
      (
        "امکان Drag & Drop ستون‌ها "
        + "بارگذاری نشد."
      ),
      "error"
    );

    return;
  }

  let isSaving = false;
  let previousOrder = [];

  const announce = (message) => {
    if (statusElement) {
      statusElement.textContent = (
        message
      );
    }
  };

  const getCookie = (name) => {
    const prefix = `${name}=`;

    const cookie = (
      document.cookie
      .split(";")
      .map(
        (item) => item.trim()
      )
      .find(
        (item) => (
          item.startsWith(prefix)
        )
      )
    );

    if (!cookie) {
      return null;
    }

    return decodeURIComponent(
      cookie.slice(prefix.length)
    );
  };

  const getColumnCards = () => (
    Array.from(board.children)
    .filter(
      (element) => (
        element.matches(
          "[data-column-card]"
        )
      )
    )
  );

  const getCurrentOrder = () => (
    getColumnCards()
    .map(
      (card) => (
        String(
          card.dataset.columnId
        )
      )
    )
  );

  const setButtonState = (
    button,
    disabled
  ) => {
    if (!button) {
      return;
    }

    button.disabled = disabled;

    if (disabled) {
      button.setAttribute(
        "aria-disabled",
        "true"
      );
    } else {
      button.removeAttribute(
        "aria-disabled"
      );
    }
  };

  const syncColumnMetadata = () => {
    const cards = getColumnCards();

    cards.forEach(
      (card, index) => {
        card.dataset.position = (
          String(index)
        );

        const numberElement = (
          card.querySelector(
            "[data-column-order-number]"
          )
        );

        if (numberElement) {
          numberElement.textContent = (
            String(index + 1)
          );
        }

        const positionElement = (
          card.querySelector(
            "[data-column-position-label]"
          )
        );

        if (positionElement) {
          positionElement.textContent = (
            `جایگاه ${index + 1}`
          );
        }

        setButtonState(
          card.querySelector(
            "[data-column-move-previous]"
          ),
          index === 0
        );

        setButtonState(
          card.querySelector(
            "[data-column-move-next]"
          ),
          index === (
            cards.length - 1
          )
        );
      }
    );
  };

  const applyOrder = (
    orderedColumnIds
  ) => {
    const cards = getColumnCards();

    const cardsById = new Map(
      cards.map(
        (card) => [
          String(
            card.dataset.columnId
          ),
          card,
        ]
      )
    );

    const uniqueIds = new Set(
      orderedColumnIds
    );

    const orderIsComplete = (
      orderedColumnIds.length
      === cards.length
      && uniqueIds.size
      === cards.length
      && orderedColumnIds.every(
        (columnId) => (
          cardsById.has(
            String(columnId)
          )
        )
      )
    );

    if (!orderIsComplete) {
      return false;
    }

    orderedColumnIds.forEach(
      (columnId) => {
        board.appendChild(
          cardsById.get(
            String(columnId)
          )
        );
      }
    );

    syncColumnMetadata();

    return true;
  };

  const restorePreviousOrder = () => {
    if (
      previousOrder.length === 0
    ) {
      syncColumnMetadata();
      return;
    }

    applyOrder(previousOrder);
  };

  const setSaving = (saving) => {
    isSaving = saving;

    board.dataset.columnSaving = (
      saving
      ? "true"
      : "false"
    );

    board.classList.toggle(
      "column-board-is-saving",
      saving
    );

    sortable.option(
      "disabled",
      saving
    );
  };

  const firstErrorMessage = (
    payload
  ) => {
    if (
      payload
      && typeof payload.message
      === "string"
    ) {
      return payload.message;
    }

    const errors = (
      payload
      && payload.errors
    );

    if (
      errors
      && typeof errors === "object"
    ) {
      for (
        const errorList
        of Object.values(errors)
      ) {
        if (
          !Array.isArray(errorList)
          || errorList.length === 0
        ) {
          continue;
        }

        const firstError = (
          errorList[0]
        );

        if (
          typeof firstError
          === "string"
        ) {
          return firstError;
        }

        if (
          firstError
          && typeof (
            firstError.message
          ) === "string"
        ) {
          return firstError.message;
        }
      }
    }

    return (
      "جابه‌جایی ستون انجام نشد."
    );
  };

  const readResponsePayload = async (
    response
  ) => {
    const contentType = (
      response.headers.get(
        "content-type"
      )
      || ""
    );

    if (
      !contentType.includes(
        "application/json"
      )
    ) {
      return null;
    }

    return response.json();
  };

  const applyServerState = (
    columns
  ) => {
    if (!Array.isArray(columns)) {
      return false;
    }

    const orderedColumns = [
      ...columns,
    ].sort(
      (first, second) => (
        first.position
        - second.position
      )
    );

    return applyOrder(
      orderedColumns.map(
        (column) => (
          String(column.id)
        )
      )
    );
  };

  const handleDragEnd = async (
    event
  ) => {
    board.classList.remove(
      "column-board-is-dragging"
    );

    const item = event.item;

    const oldIndex = Number(
      event.oldDraggableIndex
      ?? event.oldIndex
    );

    const newIndex = Number(
      event.newDraggableIndex
      ?? event.newIndex
    );

    if (
      !Number.isInteger(oldIndex)
      || !Number.isInteger(newIndex)
    ) {
      restorePreviousOrder();
      previousOrder = [];
      return;
    }

    if (oldIndex === newIndex) {
      syncColumnMetadata();
      previousOrder = [];
      return;
    }

    const endpoint = (
      item.dataset.reorderUrl
    );

    const columnTitle = (
      item.dataset.columnTitle
      || "ستون"
    );

    if (!endpoint) {
      restorePreviousOrder();

      showMessage(
        (
          "آدرس جابه‌جایی ستون "
          + "در دسترس نیست."
        ),
        "error"
      );

      previousOrder = [];
      return;
    }

    const csrfToken = getCookie(
      "csrftoken"
    );

    if (!csrfToken) {
      restorePreviousOrder();

      showMessage(
        (
          "توکن امنیتی درخواست "
          + "پیدا نشد."
        ),
        "error"
      );

      previousOrder = [];
      return;
    }

    item.classList.add(
      "is-saving"
    );

    syncColumnMetadata();
    setSaving(true);

    announce(
      `در حال جابه‌جایی ستون ${columnTitle}`
    );

    try {
      const response = await fetch(
        endpoint,
        {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": (
              "application/json"
            ),
            "X-CSRFToken": csrfToken,
            "X-Requested-With": (
              "XMLHttpRequest"
            ),
          },
          body: JSON.stringify(
            {
              target_position: (
                newIndex
              ),
            }
          ),
        }
      );

      const payload = await (
        readResponsePayload(response)
      );

      if (
        !response.ok
        || !payload
        || payload.ok !== true
      ) {
        throw new Error(
          firstErrorMessage(payload)
        );
      }

      const stateApplied = (
        applyServerState(
          payload.columns
        )
      );

      if (!stateApplied) {
        throw new Error(
          (
            "ترتیب بازگشتی سرور "
            + "کامل نیست."
          )
        );
      }

      if (
        payload.column
        && Number.isInteger(
          payload.column.position
        )
      ) {
        item.dataset.position = (
          String(
            payload.column.position
          )
        );
      }

      announce(
        `ستون ${columnTitle} جابه‌جا شد`
      );

      showMessage(
        (
          payload.message
          || (
            `ستون «${columnTitle}» `
            + "جابه‌جا شد."
          )
        ),
        "success"
      );

    } catch (error) {
      restorePreviousOrder();

      const message = (
        error instanceof Error
        ? error.message
        : (
          "جابه‌جایی ستون "
          + "انجام نشد."
        )
      );

      announce(
        (
          "خطا در جابه‌جایی ستون "
          + columnTitle
        )
      );

      showMessage(
        message,
        "error"
      );

    } finally {
      item.classList.remove(
        "is-saving"
      );

      setSaving(false);
      previousOrder = [];
    }
  };

  const sortable = new window.Sortable(
    board,
    {
      draggable: (
        "[data-column-card]"
      ),

      handle: (
        "[data-column-drag-handle]"
      ),

      direction: "horizontal",

      animation: 210,

      easing: (
        "cubic-bezier("
        + ".22, 1, .36, 1)"
      ),

      ghostClass: (
        "column-card--ghost"
      ),

      chosenClass: (
        "column-card--chosen"
      ),

      dragClass: (
        "column-card--dragging"
      ),

      forceFallback: true,
      fallbackOnBody: true,
      fallbackTolerance: 5,

      delay: 140,
      delayOnTouchOnly: true,
      touchStartThreshold: 5,

      swapThreshold: .65,
      invertSwap: true,

      scroll: true,
      scrollSensitivity: 90,
      scrollSpeed: 14,

      onMove() {
        return (
          !isSaving
          && (
            board.dataset.taskSaving
            !== "true"
          )
        );
      },

      onStart() {
        previousOrder = (
          getCurrentOrder()
        );

        board.classList.add(
          "column-board-is-dragging"
        );
      },

      onEnd(event) {
        void handleDragEnd(event);
      },
    }
  );

  syncColumnMetadata();
})();