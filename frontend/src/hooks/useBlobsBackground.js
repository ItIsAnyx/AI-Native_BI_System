import { useEffect, useRef } from "react";
import { SCENES } from "./useAuthScene";

/**
 * Переливающиеся цветные «облака» на фоне рабочего пространства (canvas на весь экран).
 * Тема читается из ref на каждом кадре, поэтому смена темы не перезапускает анимацию.
 * При prefers-reduced-motion рисуется один статичный кадр.
 */
export function useBlobsBackground(canvasRef, theme) {
  const themeRef = useRef(theme);
  useEffect(() => {
    themeRef.current = theme;
  }, [theme]);


  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return undefined;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const start = performance.now();
    let W = 0;
    let H = 0;
    let frame = 0;

    function draw() {
      const t = (performance.now() - start) / 1000;
      ctx.clearRect(0, 0, W, H);
      for (const b of (SCENES[themeRef.current] ?? SCENES.light).blobs) {
        const x = (b.x + Math.sin(t * b.driftX + b.phase) * 0.09) * W;
        const y = (b.y + Math.cos(t * b.driftY + b.phase) * 0.09) * H;
        const r = Math.max(1, b.r * (1 + Math.sin(t * b.pulse + b.phase) * 0.1));
        const hue = b.baseHue + Math.sin(t * b.hueSpeed + b.phase) * b.hueRange;
        const color = (a) => `hsla(${hue}, ${b.sat}%, ${b.lit}%, ${a})`;
        const gradient = ctx.createRadialGradient(x, y, 0, x, y, r);
        gradient.addColorStop(0, color(b.alpha));
        gradient.addColorStop(0.45, color(b.alpha * 0.5));
        gradient.addColorStop(1, color(0));
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      W = window.innerWidth;
      H = window.innerHeight;
      canvas.width = Math.max(1, Math.round(W * dpr));
      canvas.height = Math.max(1, Math.round(H * dpr));
      canvas.style.width = `${W}px`;
      canvas.style.height = `${H}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      draw();
    }
    function tick() {
      draw();
      frame = requestAnimationFrame(tick);
    }
    window.addEventListener("resize", resize);
    resize();
    if (!reduceMotion) frame = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
    };
  }, [canvasRef]);
}
