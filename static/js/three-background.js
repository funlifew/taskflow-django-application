(() => {
  "use strict";

  const TaskFlow = window.TaskFlow = window.TaskFlow || {};
  if (TaskFlow.threeBackground?.taskflowThreeBackground) return;

  const THREE = window.THREE;
  const canvas = document.querySelector("[data-three-background]");
  const root = document.documentElement;
  const coarsePointer = window.matchMedia("(pointer: coarse)");
  const mobileViewport = window.matchMedia("(max-width: 720px)");
  const fallbackTargets = [root, canvas?.parentElement].filter(Boolean);
  const listeners = [];

  let renderer = null;
  let scene = null;
  let camera = null;
  let particles = null;
  let particleGeometry = null;
  let particleMaterial = null;
  let workflowGroup = null;
  let workflowCore = null;
  let workflowNodes = [];
  let resizeObserver = null;
  let resizeFrame = 0;
  let animationFrame = 0;
  let lastFrame = 0;
  let destroyed = false;
  let contextLost = false;
  let mounted = false;
  let drawerOpen = false;
  let pointerX = 0;
  let pointerY = 0;
  let targetPointerX = 0;
  let targetPointerY = 0;
  let currentTheme = TaskFlow.theme?.value || root.dataset.theme || "light";
  const disposables = new Set();

  const quality = () => TaskFlow.motionQuality?.value
    || (window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "static" : "full");

  const isStatic = () => quality() === "static";
  const shouldAnimate = () => (
    mounted
    && !destroyed
    && !contextLost
    && !document.hidden
    && !drawerOpen
    && !isStatic()
  );

  const addListener = (target, name, handler, options) => {
    if (typeof target.addEventListener === "function") {
      target.addEventListener(name, handler, options);
      listeners.push(() => target.removeEventListener(name, handler, options));
    } else if (name === "change" && typeof target.addListener === "function") {
      target.addListener(handler);
      listeners.push(() => target.removeListener(handler));
    }
  };

  const setFallback = (active) => {
    fallbackTargets.forEach((element) => {
      element.classList.toggle("three-background-fallback", active);
    });
    if (canvas) canvas.hidden = active;
    root.dataset.webgl = active ? "fallback" : "active";
    TaskFlow.motionQuality?.refresh?.();
  };

  const registerDisposable = (...items) => {
    items.filter(Boolean).forEach((item) => disposables.add(item));
  };

  const makeParticleGeometry = () => {
    const count = 120;
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    for (let index = 0; index < count; index += 1) {
      const offset = index * 3;
      positions[offset] = (Math.random() - 0.5) * 24;
      positions[offset + 1] = (Math.random() - 0.5) * 15;
      positions[offset + 2] = (Math.random() - 0.5) * 12;
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    registerDisposable(geometry);
    return geometry;
  };

  const updateParticleColors = (theme) => {
    if (!particleGeometry) return;
    const darkPalette = [0x8e7dff, 0x49d7ff, 0xff78b5];
    const lightPalette = [0x9588dd, 0x62b8d0, 0xd991b5];
    const palette = theme === "dark" ? darkPalette : lightPalette;
    const color = new THREE.Color();
    const colors = particleGeometry.getAttribute("color");
    for (let index = 0; index < colors.count; index += 1) {
      color.setHex(palette[index % palette.length]);
      colors.setXYZ(index, color.r, color.g, color.b);
    }
    colors.needsUpdate = true;
  };

  const createWorkflowGroup = () => {
    const group = new THREE.Group();
    group.position.set(-3.4, 0.25, -1.8);

    const coreGeometry = new THREE.IcosahedronGeometry(1.15, 0);
    const coreMaterial = new THREE.MeshPhongMaterial({
      color: 0x8872ff,
      emissive: 0x241d62,
      transparent: true,
      opacity: 0.22,
      flatShading: true,
      shininess: 80,
      depthWrite: false,
    });
    const core = new THREE.Mesh(coreGeometry, coreMaterial);
    core.rotation.set(0.35, 0.4, 0.15);
    group.add(core);

    const edgeMaterial = new THREE.MeshBasicMaterial({
      color: 0xb8afff,
      wireframe: true,
      transparent: true,
      opacity: 0.32,
    });
    const edges = new THREE.Mesh(coreGeometry, edgeMaterial);
    edges.scale.setScalar(1.015);
    group.add(edges);

    const ringGeometry = new THREE.TorusGeometry(2.5, 0.018, 3, 56);
    const ringMaterial = new THREE.MeshBasicMaterial({
      color: 0x55d8ff,
      transparent: true,
      opacity: 0.22,
      depthWrite: false,
    });
    const ring = new THREE.Mesh(ringGeometry, ringMaterial);
    ring.rotation.set(1.12, 0.15, 0.18);
    group.add(ring);

    const nodeGeometry = new THREE.OctahedronGeometry(0.22, 0);
    const nodeMaterial = new THREE.MeshPhongMaterial({
      color: 0x69dcff,
      emissive: 0x153849,
      transparent: true,
      opacity: 0.72,
      flatShading: true,
      depthWrite: false,
    });
    const nodePositions = [
      new THREE.Vector3(2.35, 0.45, 0.25),
      new THREE.Vector3(-1.35, 1.9, -0.15),
      new THREE.Vector3(-1.75, -1.55, 0.35),
    ];
    workflowNodes = nodePositions.map((position, index) => {
      const node = new THREE.Mesh(nodeGeometry, nodeMaterial);
      node.position.copy(position);
      node.userData.phase = index * 2.1;
      group.add(node);
      return node;
    });

    const connectionPositions = new Float32Array(nodePositions.length * 6);
    nodePositions.forEach((position, index) => {
      const offset = index * 6;
      connectionPositions.set([0, 0, 0, position.x, position.y, position.z], offset);
    });
    const connectionGeometry = new THREE.BufferGeometry();
    connectionGeometry.setAttribute(
      "position",
      new THREE.BufferAttribute(connectionPositions, 3),
    );
    const connectionMaterial = new THREE.LineBasicMaterial({
      color: 0xa89dff,
      transparent: true,
      opacity: 0.2,
      depthWrite: false,
    });
    group.add(new THREE.LineSegments(connectionGeometry, connectionMaterial));

    registerDisposable(
      coreGeometry,
      coreMaterial,
      edgeMaterial,
      ringGeometry,
      ringMaterial,
      nodeGeometry,
      nodeMaterial,
      connectionGeometry,
      connectionMaterial,
    );

    workflowCore = core;
    return group;
  };

  const updateTheme = (theme) => {
    currentTheme = theme === "dark" ? "dark" : "light";
    if (!scene) return;
    updateParticleColors(currentTheme);
    scene.fog.color.set(currentTheme === "dark" ? 0x10162c : 0xf2f4ff);
    scene.fog.density = currentTheme === "dark" ? 0.035 : 0.052;
    particleMaterial.opacity = currentTheme === "dark" ? 0.56 : 0.24;

    const coreMaterial = workflowCore?.material;
    if (coreMaterial) {
      coreMaterial.color.set(currentTheme === "dark" ? 0x8872ff : 0x8f86c9);
      coreMaterial.emissive.set(currentTheme === "dark" ? 0x241d62 : 0x2d2948);
      coreMaterial.opacity = currentTheme === "dark" ? 0.22 : 0.12;
    }
    workflowGroup.visible = currentTheme === "dark" || quality() === "full";
    if (!document.hidden && !drawerOpen) renderFrame(performance.now(), false);
  };

  const updateDrawRange = () => {
    if (!particleGeometry) return;
    const reduced = mobileViewport.matches || coarsePointer.matches || quality() !== "full";
    particleGeometry.setDrawRange(0, reduced ? 50 : 120);
    if (workflowGroup) {
      workflowGroup.scale.setScalar(reduced ? 0.82 : 1);
    }
  };

  const resize = () => {
    resizeFrame = 0;
    if (!renderer || !camera || !canvas || destroyed) return;
    const rect = canvas.getBoundingClientRect();
    const width = Math.max(1, Math.round(rect.width || window.innerWidth));
    const height = Math.max(1, Math.round(rect.height || window.innerHeight));
    const dprCap = mobileViewport.matches || coarsePointer.matches ? 1.25 : 1.5;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, dprCap));
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    updateDrawRange();
    if (!document.hidden && !drawerOpen) renderFrame(performance.now(), false);
  };

  const queueResize = () => {
    if (resizeFrame || destroyed) return;
    resizeFrame = requestAnimationFrame(resize);
  };

  const renderFrame = (now, animate = true) => {
    if (!renderer || !scene || !camera || contextLost || destroyed) return;
    const elapsed = now * 0.001;
    const delta = lastFrame ? Math.min((now - lastFrame) / 1000, 0.05) : 0;
    lastFrame = now;

    if (animate) {
      const speed = quality() === "reduced" ? 0.34 : 1;
      pointerX += (targetPointerX - pointerX) * 0.035;
      pointerY += (targetPointerY - pointerY) * 0.035;
      particles.rotation.y += delta * 0.012 * speed;
      particles.rotation.x = Math.sin(elapsed * 0.07) * 0.035;
      workflowGroup.rotation.y += delta * 0.075 * speed;
      workflowGroup.rotation.x = Math.sin(elapsed * 0.18) * 0.08;
      workflowCore.rotation.y += delta * 0.11 * speed;
      workflowNodes.forEach((node) => {
        node.rotation.x += delta * 0.16 * speed;
        node.rotation.y += delta * 0.13 * speed;
        node.scale.setScalar(1 + Math.sin(elapsed * 0.7 + node.userData.phase) * 0.08);
      });
      camera.position.x += (pointerX * 0.42 - camera.position.x) * 0.028;
      camera.position.y += (pointerY * 0.28 - camera.position.y) * 0.028;
      camera.lookAt(0, 0, 0);
    }
    renderer.render(scene, camera);
  };

  const stopLoop = () => {
    cancelAnimationFrame(animationFrame);
    animationFrame = 0;
  };

  const tick = (now) => {
    animationFrame = 0;
    if (!shouldAnimate()) return;
    renderFrame(now, true);
    animationFrame = requestAnimationFrame(tick);
  };

  const startLoop = () => {
    stopLoop();
    lastFrame = 0;
    if (shouldAnimate()) {
      animationFrame = requestAnimationFrame(tick);
    } else if (
      mounted
      && !destroyed
      && !contextLost
      && !document.hidden
      && !drawerOpen
    ) {
      renderFrame(performance.now(), false);
    }
  };

  const destroy = () => {
    if (destroyed) return;
    destroyed = true;
    mounted = false;
    stopLoop();
    cancelAnimationFrame(resizeFrame);
    resizeObserver?.disconnect();
    listeners.splice(0).forEach((remove) => remove());
    scene?.traverse((object) => {
      if (object.geometry) disposables.add(object.geometry);
      if (Array.isArray(object.material)) {
        object.material.forEach((material) => disposables.add(material));
      } else if (object.material) {
        disposables.add(object.material);
      }
    });
    disposables.forEach((item) => item.dispose?.());
    disposables.clear();
    renderer?.renderLists?.dispose?.();
    renderer?.dispose();
    renderer?.forceContextLoss?.();
    renderer = null;
    scene = null;
    camera = null;
    setFallback(true);
  };

  const mount = () => {
    if (mounted || destroyed || !canvas || !THREE) {
      if (canvas && !THREE) setFallback(true);
      return false;
    }

    const contextOptions = {
      alpha: true,
      antialias: false,
      depth: true,
      stencil: false,
      powerPreference: "low-power",
      premultipliedAlpha: true,
    };
    let context = null;
    try {
      context = canvas.getContext("webgl2", contextOptions)
        || canvas.getContext("webgl", contextOptions)
        || canvas.getContext("experimental-webgl", contextOptions);
      if (!context) {
        setFallback(true);
        return false;
      }
      renderer = new THREE.WebGLRenderer({
        ...contextOptions,
        canvas,
        context,
      });
    } catch {
      context?.getExtension?.("WEBGL_lose_context")?.loseContext?.();
      setFallback(true);
      return false;
    }

    setFallback(false);
    canvas.setAttribute("aria-hidden", "true");
    canvas.setAttribute("role", "presentation");
    renderer.setClearColor(0x000000, 0);
    if ("outputColorSpace" in renderer && THREE.SRGBColorSpace) {
      renderer.outputColorSpace = THREE.SRGBColorSpace;
    } else if (THREE.sRGBEncoding) {
      renderer.outputEncoding = THREE.sRGBEncoding;
    }

    scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x10162c, 0.035);
    camera = new THREE.PerspectiveCamera(48, 1, 0.1, 60);
    camera.position.set(0, 0, 12);

    particleGeometry = makeParticleGeometry();
    particleMaterial = new THREE.PointsMaterial({
      size: 0.055,
      sizeAttenuation: true,
      transparent: true,
      opacity: 0.56,
      vertexColors: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    registerDisposable(particleMaterial);
    particles = new THREE.Points(particleGeometry, particleMaterial);
    scene.add(particles);

    workflowGroup = createWorkflowGroup();
    scene.add(workflowGroup);
    scene.add(new THREE.AmbientLight(0xffffff, 0.46));
    const keyLight = new THREE.DirectionalLight(0xaedfff, 0.7);
    keyLight.position.set(4, 5, 7);
    scene.add(keyLight);

    const onPointerMove = (event) => {
      if (coarsePointer.matches || quality() === "static") return;
      targetPointerX = Math.max(-1, Math.min(1, (event.clientX / window.innerWidth - 0.5) * 2));
      targetPointerY = Math.max(-1, Math.min(1, (0.5 - event.clientY / window.innerHeight) * 2));
    };
    const onVisibility = () => startLoop();
    const onDrawer = (event) => {
      drawerOpen = Boolean(event.detail?.open);
      startLoop();
    };
    const onTheme = (event) => updateTheme(event.detail?.theme);
    const onMotion = () => {
      updateDrawRange();
      if (workflowGroup) workflowGroup.visible = currentTheme === "dark" || quality() === "full";
      startLoop();
    };
    const onContextLost = (event) => {
      event.preventDefault();
      contextLost = true;
      stopLoop();
      setFallback(true);
    };
    const onContextRestored = () => {
      contextLost = false;
      setFallback(false);
      queueResize();
      startLoop();
    };
    const onPageHide = (event) => {
      if (event.persisted) {
        stopLoop();
      } else {
        destroy();
      }
    };
    const onPageShow = (event) => {
      if (event.persisted) startLoop();
    };

    addListener(window, "pointermove", onPointerMove, { passive: true });
    addListener(document, "visibilitychange", onVisibility);
    addListener(document, "taskflow:drawerchange", onDrawer);
    addListener(document, "taskflow:themechange", onTheme);
    addListener(document, "taskflow:motionchange", onMotion);
    addListener(coarsePointer, "change", queueResize);
    addListener(mobileViewport, "change", queueResize);
    addListener(canvas, "webglcontextlost", onContextLost, false);
    addListener(canvas, "webglcontextrestored", onContextRestored, false);
    addListener(window, "pagehide", onPageHide);
    addListener(window, "pageshow", onPageShow);

    if ("ResizeObserver" in window) {
      resizeObserver = new ResizeObserver(queueResize);
      resizeObserver.observe(canvas);
    } else {
      addListener(window, "resize", queueResize, { passive: true });
    }

    mounted = true;
    updateTheme(currentTheme);
    resize();
    startLoop();
    return true;
  };

  TaskFlow.threeBackground = {
    taskflowThreeBackground: true,
    get mounted() {
      return mounted;
    },
    mount,
    pause: stopLoop,
    resume: startLoop,
    destroy,
    updateTheme,
  };

  mount();
})();
