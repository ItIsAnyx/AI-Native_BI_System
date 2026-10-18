import { useEffect, useRef } from "react";

const SPACING = 26;
// На каком расстоянии от поля ввода (в px) курсор уже подсвечивает его.
const FIELD_REACH = 24;

// Цвет точек сетки и «облака» фона для каждой темы.
const SCENES = {
  light: {
    dot: [79, 70, 229],
    blobs: [
      { x: 0.15, y: 0.2, r: 620, baseHue: 285, hueRange: 18, hueSpeed: 0.08, driftX: 0.06, driftY: 0.05, pulse: 0.1, phase: 0, alpha: 0.13, sat: 75, lit: 64 },
      { x: 0.85, y: 0.25, r: 540, baseHue: 310, hueRange: 20, hueSpeed: -0.07, driftX: 0.05, driftY: 0.07, pulse: 0.12, phase: 1.5, alpha: 0.14, sat: 73, lit: 66 },
      { x: 0.5, y: 0.8, r: 680, baseHue: 295, hueRange: 12, hueSpeed: 0.1, driftX: 0.05, driftY: 0.06, pulse: 0.08, phase: 3, alpha: 0.14, sat: 74, lit: 65 },
      { x: 0.1, y: 0.65, r: 520, baseHue: 315, hueRange: 18, hueSpeed: -0.09, driftX: 0.07, driftY: 0.05, pulse: 0.13, phase: 4.5, alpha: 0.12, sat: 78, lit: 64 },
    ],
  },
  dark: {
    dot: [196, 181, 253],
    blobs: [
      { x: 0.15, y: 0.2, r: 660, baseHue: 285, hueRange: 18, hueSpeed: 0.09, driftX: 0.06, driftY: 0.05, pulse: 0.1, phase: 0, alpha: 0.16, sat: 78, lit: 58 },
      { x: 0.85, y: 0.25, r: 580, baseHue: 310, hueRange: 20, hueSpeed: -0.08, driftX: 0.05, driftY: 0.07, pulse: 0.12, phase: 1.5, alpha: 0.14, sat: 76, lit: 60 },
      { x: 0.5, y: 0.8, r: 720, baseHue: 295, hueRange: 12, hueSpeed: 0.1, driftX: 0.05, driftY: 0.06, pulse: 0.08, phase: 3, alpha: 0.15, sat: 76, lit: 58 },
      { x: 0.1, y: 0.65, r: 540, baseHue: 315, hueRange: 18, hueSpeed: -0.1, driftX: 0.07, driftY: 0.05, pulse: 0.13, phase: 4.5, alpha: 0.13, sat: 80, lit: 58 },
    ],
  },
};

/**
 * Анимированная сцена страниц входа и регистрации:
 *  - переливающиеся цветные «облака» (canvas .bg-blobs);
 *  - сетка точек, притягивающихся к курсору (canvas .bg-grid);
 *  - свечение рамки карточки под курсором, лёгкое притяжение карточки и кнопки;
 *  - подсветка поля ввода, рядом с которым находится курсор.
 *
 * Тема читается из ref на каждом кадре, поэтому её смена не перезапускает анимацию.
 */
