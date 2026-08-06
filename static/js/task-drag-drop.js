(() => {
  "use strict";

  const board = document.querySelector('[data-task-board][data-drag-enabled="true"]');
  if (!board || board.dataset.taskDragBound === "1") return;

  const showMessage = (message, type = "info") => {
    if (typeof window.TaskFlowFlash?.create === "function") {
      window.TaskFlowFlash.create(message, type);
    } else if (type === "error") {
      window.alert(message);
    }
  };

  if (typeof window.Sortable !== "function") {
    showMessage("امکان کشیدن و رها کردن کارها بارگذاری نشد.", "error");
    return;
  }

  board.dataset.taskDragBound = "1";
  const interactionRoot = board.closest("[data-board-interactions]") || board;
  const taskLists = Array.from(board.querySelectorAll("[data-task-list]"));
  const statusElement = interactionRoot.querySelector("[data-task-drag-status]");
  const listByColumnId = new Map(taskLists.map((list) => [
    String(list.dataset.columnId),
    list,
  ]));
  const countByColumnId = new Map(
    Array.from(board.querySelectorAll("[data-column-task-count]")).map((element) => [
      String(element.dataset.columnTaskCount),
      element,
    ]),
  );
  const countFormatter = new Intl.NumberFormat("fa-IR");
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
  const sortables = [];
  let isSaving = false;

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

  const getTaskCards = (list) => Array.from(list.children)
    .filter((element) => element.matches("[data-task-card]"));

  const getEmptyElements = (list) => Array.from(list.children)
    .filter((element) => element.matches("[data-task-empty]"));

  const createEmptyElement = () => {
    const empty = document.createElement("p");
    empty.className = "task-list-empty";
    empty.dataset.taskEmpty = "";
    empty.textContent = "هنوز کاری در این ستون ثبت نشده است.";
    return empty;
  };

  const syncList = (list) => {
    if (!list) return;
    const cards = getTaskCards(list);
    const emptyElements = getEmptyElements(list);
    list.classList.toggle("is-empty", cards.length === 0);

    if (cards.length === 0) {
      const empty = emptyElements.shift() || createEmptyElement();
      empty.hidden = false;
      if (empty.parentElement !== list) list.append(empty);
      emptyElements.forEach((element) => element.remove());
    } else {
      emptyElements.forEach((element) => element.remove());
    }

    cards.forEach((card, index) => {
      card.dataset.position = String(index);
    });

    const countElement = countByColumnId.get(String(list.dataset.columnId));
    if (countElement) {
      countElement.textContent = `${countFormatter.format(cards.length)} کار`;
    }
  };

  const syncAllLists = () => taskLists.forEach(syncList);

  const insertAtTaskIndex = (list, item, index) => {
    getEmptyElements(list).forEach((element) => element.remove());
    const remaining = getTaskCards(list).filter((card) => card !== item);
    list.insertBefore(item, remaining[index] || null);
  };

  const restorePreviousPosition = (item, sourceList, oldIndex) => {
    insertAtTaskIndex(sourceList, item, oldIndex);
    syncAllLists();
  };

  const setSaving = (saving) => {
    isSaving = saving;
    board.dataset.taskSaving = saving ? "true" : "false";
    board.classList.toggle("task-board-is-saving", saving);
    sortables.forEach((sortable) => sortable.option("disabled", saving));
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
    return "جابه‌جایی کار انجام نشد.";
  };

  const readResponsePayload = async (response) => {
    const contentType = response.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) return null;
    return response.json();
  };

  const applyServerState = (columns) => {
    if (!Array.isArray(columns) || !columns.length) return false;

    const cardsById = new Map(
      Array.from(board.querySelectorAll("[data-task-card]")).map((card) => [
        String(card.dataset.taskId),
        card,
      ]),
    );
    const seenColumns = new Set();
    const seenTasks = new Set();
    const normalized = [];

    for (const state of columns) {
      const columnId = String(state?.id ?? "");
      const list = listByColumnId.get(columnId);
      if (!list || seenColumns.has(columnId) || !Array.isArray(state?.task_ids)) return false;
      const taskIds = state.task_ids.map(String);
      if (
        new Set(taskIds).size !== taskIds.length
        || taskIds.some((id) => !cardsById.has(id) || seenTasks.has(id))
      ) return false;
      seenColumns.add(columnId);
      taskIds.forEach((id) => seenTasks.add(id));
      normalized.push({ list, taskIds });
    }

    const currentIds = normalized.flatMap(({ list }) => getTaskCards(list)
      .map((card) => String(card.dataset.taskId)));
    if (
      currentIds.length !== seenTasks.size
      || currentIds.some((id) => !seenTasks.has(id))
    ) return false;

    normalized.forEach(({ list }) => {
      getEmptyElements(list).forEach((element) => element.remove());
    });
    normalized.forEach(({ list, taskIds }) => {
      taskIds.forEach((id) => list.append(cardsById.get(id)));
    });
    normalized.forEach(({ list }) => syncList(list));
    return true;
  };

  const failBeforeRequest = (item, sourceList, oldIndex, message) => {
    restorePreviousPosition(item, sourceList, oldIndex);
    announce(message);
    showMessage(message, "error");
    feedback(item, "error");
  };

  const handleDragEnd = async (event) => {
    board.classList.remove("task-board-is-dragging");
    const item = event.item;
    const sourceList = event.from;
    const targetList = event.to;
    const oldIndex = Number(event.oldDraggableIndex ?? event.oldIndex);
    const newIndex = Number(event.newDraggableIndex ?? event.newIndex);

    if (!item || !sourceList || !targetList) {
      syncAllLists();
      return;
    }
    if (!Number.isInteger(oldIndex) || !Number.isInteger(newIndex)) {
      syncAllLists();
      feedback(item, "error");
      return;
    }
    if (sourceList === targetList && oldIndex === newIndex) {
      syncList(sourceList);
      return;
    }

    const endpoint = item.dataset.reorderUrl;
    const targetColumnId = Number(targetList.dataset.columnId);
    if (!endpoint || !Number.isInteger(targetColumnId)) {
      failBeforeRequest(
        item,
        sourceList,
        oldIndex,
        "اطلاعات جابه‌جایی کار کامل نیست.",
      );
      return;
    }

    const csrfToken = getCookie("csrftoken");
    if (!csrfToken) {
      failBeforeRequest(
        item,
        sourceList,
        oldIndex,
        "توکن امنیتی درخواست پیدا نشد.",
      );
      return;
    }

    const taskTitle = item.dataset.taskTitle || "کار";
    item.classList.add("is-saving");
    syncList(sourceList);
    if (targetList !== sourceList) syncList(targetList);
    setSaving(true);
    announce(`در حال جابه‌جایی ${taskTitle}`);

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({
          target_column: targetColumnId,
          target_position: newIndex,
        }),
      });
      const payload = await readResponsePayload(response);
      if (!response.ok || !payload || payload.ok !== true) {
        throw new Error(firstErrorMessage(payload));
      }
      if (!applyServerState(payload.columns)) {
        throw new Error("ترتیب بازگشتی سرور کامل نیست.");
      }

      if (payload.task?.reorder_url) {
        item.dataset.reorderUrl = payload.task.reorder_url;
      }
      if (Number.isInteger(payload.task?.position)) {
        item.dataset.position = String(payload.task.position);
      }
      const message = typeof payload.message === "string"
        ? localizeProductCopy(payload.message)
        : `کار «${taskTitle}» جابه‌جا شد.`;
      announce(`${taskTitle} جابه‌جا شد`);
      showMessage(message, "success");
      feedback(item, "success");
    } catch (error) {
      restorePreviousPosition(item, sourceList, oldIndex);
      const message = error instanceof Error
        ? localizeProductCopy(error.message)
        : "جابه‌جایی کار انجام نشد.";
      announce(`خطا در جابه‌جایی ${taskTitle}`);
      showMessage(message, "error");
      feedback(item, "error");
    } finally {
      item.classList.remove("is-saving");
      setSaving(false);
    }
  };

  const motionQuality = window.TaskFlow?.motionQuality?.value;
  const durationForQuality = (value) => (
    reduceMotion.matches || value === "static"
      ? 0
      : (value === "reduced" ? 120 : 180)
  );
  const animationDuration = durationForQuality(motionQuality);

  taskLists.forEach((list) => {
    const sortable = new window.Sortable(list, {
      group: {
        name: `taskflow-board-${board.dataset.boardId}`,
        pull: true,
        put: true,
      },
      draggable: "[data-task-card]",
      handle: "[data-drag-handle]",
      animation: animationDuration,
      easing: "cubic-bezier(.22, 1, .36, 1)",
      ghostClass: "task-card--ghost",
      chosenClass: "task-card--chosen",
      dragClass: "task-card--dragging",
      forceFallback: true,
      fallbackOnBody: true,
      fallbackTolerance: 4,
      delay: 120,
      delayOnTouchOnly: true,
      touchStartThreshold: 4,
      emptyInsertThreshold: 50,
      scroll: true,
      scrollSensitivity: 80,
      scrollSpeed: 12,
      onMove() {
        return !isSaving && board.dataset.columnSaving !== "true";
      },
      onStart() {
        board.classList.add("task-board-is-dragging");
      },
      onEnd(event) {
        void handleDragEnd(event);
      },
    });
    sortables.push(sortable);
  });

  const updateAnimation = (value) => {
    const duration = durationForQuality(value);
    sortables.forEach((sortable) => sortable.option("animation", duration));
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

  syncAllLists();
})();
