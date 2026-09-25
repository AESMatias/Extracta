"use client";

import clsx from "clsx";
import { useEffect, useRef } from "react";

// Two colors only, for a consistent look: the brand's green-teal and blue.
const PALETTE = ["16 185 129", "47 111 237"];

interface Ember {
  x: number;
  y: number;
  z: number; // depth 0 (far: small, sharp, slow) to 1 (near: big, soft, faster)
  vx: number;
  rise: number; // upward speed
  sway: number; // phase of the side-to-side drift
  swaySpeed: number;
  flicker: number;
  color: string;
}

/**
 * Embers floating up through the air, in the style of Battlefield 4's menus: far ones are tiny
 * sharp sparks, near ones are big out-of-focus glows (bokeh), all drifting upward with a gentle
 * sway and a flicker. Decorative only: pauses off screen and in background tabs, and stays still
 * for people who prefer reduced motion.
 */
export function WindParticles({ className }: { className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let width = 0;
    let height = 0;
    let embers: Ember[] = [];
    let frame = 0;
    let running = false;
    let visible = true;
    const pointer = { x: -9999, y: -9999 };

    const spawn = (anywhere: boolean): Ember => {
      const z = Math.random() ** 1.8; // most embers far away, a few close to the viewer
      return {
        x: Math.random() * width,
        y: anywhere ? Math.random() * height : height + 20 + Math.random() * 40,
        z,
        vx: (Math.random() - 0.3) * 0.12,
        rise: 0.12 + z * 0.45 + Math.random() * 0.1,
        sway: Math.random() * Math.PI * 2,
        swaySpeed: 0.004 + Math.random() * 0.01,
        flicker: Math.random() * Math.PI * 2,
        color: PALETTE[Math.random() < 0.55 ? 0 : 1] ?? "47 111 237",
      };
    };

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = rect.width;
      height = rect.height;
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const count = Math.min(90, Math.round((width * height) / 12000));
      embers = Array.from({ length: count }, () => spawn(true));
    };

    const draw = () => {
      const dark = document.documentElement.classList.contains("dark");
      ctx.clearRect(0, 0, width, height);
      // Far embers first, near ones last, so the near glows sit on top.
      const ordered = [...embers].sort((a, b) => a.z - b.z);
      for (const e of ordered) {
        const flicker = 0.7 + 0.3 * Math.sin(e.flicker);
        // Fade in near the bottom and out near the top, like embers cooling as they rise.
        const heightFade = Math.min(1, e.y / (height * 0.25), (height - e.y) / (height * 0.12) + 0.2);
        const alpha = Math.max(0, heightFade) * flicker * (dark ? 1 : 0.8);
        if (alpha < 0.02) continue;
        if (e.z > 0.55) {
          // Near: a large, soft, out-of-focus glow.
          const radius = 4 + e.z * 10;
          const glow = ctx.createRadialGradient(e.x, e.y, 0, e.x, e.y, radius);
          glow.addColorStop(0, `rgb(${e.color} / ${alpha * 0.35})`);
          glow.addColorStop(0.5, `rgb(${e.color} / ${alpha * 0.14})`);
          glow.addColorStop(1, `rgb(${e.color} / 0)`);
          ctx.fillStyle = glow;
          ctx.beginPath();
          ctx.arc(e.x, e.y, radius, 0, Math.PI * 2);
          ctx.fill();
        } else {
          // Far: a tiny sharp spark with a faint halo.
          const size = 0.8 + e.z * 2.2;
          ctx.fillStyle = `rgb(${e.color} / ${alpha * 0.25})`;
          ctx.beginPath();
          ctx.arc(e.x, e.y, size * 2.2, 0, Math.PI * 2);
          ctx.fill();
          ctx.fillStyle = `rgb(${e.color} / ${alpha * 0.9})`;
          ctx.beginPath();
          ctx.arc(e.x, e.y, size / 2 + 0.3, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    };

    const step = () => {
      for (const e of embers) {
        e.sway += e.swaySpeed;
        e.flicker += 0.03 + e.z * 0.04;
        let dx = e.vx + Math.sin(e.sway) * (0.15 + e.z * 0.25);
        let dy = -e.rise;
        // The pointer parts the embers softly.
        const px = e.x - pointer.x;
        const py = e.y - pointer.y;
        const distance = Math.hypot(px, py);
        if (distance < 100 && distance > 0.1) {
          const push = (1 - distance / 100) * 0.7;
          dx += (px / distance) * push;
          dy += (py / distance) * push;
        }
        e.x += dx;
        e.y += dy;
        if (e.y < -30 || e.x < -40 || e.x > width + 40) Object.assign(e, spawn(false));
      }
      draw();
      frame = requestAnimationFrame(step);
    };

    const start = () => {
      if (running || reduced || !visible || document.hidden) return;
      running = true;
      frame = requestAnimationFrame(step);
    };
    const stop = () => {
      running = false;
      cancelAnimationFrame(frame);
    };

    resize();
    draw();
    start();

    const resizeObserver = new ResizeObserver(() => {
      resize();
      draw();
    });
    resizeObserver.observe(canvas);
    const intersection = new IntersectionObserver(([entry]) => {
      visible = entry?.isIntersecting ?? true;
      if (visible) start();
      else stop();
    });
    intersection.observe(canvas);
    const onVisibility = () => (document.hidden ? stop() : start());
    const onPointer = (event: PointerEvent) => {
      const rect = canvas.getBoundingClientRect();
      pointer.x = event.clientX - rect.left;
      pointer.y = event.clientY - rect.top;
    };
    const onLeave = () => {
      pointer.x = -9999;
      pointer.y = -9999;
    };
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("pointermove", onPointer, { passive: true });
    document.addEventListener("pointerleave", onLeave);

    return () => {
      stop();
      resizeObserver.disconnect();
      intersection.disconnect();
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("pointermove", onPointer);
      document.removeEventListener("pointerleave", onLeave);
    };
  }, []);

  return <canvas ref={canvasRef} className={clsx("pointer-events-none absolute inset-0 size-full", className)} aria-hidden />;
}