export function useAuthScene({ containerRef, cardRef, blobsRef, gridRef, theme }) {
  const themeRef = useRef(theme);
  useEffect(() => {
    themeRef.current = theme;
  }, [theme]);

  useEffect(() => {
    const container = containerRef.current;
    const card = cardRef.current;
    const blobsCanvas = blobsRef.current;
    const gridCanvas = gridRef.current;
    if (!container || !card || !blobsCanvas || !gridCanvas) return undefined;
    const blobsCtx = blobsCanvas.getContext("2d");
    const gridCtx = gridCanvas.getContext("2d");
    if (!blobsCtx || !gridCtx) return undefined;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const startTime = performance.now();
    const mouse = { x: -2000, y: -2000, tx: -2000, ty: -2000 };
    let W = 0;
    let H = 0;
    let dots = [];
    let frame = 0;

    const blobsOf = () => (SCENES[themeRef.current] ?? SCENES.light).blobs;
    const pos = (b, t) => ({
      x: (b.x + Math.sin(t * b.driftX + b.phase) * 0.09) * W,
      y: (b.y + Math.cos(t * b.driftY + b.phase) * 0.09) * H,
      r: b.r * (1 + Math.sin(t * b.pulse + b.phase) * 0.1),
    });

    function drawBlobs(t) {
      blobsCtx.clearRect(0, 0, W, H);
      for (const b of blobsOf()) {
        const { x, y, r } = pos(b, t);
        const hue = b.baseHue + Math.sin(t * b.hueSpeed + b.phase) * b.hueRange;
        const color = (a) => `hsla(${hue}, ${b.sat}%, ${b.lit}%, ${a})`;
        const gradient = blobsCtx.createRadialGradient(x, y, 0, x, y, Math.max(1, r));
        gradient.addColorStop(0, color(b.alpha));
        gradient.addColorStop(0.45, color(b.alpha * 0.5));
        gradient.addColorStop(1, color(0));
        blobsCtx.fillStyle = gradient;
        blobsCtx.beginPath();
        blobsCtx.arc(x, y, Math.max(1, r), 0, Math.PI * 2);
        blobsCtx.fill();
      }
    }

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      W = container.clientWidth;
      H = container.clientHeight;
      for (const [canvas, ctx] of [
        [blobsCanvas, blobsCtx],
        [gridCanvas, gridCtx],
      ]) {
        canvas.width = Math.max(1, Math.round(W * dpr));
        canvas.height = Math.max(1, Math.round(H * dpr));
        canvas.style.width = `${W}px`;
        canvas.style.height = `${H}px`;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      }
      dots = [];
      for (let y = SPACING / 2; y < H; y += SPACING) {
        for (let x = SPACING / 2; x < W; x += SPACING) {
          dots.push({ ox: x, oy: y, x, y });
        }
      }
      if (reduceMotion) drawBlobs((performance.now() - startTime) / 1000);
    }

    function tick() {
      const t = (performance.now() - startTime) / 1000;
      mouse.x += (mouse.tx - mouse.x) * 0.18;
      mouse.y += (mouse.ty - mouse.y) * 0.18;

      drawBlobs(t);

      // Положение облаков считаем один раз за кадр, а не для каждой точки.
      const live = blobsOf().map((b) => {
        const p = pos(b, t);
        const sigma = p.r * 0.35 + 30;
        return { ...p, alpha: b.alpha, k: 1 / (2 * sigma * sigma) };
      });
      const [dr, dg, db] = (SCENES[themeRef.current] ?? SCENES.light).dot;

      gridCtx.clearRect(0, 0, W, H);
      const R = 150;
      for (const d of dots) {
        const dx = mouse.x - d.ox;
        const dy = mouse.y - d.oy;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < R && dist > 0.1) {
          const pull = (1 - dist / R) * 11;
          d.x = d.ox + (dx / dist) * pull;
          d.y = d.oy + (dy / dist) * pull;
        } else {
          d.x += (d.ox - d.x) * 0.2;
          d.y += (d.oy - d.y) * 0.2;
        }
        const intensity = Math.max(0, 1 - dist / R);
        let r = 0.5 + intensity * 1.5;
        let alpha = 0.18 + intensity * 0.45;

        // Влияние облаков на точку: чем ближе облако, тем крупнее и ярче точка.
        let influence = 0;
        for (const b of live) {
          const bx = d.x - b.x;
          const by = d.y - b.y;
          const a = b.alpha * Math.exp(-(bx * bx + by * by) * b.k);
          if (a >= 0.005) influence += a;
        }
        if (influence >= 0.01) {
          const highlight = Math.min(1, Math.min(1, influence) * 4);
          const phase = d.ox * 0.08 + d.oy * 0.08;
          const pulse = 1 + Math.sin(t * 1.6 + phase) * 0.3 * highlight;
          r = (r + highlight * 3) * pulse;
          alpha = Math.min(1, alpha + highlight * 0.7);
        }

        gridCtx.beginPath();
        gridCtx.arc(d.x, d.y, r, 0, Math.PI * 2);
        gridCtx.fillStyle = `rgba(${dr},${dg},${db},${alpha})`;
        gridCtx.fill();
      }

      // Сначала читаем геометрию, потом пишем стили, чтобы не провоцировать лишние пересчёты layout.
      const containerRect = container.getBoundingClientRect();
      const cardRect = card.getBoundingClientRect();
      const fields = Array.from(card.querySelectorAll(".field"));
      // Подсветка считается по самому полю ввода, а не по всему блоку (подпись, подсказка, ошибка):
      // иначе у соседних полей зоны перекрываются.
      const fieldRects = fields.map((f) => (f.querySelector(".input-wrap") ?? f).getBoundingClientRect());

      const cardLeft = cardRect.left - containerRect.left;
      const cardTop = cardRect.top - containerRect.top;
      const inside = mouse.tx > -1000;
      card.style.setProperty(
        "--cursor-x",
        inside ? `${Math.max(-20, Math.min(cardRect.width + 20, mouse.x - cardLeft))}px` : "-1000px",
      );
      card.style.setProperty(
        "--cursor-y",
        inside ? `${Math.max(-20, Math.min(cardRect.height + 20, mouse.y - cardTop))}px` : "-1000px",
      );

      // Карточка слегка тянется к курсору. Смещение считаем от положения карточки без сдвига.
      const curShiftX = parseFloat(card.dataset.sx || "0");
      const curShiftY = parseFloat(card.dataset.sy || "0");
      const cx = cardLeft - curShiftX + cardRect.width / 2;
      const cy = cardTop - curShiftY + cardRect.height / 2;
      const cdx = mouse.x - cx;
      const cdy = mouse.y - cy;
      const cdist = Math.sqrt(cdx * cdx + cdy * cdy);
      const proximity = Math.max(0, 1 - cdist / 280);
      const sx = (cdx / Math.max(1, cdist)) * 3 * proximity;
      const sy = (cdy / Math.max(1, cdist)) * 3 * proximity;
      card.dataset.sx = String(sx);
      card.dataset.sy = String(sy);
      card.style.transform = `translate(${sx}px, ${sy}px)`;

      // Подсвечивается только одно поле: ближайшее к курсору, и только если курсор над ним
      // или не дальше FIELD_REACH от его края.
      let nearest = -1;
      let nearestDist = FIELD_REACH;
      fieldRects.forEach((fr, i) => {
        const fdx = Math.max(fr.left - containerRect.left - mouse.x, 0, mouse.x - (fr.right - containerRect.left));
        const fdy = Math.max(fr.top - containerRect.top - mouse.y, 0, mouse.y - (fr.bottom - containerRect.top));
        const dist = Math.hypot(fdx, fdy);
        if (dist < nearestDist) {
          nearestDist = dist;
          nearest = i;
        }
      });
      fields.forEach((field, i) => field.classList.toggle("active", i === nearest));

      frame = requestAnimationFrame(tick);
    }

    const setPointer = (event, snap) => {
      const point = event.touches ? event.touches[0] : event;
      if (!point) return;
      const rect = container.getBoundingClientRect();
      mouse.tx = point.clientX - rect.left;
      mouse.ty = point.clientY - rect.top;
      if (snap) {
        mouse.x = mouse.tx;
        mouse.y = mouse.ty;
      }
    };
    const onMove = (e) => setPointer(e, false);
    const onTouchStart = (e) => setPointer(e, true);
    const onLeave = () => {
      mouse.tx = -2000;
      mouse.ty = -2000;
    };

    const observer = new ResizeObserver(resize);
    observer.observe(container);
    resize();

    if (!reduceMotion) {
      container.addEventListener("mousemove", onMove);
      container.addEventListener("mouseleave", onLeave);
      container.addEventListener("touchstart", onTouchStart, { passive: true });
      container.addEventListener("touchmove", onMove, { passive: true });
      frame = requestAnimationFrame(tick);
    }

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      container.removeEventListener("mousemove", onMove);
      container.removeEventListener("mouseleave", onLeave);
      container.removeEventListener("touchstart", onTouchStart);
      container.removeEventListener("touchmove", onMove);
      card.style.transform = "";
      delete card.dataset.sx;
      delete card.dataset.sy;
    };
  }, [containerRef, cardRef, blobsRef, gridRef]);
}
