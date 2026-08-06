(() => {
  "use strict";

  const board = document.querySelector(
    '[data-column-board][data-column-drag-enabled="true"]',
  );
  if (!board || board.dataset.columnDragBound === "1") return;

  const showMessage = (message, type = "info") => {
    if (typeof window.TaskFlowFlash?.create === "function") {
      window.TaskFlowFlash.create(message, type);
    } else if (type === "error") {
      window.alert(message);
    }
  };

  if (typeof window.Sortable !== "function") {
    showMessage("امکان کشیدن و رها کردن ستون‌ها بارگذاری نشد.", "error");
    return;
  }

  board.dataset.columnDragBound = "1";
  const interactionRoot = board.closest("[data-board-interactions]") || board;
  const statusElement = interactionRoot.querySelector("[data-column-drag-status]");
  const numberFormatter = new Intl.NumberFormat("fa-IR");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const productTerms = /\b(Workspaces?|Tasks?|Boards?|Columns?)\b/gi;
  const productCopy = {
    task: "کار",
    tasks: "کارها",
    workspace: "فضای کاری",
    workspaces: "فضاهای کاری",
    board: "برد",
    boards: "بردها",
    column: "ستون",
    columns: "ستون‌ها",
  };
  let isSaving = false;
  let previousOrder = [];

  const localizeProductCopy = (value) => String(value).replace(
    productTerms,
    (term) => productCopy[term.toLowerCase()] || term,
  );

  const announce = (message) => {
    if (statusElement) statusElement.textContent = message;
  };

  const feedback = (element, type) => {
    document.dispatchEvent(new CustomEvent("taskflow:dragfeedback", {
      detail: { element, type },
    }));
  };

  const getCookie = (name) => {
    const prefix = `${name}=`;
    const cookie = document.cookie
      .split(";")
      .map((item) => item.trim())
      .find((item) => item.startsWith(prefix));
    if (!cookie) return null;
    try {
      return decodeURIComponent(cookie.slice(prefix.length));
    } catch {
      return cookie.slice(prefix.length);
    }
  };

  const getColumnCards = () => Array.from(board.children)
    .filter((element) => element.matches("[data-column-card]"));

  const getCurrentOrder = () => getColumnCards()
    .map((card) => String(card.dataset.columnId));

  const setButtonState = (button, disabled) => {
    if (!button) return;
    button.disabled = disabled;
    if (disabled) {
      button.setAttribute("aria-disabled", "true");
    } else {
      button.removeAttribute("aria-disabled");
    }
  };

  const syncColumnMetadata = () => {
    const cards = getColumnCards();
    cards.forEach((card, index) => {
      const position = numberFormatter.format(index + 1);
      card.dataset.position = String(index);
      const numberElement = card.querySelector("[data-column-order-number]");
      if (numberElement) numberElement.textContent = position;
      const positionElement = card.querySelector("[data-column-position-label]");
      if (positionElement) positionElement.textContent = `جایگاه ${position}`;
      setButtonState(card.querySelector("[data-column-move-previous]"), index === 0);
      setButtonState(
        card.querySelector("[data-column-move-next]"),
        index === cards.length - 1,
      );
    });
  };

  const applyOrder = (orderedColumnIds) => {
    if (!Array.isArray(orderedColumnIds)) return false;
    const normalizedIds = orderedColumnIds.map(String);
    const cards = getColumnCards();
    const cardsById = new Map(cards.map((card) => [
      String(card.dataset.columnId),
      card,
    ]));
    const orderIsComplete = (
      normalizedIds.length === cards.length
      && new Set(normalizedIds).size === cards.length
      && normalizedIds.every((columnId) => cardsById.has(columnId))
    );
    if (!orderIsComplete) return false;
    normalizedIds.forEach((columnId) => board.append(cardsById.get(columnId)));
    syncColumnMetadata();
    return true;
  };

  const restorePreviousOrder = () => {
    if (!previousOrder.length || !applyOrder(previousOrder)) syncColumnMetadata();
  };

  const setSaving = (saving) => {
    isSaving = saving;
    board.dataset.columnSaving = saving ? "true" : "false";
    board.classList.toggle("column-board-is-saving", saving);
    sortable.option("disabled", saving);
  };

  const firstErrorMessage = (payload) => {
    if (typeof payload?.message === "string") {
      return localizeProductCopy(payload.message);
    }
    if (payload?.errors && typeof payload.errors === "object") {
      for (const errorList of Object.values(payload.errors)) {
        if (!Array.isArray(errorList) || !errorList.length) continue;
        const first = errorList[0];
        if (typeof first === "string") return localizeProductCopy(first);
        if (typeof first?.message === "string") return localizeProductCopy(first.message);
      }
    }
    return "جابه‌جایی ستون انجام نشد.";
  };

  const readResponsePayload = async (response) => {
    const contentType = response.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) return null;
    return response.json();
  };

  const applyServerState = (columns) => {
    if (!Array.isArray(columns)) return false;
    const normalized = columns.map((column) => ({
      id: String(column?.id ?? ""),
      position: Number(column?.position),
    }));
    if (normalized.some((column) => !column.id || !Number.isInteger(column.position))) {
      return false;
    }
    normalized.sort((first, second) => first.position - second.position);
    return applyOrder(normalized.map((column) => column.id));
  };

  const failBeforeRequest = (item, message) => {
    restorePreviousOrder();
    announce(message);
    showMessage(message, "error");
    feedback(item, "error");
    previousOrder = [];
  };

  const handleDragEnd = async (event) => {
    board.classList.remove("column-board-is-dragging");
    const item = event.item;
    const oldIndex = Number(event.oldDraggableIndex ?? event.oldIndex);
    const newIndex = Number(event.newDraggableIndex ?? event.newIndex);

    if (!item || !Number.isInteger(oldIndex) || !Number.isInteger(newIndex)) {
      restorePreviousOrder();
      if (item) feedback(item, "error");
      previousOrder = [];
      return;
    }
    if (oldIndex === newIndex) {
      syncColumnMetadata();
      previousOrder = [];
      return;
    }

    const endpoint = item.dataset.reorderUrl;
    const columnTitle = item.dataset.columnTitle || "ستون";
    if (!endpoint) {
      failBeforeRequest(item, "آدرس جابه‌جایی ستون در دسترس نیست.");
      return;
    }
    const csrfToken = getCookie("csrftoken");
    if (!csrfToken) {
      failBeforeRequest(item, "توکن امنیتی درخواست پیدا نشد.");
      return;
    }

    item.classList.add("is-saving");
    syncColumnMetadata();
    setSaving(true);
    announce(`در حال جابه‌جایی ستون ${columnTitle}`);

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({ target_position: newIndex }),
      });
      const payload = await readResponsePayload(response);
      if (!response.ok || !payload || payload.ok !== true) {
        throw new Error(firstErrorMessage(payload));
      }
      if (!applyServerState(payload.columns)) {
        throw new Error("ترتیب بازگشتی سرور کامل نیست.");
      }
      if (Number.isInteger(payload.column?.position)) {
        item.dataset.position = String(payload.column.position);
      }
      const message = typeof payload.message === "string"
        ? localizeProductCopy(payload.message)
        : `ستون «${columnTitle}» جابه‌جا شد.`;
      announce(`ستون ${columnTitle} جابه‌جا شد`);
      showMessage(message, "success");
      feedback(item, "success");
    } catch (error) {
      restorePreviousOrder();
      const message = error instanceof Error
        ? localizeProductCopy(error.message)
        : "جابه‌جایی ستون انجام نشد.";
      announce(`خطا در جابه‌جایی ستون ${columnTitle}`);
      showMessage(message, "error");
      feedback(item, "error");
    } finally {
      item.classList.remove("is-saving");
      setSaving(false);
      previousOrder = [];
    }
  };

  const motionQuality = window.TaskFlow?.motionQuality?.value;
  const animationDuration = reduceMotion.matches || motionQuality === "static"
    ? 0
    : (motionQuality === "reduced" ? 130 : 210);

  const sortable = new window.Sortable(board, {
    draggable: "[data-column-card]",
    handle: "[data-column-drag-handle]",
    direction: "horizontal",
    animation: animationDuration,
    easing: "cubic-bezier(.22, 1, .36, 1)",
    ghostClass: "column-card--ghost",
    chosenClass: "column-card--chosen",
    dragClass: "column-card--dragging",
    forceFallback: true,
    fallbackOnBody: true,
    fallbackTolerance: 5,
    delay: 140,
    delayOnTouchOnly: true,
    touchStartThreshold: 5,
    swapThreshold: 0.65,
    invertSwap: true,
    scroll: true,
    scrollSensitivity: 90,
    scrollSpeed: 14,
    onMove() {
      return !isSaving && board.dataset.taskSaving !== "true";
    },
    onStart() {
      previousOrder = getCurrentOrder();
      board.classList.add("column-board-is-dragging");
    },
    onEnd(event) {
      void handleDragEnd(event);
    },
  });

  const updateAnimation = (quality) => {
    const duration = reduceMotion.matches || quality === "static"
      ? 0
      : (quality === "reduced" ? 130 : 210);
    sortable.option("animation", duration);
  };
  document.addEventListener("taskflow:motionchange", (event) => {
    updateAnimation(event.detail?.quality);
  });
  const onReducedMotionChange = () => {
    updateAnimation(window.TaskFlow?.motionQuality?.value || "full");
  };
  if (typeof reduceMotion.addEventListener === "function") {
    reduceMotion.addEventListener("change", onReducedMotionChange);
  } else {
    reduceMotion.addListener(onReducedMotionChange);
  }

  syncColumnMetadata();
})();
