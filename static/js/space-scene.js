(() => {
  "use strict";

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const coarsePointer = window.matchMedia("(pointer: coarse)").matches;

  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

  function createShader(gl, type, source) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);

    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      const error = gl.getShaderInfoLog(shader);
      gl.deleteShader(shader);
      throw new Error(`TaskFlow shader error: ${error}`);
    }

    return shader;
  }

  function createProgram(gl, vertexSource, fragmentSource) {
    const program = gl.createProgram();
    const vertexShader = createShader(gl, gl.VERTEX_SHADER, vertexSource);
    const fragmentShader = createShader(gl, gl.FRAGMENT_SHADER, fragmentSource);

    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);

    gl.deleteShader(vertexShader);
    gl.deleteShader(fragmentShader);

    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      const error = gl.getProgramInfoLog(program);
      gl.deleteProgram(program);
      throw new Error(`TaskFlow program error: ${error}`);
    }

    return program;
  }

  function makeParticleData(count, spread = 8) {
    const stride = 9;
    const data = new Float32Array(count * stride);

    for (let index = 0; index < count; index += 1) {
      const offset = index * stride;
      const palette = Math.random();

      data[offset] = (Math.random() - 0.5) * spread;
      data[offset + 1] = (Math.random() - 0.5) * spread;
      data[offset + 2] = Math.random() * 18 + 1;
      data[offset + 3] = Math.random() * 1.8 + 0.65;
      data[offset + 4] = Math.random() * 1.2 + 0.45;
      data[offset + 5] = Math.random() * Math.PI * 2;

      if (palette < 0.34) {
        data[offset + 6] = 0.52;
        data[offset + 7] = 0.42;
        data[offset + 8] = 1.0;
      } else if (palette < 0.68) {
        data[offset + 6] = 0.18;
        data[offset + 7] = 0.82;
        data[offset + 8] = 1.0;
      } else {
        data[offset + 6] = 1.0;
        data[offset + 7] = 0.44;
        data[offset + 8] = 0.76;
      }
    }

    return { data, stride };
  }

  function mountWebGL(canvas, options) {
    const gl = canvas.getContext("webgl", {
      alpha: true,
      antialias: false,
      depth: false,
      premultipliedAlpha: false,
      powerPreference: coarsePointer ? "low-power" : "high-performance",
    });

    if (!gl) {
      throw new Error("WebGL is unavailable");
    }

    const vertexSource = `
      precision highp float;

      attribute vec3 a_position;
      attribute float a_size;
      attribute float a_speed;
      attribute float a_phase;
      attribute vec3 a_color;

      uniform float u_time;
      uniform float u_aspect;
      uniform vec2 u_pointer;
      uniform float u_speed;
      uniform float u_point_scale;

      varying vec3 v_color;
      varying float v_alpha;

      void main() {
        float depth = 19.0;
        float z = mod(a_position.z - (u_time * a_speed * u_speed), depth) + 0.85;
        float angle = (u_time * 0.035) + a_phase;
        float ca = cos(angle);
        float sa = sin(angle);

        vec2 rotated = vec2(
          a_position.x * ca - a_position.y * sa,
          a_position.x * sa + a_position.y * ca
        );

        rotated += u_pointer * (0.18 + z * 0.018);

        float perspective = 1.55 / z;
        vec2 projected = rotated * perspective;
        projected.x /= u_aspect;

        gl_Position = vec4(projected, 0.0, 1.0);
        gl_PointSize = clamp(a_size * u_point_scale / z, 1.0, 12.0);

        v_color = a_color;
        v_alpha = (1.0 - smoothstep(2.0, 19.0, z)) * 0.92;
      }
    `;

    const fragmentSource = `
      precision mediump float;

      varying vec3 v_color;
      varying float v_alpha;

      void main() {
        vec2 center = gl_PointCoord - vec2(0.5);
        float distanceToCenter = length(center);

        if (distanceToCenter > 0.5) {
          discard;
        }

        float core = smoothstep(0.22, 0.0, distanceToCenter);
        float glow = smoothstep(0.5, 0.0, distanceToCenter);
        float alpha = (glow * 0.42 + core * 0.78) * v_alpha;

        gl_FragColor = vec4(v_color + core * 0.35, alpha);
      }
    `;

    const program = createProgram(gl, vertexSource, fragmentSource);
    const count = options.count;
    const { data, stride } = makeParticleData(count, options.spread);

    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);

    const bytes = Float32Array.BYTES_PER_ELEMENT;
    const attributes = [
      ["a_position", 3, 0],
      ["a_size", 1, 3],
      ["a_speed", 1, 4],
      ["a_phase", 1, 5],
      ["a_color", 3, 6],
    ];

    attributes.forEach(([name, size, offset]) => {
      const location = gl.getAttribLocation(program, name);
      gl.enableVertexAttribArray(location);
      gl.vertexAttribPointer(
        location,
        size,
        gl.FLOAT,
        false,
        stride * bytes,
        offset * bytes,
      );
    });

    const uniforms = {
      time: gl.getUniformLocation(program, "u_time"),
      aspect: gl.getUniformLocation(program, "u_aspect"),
      pointer: gl.getUniformLocation(program, "u_pointer"),
      speed: gl.getUniformLocation(program, "u_speed"),
      pointScale: gl.getUniformLocation(program, "u_point_scale"),
    };

    const state = {
      width: 1,
      height: 1,
      dpr: 1,
      raf: 0,
      start: performance.now(),
      pointerX: 0,
      pointerY: 0,
      targetX: 0,
      targetY: 0,
      visible: true,
    };

    gl.useProgram(program);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE);
    gl.disable(gl.DEPTH_TEST);

    function resize() {
      const rect = canvas.getBoundingClientRect();
      state.width = Math.max(1, rect.width || window.innerWidth);
      state.height = Math.max(1, rect.height || window.innerHeight);
      state.dpr = Math.min(
        window.devicePixelRatio || 1,
        options.maxDpr,
      );

      const pixelWidth = Math.round(state.width * state.dpr);
      const pixelHeight = Math.round(state.height * state.dpr);

      if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
        canvas.width = pixelWidth;
        canvas.height = pixelHeight;
      }

      gl.viewport(0, 0, pixelWidth, pixelHeight);
    }

    function render(now) {
      if (!state.visible) return;

      state.pointerX += (state.targetX - state.pointerX) * 0.035;
      state.pointerY += (state.targetY - state.pointerY) * 0.035;

      const elapsed = (now - state.start) / 1000;
      const aspect = state.width / Math.max(1, state.height);

      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);

      gl.useProgram(program);
      gl.uniform1f(uniforms.time, elapsed);
      gl.uniform1f(uniforms.aspect, aspect);
      gl.uniform2f(uniforms.pointer, state.pointerX, state.pointerY);
      gl.uniform1f(uniforms.speed, options.speed);
      gl.uniform1f(uniforms.pointScale, options.pointScale * state.dpr);
      gl.drawArrays(gl.POINTS, 0, count);

      state.raf = requestAnimationFrame(render);
    }

    function onPointerMove(event) {
      state.targetX = clamp((event.clientX / state.width - 0.5) * 2, -1, 1);
      state.targetY = clamp((0.5 - event.clientY / state.height) * 2, -1, 1);
    }

    function onVisibilityChange() {
      state.visible = !document.hidden;

      if (state.visible) {
        state.start = performance.now();
        cancelAnimationFrame(state.raf);
        state.raf = requestAnimationFrame(render);
      } else {
        cancelAnimationFrame(state.raf);
      }
    }

    const resizeObserver = "ResizeObserver" in window
      ? new ResizeObserver(resize)
      : null;

    if (resizeObserver) {
      resizeObserver.observe(canvas);
    } else {
      window.addEventListener("resize", resize, { passive: true });
    }

    window.addEventListener("pointermove", onPointerMove, { passive: true });
    document.addEventListener("visibilitychange", onVisibilityChange);

    resize();
    state.raf = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(state.raf);
      resizeObserver?.disconnect();
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", onPointerMove);
      document.removeEventListener("visibilitychange", onVisibilityChange);
      gl.deleteBuffer(buffer);
      gl.deleteProgram(program);
    };
  }

  function mountCanvasFallback(canvas, options) {
    const ctx = canvas.getContext("2d", { alpha: true });
    const state = {
      width: 1,
      height: 1,
      dpr: 1,
      raf: 0,
      last: performance.now(),
      pointerX: 0,
      pointerY: 0,
      targetX: 0,
      targetY: 0,
      particles: [],
    };

    function makeParticle(resetDepth = false) {
      return {
        x: (Math.random() - 0.5) * 1600,
        y: (Math.random() - 0.5) * 1100,
        z: resetDepth ? 1700 : Math.random() * 1600 + 80,
        size: Math.random() * 1.8 + 0.4,
        speed: Math.random() * 34 + 18,
        color: Math.random() > 0.5 ? "129,104,255" : "57,214,255",
      };
    }

    function resize() {
      const rect = canvas.getBoundingClientRect();
      state.width = Math.max(1, rect.width || window.innerWidth);
      state.height = Math.max(1, rect.height || window.innerHeight);
      state.dpr = Math.min(window.devicePixelRatio || 1, options.maxDpr);

      canvas.width = Math.round(state.width * state.dpr);
      canvas.height = Math.round(state.height * state.dpr);
      ctx.setTransform(state.dpr, 0, 0, state.dpr, 0, 0);

      state.particles = Array.from(
        { length: Math.min(options.count, 150) },
        () => makeParticle(false),
      );
    }

    function render(now) {
      const delta = Math.min((now - state.last) / 1000, 0.04);
      state.last = now;

      state.pointerX += (state.targetX - state.pointerX) * 0.04;
      state.pointerY += (state.targetY - state.pointerY) * 0.04;

      ctx.clearRect(0, 0, state.width, state.height);

      for (const particle of state.particles) {
        particle.z -= particle.speed * delta * options.speed;

        if (particle.z < 60) {
          Object.assign(particle, makeParticle(true));
        }

        const focal = Math.min(state.width, state.height) * 0.86;
        const scale = focal / particle.z;
        const x = state.width / 2 + (particle.x + state.pointerX * particle.z * 0.04) * scale;
        const y = state.height / 2 + (particle.y + state.pointerY * particle.z * 0.03) * scale;

        if (x < -20 || x > state.width + 20 || y < -20 || y > state.height + 20) {
          continue;
        }

        const radius = Math.max(0.5, particle.size * scale * 3);
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${particle.color},${Math.min(0.9, scale * 1.6)})`;
        ctx.shadowColor = `rgba(${particle.color},0.85)`;
        ctx.shadowBlur = radius * 8;
        ctx.fill();
      }

      ctx.shadowBlur = 0;
      state.raf = requestAnimationFrame(render);
    }

    function onPointerMove(event) {
      state.targetX = clamp((event.clientX / state.width - 0.5) * 2, -1, 1);
      state.targetY = clamp((0.5 - event.clientY / state.height) * 2, -1, 1);
    }

    const resizeObserver = "ResizeObserver" in window
      ? new ResizeObserver(resize)
      : null;

    if (resizeObserver) {
      resizeObserver.observe(canvas);
    } else {
      window.addEventListener("resize", resize, { passive: true });
    }

    window.addEventListener("pointermove", onPointerMove, { passive: true });

    resize();
    state.raf = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(state.raf);
      resizeObserver?.disconnect();
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", onPointerMove);
    };
  }

  function mount(canvas, customOptions = {}) {
    if (!canvas || canvas.dataset.spaceMounted === "1" || reduceMotion) {
      return () => {};
    }

    canvas.dataset.spaceMounted = "1";

    const mobile = window.matchMedia("(max-width: 720px)").matches;
    const options = {
      count: mobile ? 120 : 260,
      spread: mobile ? 6.5 : 9.5,
      speed: 1,
      pointScale: mobile ? 17 : 21,
      maxDpr: coarsePointer ? 1.25 : 1.7,
      ...customOptions,
    };

    try {
      return mountWebGL(canvas, options);
    } catch (error) {
      console.warn("TaskFlow WebGL scene switched to Canvas fallback.", error);
      return mountCanvasFallback(canvas, options);
    }
  }

  window.TaskFlowSpaceScene = Object.freeze({ mount });
})();
