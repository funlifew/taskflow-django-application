(() => {
  "use strict";

  const TaskFlow = window.TaskFlow = window.TaskFlow || {};
  if (TaskFlow.motion?.taskflowMotionController) return;

  const gsap = window.gsap;
  const $ = (selector, scope = document) => scope.querySelector(selector);
  const $$ = (selector, scope = document) => Array.from(scope.querySelectorAll(selector));
  const quality = () => TaskFlow.motionQuality?.value
    || (window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "static" : "full");
  const isStatic = () => quality() === "static";
  const isReduced = () => quality() !== "full";
  const numberFormatter = new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 1 });
  let revealObserver = null;
  const countTweens = new Set();
  const drawerCloseCallbacks = new Set();

  const clearMotionStyles = (elements) => {
    if (!gsap) return;
    gsap.set(elements, {
      clearProps: "opacity,visibility,transform,filter,willChange",
    });
  };

  const revealElement = (element, index = 0) => {
    if (!gsap || element.dataset.motionRevealed === "1") return;
    element.dataset.motionRevealed = "1";
    if (isStatic()) {
      clearMotionStyles(element);
      return;
    }

    const reduced = isReduced();
    gsap.fromTo(
      element,
      {
        autoAlpha: 0,
        y: reduced ? 0 : 12,
      },
      {
        autoAlpha: 1,
        y: 0,
        duration: reduced ? 0.2 : 0.46,
        delay: reduced ? 0 : Math.min(index, 4) * 0.035,
        ease: "power3.out",
        overwrite: "auto",
        clearProps: "opacity,visibility,transform,willChange",
      },
    );
  };

  const initReveals = () => {
    const elements = $$('[data-reveal]');
    if (!elements.length) return;
    if (!gsap || isStatic() || !("IntersectionObserver" in window)) {
      elements.forEach((element) => {
        element.dataset.motionRevealed = "1";
        element.classList.add("is-revealed");
      });
      clearMotionStyles(elements);
      return;
    }

    revealObserver?.disconnect();
    revealObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const index = elements.indexOf(entry.target);
        revealElement(entry.target, index);
        revealObserver.unobserve(entry.target);
      });
    }, { threshold: 0.06, rootMargin: "0px 0px -3% 0px" });
    elements.forEach((element) => revealObserver.observe(element));
  };

  const parseDisplayNumber = (text) => {
    const normalized = text
      .trim()
      .replace(/[۰-۹]/g, (digit) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(digit)))
      .replace(/[٠-٩]/g, (digit) => String("٠١٢٣٤٥٦٧٨٩".indexOf(digit)))
      .replace(/[٬,]/g, "")
      .replace(/٫/g, ".");
    const match = normalized.match(/^(-?\d+(?:\.\d+)?)\s*([%٪]?)$/);
    if (!match) return null;
    return { value: Number(match[1]), suffix: match[2] ? "٪" : "" };
  };

  const initCounts = () => {
    $$('.stat-value, [data-count-up]').forEach((element) => {
      if (element.dataset.countBound === "1") return;
      const parsed = parseDisplayNumber(element.textContent);
      if (!parsed || !Number.isFinite(parsed.value)) return;
      element.dataset.countBound = "1";
      element.dataset.countTarget = `${numberFormatter.format(parsed.value)}${parsed.suffix}`;
      if (!gsap || isStatic()) {
        element.textContent = element.dataset.countTarget;
        return;
      }

      const state = { value: 0 };
      let tween = null;
      tween = gsap.to(state, {
        value: parsed.value,
        duration: isReduced() ? 0.35 : 0.7,
        ease: "power2.out",
        onUpdate: () => {
          element.textContent = `${numberFormatter.format(state.value)}${parsed.suffix}`;
        },
        onComplete: () => {
          element.textContent = `${numberFormatter.format(parsed.value)}${parsed.suffix}`;
          countTweens.delete(tween);
        },
      });
      countTweens.add(tween);
    });
  };

  const initProgress = () => {
    $$('.progress span').forEach((bar) => {
      if (bar.dataset.motionProgressBound === "1") return;
      bar.dataset.motionProgressBound = "1";
      const target = bar.dataset.progressTarget || bar.style.width || "0%";
      if (!gsap || isStatic()) {
        bar.style.width = target;
        return;
      }
      gsap.fromTo(
        bar,
        { width: 0 },
        {
          width: target,
          duration: isReduced() ? 0.3 : 0.65,
          ease: "power3.out",
          overwrite: "auto",
        },
      );
    });
  };

  const animateDrawer = ({ open, panel, backdrop, complete }) => {
    if (!gsap || !panel || isStatic()) {
      if (!open) complete?.();
      return;
    }
    gsap.killTweensOf([panel, backdrop]);
    if (open) {
      drawerCloseCallbacks.forEach((finish) => finish());
      gsap.fromTo(
        panel,
        { xPercent: 104 },
        {
          xPercent: 0,
          duration: isReduced() ? 0.18 : 0.26,
          ease: "power3.out",
          clearProps: "transform",
        },
      );
      if (backdrop) {
        gsap.fromTo(backdrop, { autoAlpha: 0 }, {
          autoAlpha: 1,
          duration: 0.2,
          ease: "power2.out",
          clearProps: "opacity,visibility",
        });
      }
    } else {
      const finish = () => {
        if (!drawerCloseCallbacks.delete(finish)) return;
        complete?.();
      };
      drawerCloseCallbacks.add(finish);
      gsap.to(panel, {
        xPercent: 104,
        duration: isReduced() ? 0.15 : 0.22,
        ease: "power2.in",
        clearProps: "transform",
        onComplete: finish,
      });
      if (backdrop) {
        gsap.to(backdrop, {
          autoAlpha: 0,
          duration: 0.16,
          ease: "power2.out",
          clearProps: "opacity,visibility",
        });
      }
    }
  };

  const animateNotification = (panel, open, complete) => {
    if (!panel) {
      complete?.();
      return;
    }
    if (!gsap || isStatic()) {
      if (!open) complete?.();
      return;
    }

    gsap.killTweensOf(panel);
    panel.style.animation = "none";
    if (open) {
      gsap.fromTo(
        panel,
        { autoAlpha: 0, y: -8, scale: isReduced() ? 1 : 0.985 },
        {
          autoAlpha: 1,
          y: 0,
          scale: 1,
          duration: isReduced() ? 0.16 : 0.22,
          ease: "power3.out",
          overwrite: "auto",
          clearProps: "opacity,visibility,transform",
        },
      );
    } else {
      gsap.to(panel, {
        autoAlpha: 0,
        y: -6,
        duration: isReduced() ? 0.12 : 0.17,
        ease: "power2.in",
        overwrite: "auto",
        onComplete: () => {
          panel.style.removeProperty("animation");
          clearMotionStyles(panel);
          complete?.();
        },
      });
    }
  };

  const animateTheme = () => {
    if (!gsap || isStatic()) return;
    const background = $('.app-background, .auth-scene');
    if (!background) return;
    gsap.fromTo(background, { opacity: 0.72 }, {
      opacity: 1,
      duration: isReduced() ? 0.18 : 0.32,
      ease: "sine.inOut",
      overwrite: "auto",
      clearProps: "opacity",
    });
  };

  const feedback = (element, type = "success") => {
    if (!gsap || !element || isStatic()) return;
    gsap.fromTo(
      element,
      { scale: 1 },
      {
        scale: type === "error" ? 0.992 : 1.012,
        duration: 0.14,
        yoyo: true,
        repeat: 1,
        ease: "power2.out",
        clearProps: "transform",
      },
    );
  };

  const settleStaticMotion = () => {
    if (!gsap) return;
    revealObserver?.disconnect();
    const reveals = $$('[data-reveal]');
    const bars = $$('.progress span');
    const panels = $$('.notification-menu__panel');
    const animatedElements = [
      ...reveals,
      ...bars,
      ...panels,
      ...$$('.drawer-panel, .drawer-backdrop, .app-background, .auth-scene'),
    ];
    gsap.killTweensOf(animatedElements);
    drawerCloseCallbacks.forEach((finish) => finish());
    countTweens.forEach((tween) => tween.kill());
    countTweens.clear();
    reveals.forEach((element) => {
      element.dataset.motionRevealed = "1";
      element.classList.add("is-revealed");
    });
    $$('[data-count-target]').forEach((element) => {
      element.textContent = element.dataset.countTarget;
    });
    bars.forEach((bar) => {
      bar.style.width = bar.dataset.progressTarget || bar.style.width || "0%";
    });
    panels.forEach((panel) => {
      panel.style.removeProperty("animation");
      if (panel.getAttribute("aria-hidden") === "true") panel.hidden = true;
    });
    clearMotionStyles(animatedElements);
  };

  const init = () => {
    if (document.body?.dataset.taskflowMotionBound === "1") return;
    if (document.body) document.body.dataset.taskflowMotionBound = "1";
    if (!gsap) document.documentElement.classList.add("gsap-fallback");
    initReveals();
    initCounts();
    initProgress();
  };

  TaskFlow.motion = {
    taskflowMotionController: true,
    init,
    reveal: revealElement,
    animateDrawer,
    animateNotification,
    animateTheme,
    feedback,
  };

  document.addEventListener("taskflow:drawerchange", (event) => animateDrawer(event.detail || {}));
  document.addEventListener("taskflow:themechange", animateTheme);
  document.addEventListener("taskflow:motionchange", (event) => {
    if (event.detail?.quality === "static") {
      settleStaticMotion();
    }
  });
  document.addEventListener("taskflow:dragfeedback", (event) => {
    feedback(event.detail?.element, event.detail?.type);
  });

  if (document.body) {
    init();
  } else {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  }
})();
