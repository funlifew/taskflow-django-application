(() => {
  "use strict";

  const board = document.querySelector(
    '[data-task-board][data-drag-enabled="true"]'
  );

  if (!board) {
    return;
  }

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
        "امکان Drag & Drop "
        + "بارگذاری نشد."
      ),
      "error"
    );

    return;
  }

  const taskLists = Array.from(
    board.querySelectorAll(
      "[data-task-list]"
    )
  );

  const listByColumnId = new Map(
    taskLists.map(
      (list) => [
        String(
          list.dataset.columnId
        ),
        list,
      ]
    )
  );

  const countByColumnId = new Map(
    Array.from(
      board.querySelectorAll(
        "[data-column-task-count]"
      )
    ).map(
      (element) => [
        String(
          element.dataset
            .columnTaskCount
        ),
        element,
      ]
    )
  );

  const statusElement = (
    board.querySelector(
      "[data-drag-status]"
    )
  );

  const sortables = [];
  let isSaving = false;

  const announce = (message) => {
    if (statusElement) {
      statusElement.textContent = (
        message
      );
    }
  };

  const getCookie = (name) => {
    const cookiePrefix = (
      `${name}=`
    );

    const cookie = (
      document.cookie
      .split(";")
      .map(
        (item) => item.trim()
      )
      .find(
        (item) => (
          item.startsWith(
            cookiePrefix
          )
        )
      )
    );

    if (!cookie) {
      return null;
    }

    return decodeURIComponent(
      cookie.slice(
        cookiePrefix.length
      )
    );
  };

  const getTaskCards = (list) => (
    Array.from(list.children)
    .filter(
      (element) => (
        element.matches(
          "[data-task-card]"
        )
      )
    )
  );

  const getEmptyElement = (list) => (
    Array.from(list.children)
    .find(
      (element) => (
        element.matches(
          "[data-task-empty]"
        )
      )
    )
  );

  const syncList = (list) => {
    const cards = getTaskCards(
      list
    );

    const emptyElement = (
      getEmptyElement(list)
    );

    list.classList.toggle(
      "is-empty",
      cards.length === 0
    );

    if (emptyElement) {
      emptyElement.hidden = (
        cards.length > 0
      );
    }

    cards.forEach(
      (card, index) => {
        card.dataset.position = (
          String(index)
        );
      }
    );

    const countElement = (
      countByColumnId.get(
        String(
          list.dataset.columnId
        )
      )
    );

    if (countElement) {
      countElement.textContent = (
        `${cards.length} Task`
      );
    }
  };

  const syncAllLists = () => {
    taskLists.forEach(
      (list) => syncList(list)
    );
  };

  const insertAtTaskIndex = (
    list,
    item,
    index
  ) => {
    const remainingCards = (
      getTaskCards(list)
      .filter(
        (card) => (
          card !== item
        )
      )
    );

    const emptyElement = (
      getEmptyElement(list)
    );

    const referenceElement = (
      remainingCards[index]
      || emptyElement
      || null
    );

    list.insertBefore(
      item,
      referenceElement
    );
  };

  const restorePreviousPosition = (
    item,
    sourceList,
    oldIndex
  ) => {
    insertAtTaskIndex(
      sourceList,
      item,
      oldIndex
    );

    syncAllLists();
  };

  const setSaving = (saving) => {
    isSaving = saving;

    board.classList.toggle(
      "task-board-is-saving",
      saving
    );

    sortables.forEach(
      (sortable) => {
        sortable.option(
          "disabled",
          saving
        );
      }
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
          Array.isArray(errorList)
          && errorList.length > 0
        ) {
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
            return (
              firstError.message
            );
          }
        }
      }
    }

    return (
      "جابه‌جایی Task انجام نشد."
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
      syncAllLists();
      return;
    }

    const cardsById = new Map(
      Array.from(
        board.querySelectorAll(
          "[data-task-card]"
        )
      ).map(
        (card) => [
          String(
            card.dataset.taskId
          ),
          card,
        ]
      )
    );

    columns.forEach(
      (columnState) => {
        const list = (
          listByColumnId.get(
            String(columnState.id)
          )
        );

        if (!list) {
          return;
        }

        const emptyElement = (
          getEmptyElement(list)
        );

        columnState.task_ids.forEach(
          (taskId) => {
            const card = (
              cardsById.get(
                String(taskId)
              )
            );

            if (!card) {
              return;
            }

            list.insertBefore(
              card,
              emptyElement || null
            );
          }
        );

        syncList(list);
      }
    );
  };

  const handleDragEnd = async (
    event
  ) => {
    board.classList.remove(
      "task-board-is-dragging"
    );

    const item = event.item;
    const sourceList = event.from;
    const targetList = event.to;

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
      syncAllLists();
      return;
    }

    const sourceColumnId = (
      String(
        sourceList.dataset.columnId
      )
    );

    const targetColumnId = (
      Number(
        targetList.dataset.columnId
      )
    );

    if (
      sourceList === targetList
      && oldIndex === newIndex
    ) {
      syncList(sourceList);
      return;
    }

    const endpoint = (
      item.dataset.reorderUrl
    );

    if (
      !endpoint
      || !Number.isInteger(
        targetColumnId
      )
    ) {
      restorePreviousPosition(
        item,
        sourceList,
        oldIndex
      );

      showMessage(
        (
          "اطلاعات جابه‌جایی "
          + "Task کامل نیست."
        ),
        "error"
      );

      return;
    }

    const csrfToken = getCookie(
      "csrftoken"
    );

    if (!csrfToken) {
      restorePreviousPosition(
        item,
        sourceList,
        oldIndex
      );

      showMessage(
        (
          "توکن امنیتی درخواست "
          + "پیدا نشد."
        ),
        "error"
      );

      return;
    }

    const taskTitle = (
      item.dataset.taskTitle
      || "Task"
    );

    item.classList.add(
      "is-saving"
    );

    syncList(sourceList);

    if (
      targetList !== sourceList
    ) {
      syncList(targetList);
    }

    setSaving(true);

    announce(
      `در حال جابه‌جایی ${taskTitle}`
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
            "X-CSRFToken": (
              csrfToken
            ),
            "X-Requested-With": (
              "XMLHttpRequest"
            ),
          },
          body: JSON.stringify(
            {
              target_column: (
                targetColumnId
              ),
              target_position: (
                newIndex
              ),
            }
          ),
        }
      );

      const payload = await (
        readResponsePayload(
          response
        )
      );

      if (
        !response.ok
        || !payload
        || payload.ok !== true
      ) {
        throw new Error(
          firstErrorMessage(
            payload
          )
        );
      }

      applyServerState(
        payload.columns
      );

      if (
        payload.task
        && payload.task.reorder_url
      ) {
        item.dataset.reorderUrl = (
          payload.task.reorder_url
        );
      }

      if (
        payload.task
        && Number.isInteger(
          payload.task.position
        )
      ) {
        item.dataset.position = (
          String(
            payload.task.position
          )
        );
      }

      announce(
        `${taskTitle} جابه‌جا شد`
      );

      showMessage(
        (
          payload.message
          || (
            `Task «${taskTitle}» `
            + "جابه‌جا شد."
          )
        ),
        "success"
      );

    } catch (error) {
      restorePreviousPosition(
        item,
        sourceList,
        oldIndex
      );

      const errorMessage = (
        error instanceof Error
        ? error.message
        : (
          "جابه‌جایی Task "
          + "انجام نشد."
        )
      );

      announce(
        `خطا در جابه‌جایی ${taskTitle}`
      );

      showMessage(
        errorMessage,
        "error"
      );

    } finally {
      item.classList.remove(
        "is-saving"
      );

      setSaving(false);

      // sourceColumnId عمداً نگه داشته
      // شده تا هنگام Debug مشخص باشد
      // عملیات از کدام ستون آغاز شده است.
      void sourceColumnId;
    }
  };

  taskLists.forEach(
    (list) => {
      const sortable = (
        new window.Sortable(
          list,
          {
            group: {
              name: (
                `taskflow-board-`
                + board.dataset.boardId
              ),
              pull: true,
              put: true,
            },

            draggable: (
              "[data-task-card]"
            ),

            handle: (
              "[data-drag-handle]"
            ),

            animation: 180,
            easing: (
              "cubic-bezier("
              + ".22, 1, .36, 1)"
            ),

            ghostClass: (
              "task-card--ghost"
            ),

            chosenClass: (
              "task-card--chosen"
            ),

            dragClass: (
              "task-card--dragging"
            ),

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
              return !isSaving;
            },

            onStart() {
              board.classList.add(
                "task-board-is-dragging"
              );
            },

            onEnd(event) {
              void handleDragEnd(
                event
              );
            },
          }
        )
      );

      sortables.push(
        sortable
      );
    }
  );

  syncAllLists();
})();