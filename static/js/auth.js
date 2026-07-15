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
    $$('[data-theme-use]').forEach((use) => setUseIcon(use, theme === "dark" ? "sun" : "moon"));
  }

  function initTheme() {
    const saved = localStorage.getItem(THEME_KEY);
    const preferred = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    applyTheme(saved || preferred);
    $$('[data-theme-toggle]').forEach((button) => button.addEventListener("click", () => applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark")));
  }

  function initPasswordToggles() {
    $$('[data-password-toggle]').forEach((button) => {
      button.addEventListener("click", () => {
        const input = document.getElementById(button.getAttribute("aria-controls"));
        if (!input) return;
        const reveal = input.type === "password";
        input.type = reveal ? "text" : "password";
        button.setAttribute("aria-label", reveal ? "پنهان کردن رمز عبور" : "نمایش رمز عبور");
        setUseIcon($("use", button), reveal ? "eye-off" : "eye");
      });
    });
  }

  function initForms() {
    $$('[data-auth-form]').forEach((form) => {
      form.addEventListener("submit", () => {
        const button = $('[data-submit-button]', form);
        if (!button || button.classList.contains("is-loading")) return;
        button.classList.add("is-loading");
        button.disabled = true;
      });
    });
  }

  function initCardTilt() {
    if (reduceMotion || coarsePointer) return;
    const card = $('[data-tilt-card]');
    if (!card) return;
    let frame = null;
    card.addEventListener("pointermove", (event) => {
      if (frame) cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const rect = card.getBoundingClientRect();
        const x = (event.clientX - rect.left) / rect.width;
        const y = (event.clientY - rect.top) / rect.height;
        card.style.setProperty("--shine-x", `${x * 100}%`);
        card.style.setProperty("--shine-y", `${y * 100}%`);
        card.style.transform = `perspective(1000px) rotateX(${(0.5 - y) * 3.2}deg) rotateY(${(x - 0.5) * 4.5}deg) translateY(-2px)`;
      });
    });
    card.addEventListener("pointerleave", () => { card.style.transform = ""; });
  }

  function initDepthCards() {
    if (reduceMotion || coarsePointer) return;
    const cards = $$('[data-depth]');
    window.addEventListener("pointermove", (event) => {
      const nx = event.clientX / innerWidth - .5;
      const ny = event.clientY / innerHeight - .5;
      cards.forEach((card) => {
        const depth = Number(card.dataset.depth || 1);
        card.style.translate = `${nx * 15 * depth}px ${ny * 10 * depth}px`;
      });
    }, { passive: true });
  }

  function initSpaceCanvas() {
    const canvas = $('[data-auth-space]');
    if (!canvas || reduceMotion) return;
    const ctx = canvas.getContext("2d", { alpha: true });
    let width = 0, height = 0, dpr = 1, animationId = 0, last = 0;
    const pointer = { x: 0, y: 0, tx: 0, ty: 0 };
    let particles = [];

    const makeParticle = () => ({
      x: (Math.random() - .5) * 1600,
      y: (Math.random() - .5) * 1100,
      z: Math.random() * 1500 + 120,
      size: Math.random() * 1.6 + .35,
      speed: Math.random() * 32 + 18,
      hue: Math.random() > .52 ? 252 : 190,
      alpha: Math.random() * .65 + .25,
    });

    function resize() {
      width = window.innerWidth;
      height = window.innerHeight;
      dpr = Math.min(window.devicePixelRatio || 1, 1.7);
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const count = Math.max(65, Math.min(190, Math.floor((width * height) / 9000)));
      particles = Array.from({ length: count }, makeParticle);
    }

    function project(particle) {
      const focal = Math.min(width, height) * .82;
      const scale = focal / particle.z;
      return {
        x: width / 2 + (particle.x + pointer.x * particle.z * .035) * scale,
        y: height / 2 + (particle.y + pointer.y * particle.z * .025) * scale,
        scale,
      };
    }

    function draw(time) {
      const dt = Math.min((time - last) / 1000 || 0, .035);
      last = time;
      pointer.x += (pointer.tx - pointer.x) * .045;
      pointer.y += (pointer.ty - pointer.y) * .045;
      ctx.clearRect(0, 0, width, height);
      const projected = [];

      for (const particle of particles) {
        particle.z -= particle.speed * dt;
        if (particle.z < 80) Object.assign(particle, makeParticle(), { z: 1550 });
        const point = project(particle);
        projected.push({ ...point, particle });
        if (point.x < -20 || point.x > width + 20 || point.y < -20 || point.y > height + 20) continue;
        const radius = Math.max(.35, particle.size * point.scale * 2.4);
        ctx.beginPath();
        ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${particle.hue}, 95%, 74%, ${Math.min(.85, particle.alpha * point.scale * 1.8)})`;
        ctx.shadowColor = `hsla(${particle.hue}, 95%, 66%, .75)`;
        ctx.shadowBlur = radius * 7;
        ctx.fill();
      }
      ctx.shadowBlur = 0;

      if (width > 720) {
        for (let i = 0; i < projected.length; i += 3) {
          const a = projected[i];
          for (let j = i + 3; j < Math.min(projected.length, i + 18); j += 3) {
            const b = projected[j];
            const dx = a.x - b.x, dy = a.y - b.y;
            const distance = Math.hypot(dx, dy);
            if (distance > 95) continue;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y);
            ctx.strokeStyle = `rgba(126, 113, 255, ${(1 - distance / 95) * .08})`;
            ctx.lineWidth = .6;
            ctx.stroke();
          }
        }
      }
      animationId = requestAnimationFrame(draw);
    }

    window.addEventListener("resize", resize, { passive: true });
    window.addEventListener("pointermove", (event) => {
      pointer.tx = (event.clientX / width - .5) * 2;
      pointer.ty = (event.clientY / height - .5) * 2;
    }, { passive: true });
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) cancelAnimationFrame(animationId);
      else { last = performance.now(); animationId = requestAnimationFrame(draw); }
    });
    resize();
    animationId = requestAnimationFrame(draw);
  }

  document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initPasswordToggles();
    initForms();
    initCardTilt();
    initDepthCards();
    initSpaceCanvas();
  }, { once: true });
})();
