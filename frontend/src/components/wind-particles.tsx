"use client";

import clsx from "clsx";
import { useEffect, useRef } from "react";

const COLORS = ["16 185 129", "6 182 212", "47 111 237", "250 204 21"]; // green, cyan, blue, a touch of yellow
const COLOR_WEIGHTS = [0.3, 0.26, 0.26, 0.18];
const FALLBACK = "6 182 212";

interface Firefly {
  x: number;
  y: number;
  angle: number; // heading; it wanders a little every frame
  speed: number; // px per frame: slow, like a firefly
  size: number;
  color: string;
  age: number; // frames lived
  life: number; // frames until it fades out and reappears elsewhere
  blink: number; // phase of its gentle glow pulse
  blinkSpeed: number;
}

function pickColor(): string {
  let r = Math.random();
  for (let i = 0; i < COLORS.length; i++) {
    r -= COLOR_WEIGHTS[i] ?? 0;
    if (r <= 0) return COLORS[i] ?? FALLBACK;
  }
  return FALLBACK;
}

/**
 * Fireflies: small glowing squares that drift slowly, light up, pulse and fade away, then appear
 * somewhere else. Decorative only: pauses off screen and in background tabs, and stays still for
 * people who prefer reduced motion.
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
    let flies: Firefly[] = [];
    let frame = 0;
    let running = false;
    let visible = true;
    let time = 0;
    const pointer = { x: -9999, y: -9999 };

    const spawn = (anyAge: boolean): Firefly => {
      const life = 360 + Math.random() * 540; // 6 to 15 seconds at 60 fps
      return {
        x: Math.random() * width,
        y: Math.random() * height,
        angle: Math.random() * Math.PI * 2,
        speed: 0.12 + Math.random() * 0.22,
        size: 1.6 + Math.random() * 1.8,
        color: pickColor(),
        age: anyAge ? Math.random() * life : 0,
        life,
        blink: Math.random() * Math.PI * 2,
        blinkSpeed: 0.02 + Math.random() * 0.03,
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
      const count = Math.min(70, Math.round((width * height) / 16000));
      flies = Array.from({ length: count }, () => spawn(true));
    };

    /** 0 -> 1 -> 0 over its life: fades in, glows, fades out. */
    const presence = (f: Firefly) => {
      const t = f.age / f.life;
      return t < 0.2 ? t / 0.2 : t > 0.75 ? Math.max(0, (1 - t) / 0.25) : 1;
    };

    const draw = () => {
      const dark = document.documentElement.classList.contains("dark");
      ctx.clearRect(0, 0, width, height);
      for (const f of flies) {
        const pulse = 0.55 + 0.45 * Math.sin(f.blink);
        const alpha = presence(f) * pulse * (dark ? 0.95 : 0.75);
        if (alpha < 0.01) continue;
        // The glow: a soft halo around the firefly.
        const radius = f.size * (dark ? 7 : 5.5);
        const glow = ctx.createRadialGradient(f.x, f.y, 0, f.x, f.y, radius);
        glow.addColorStop(0, `rgb(${f.color} / ${alpha * 0.45})`);
        glow.addColorStop(1, `rgb(${f.color} / 0)`);
        ctx.fillStyle = glow;
        ctx.fillRect(f.x - radius, f.y - radius, radius * 2, radius * 2);
        // The light itself: a tiny square, true to the site's square design.
        ctx.fillStyle = `rgb(${f.color} / ${alpha})`;
        ctx.fillRect(f.x - f.size / 2, f.y - f.size / 2, f.size, f.size);
      }
    };

    const step = () => {
      time += 1;
      for (const f of flies) {
        f.age += 1;
        f.blink += f.blinkSpeed;
        // Wander: the heading drifts a little, with a faint shared breeze.
        f.angle += (Math.random() - 0.5) * 0.12 + Math.sin(time * 0.002 + f.y * 0.01) * 0.004;
        let vx = Math.cos(f.angle) * f.speed + 0.03;
        let vy = Math.sin(f.angle) * f.speed - 0.015;
        // The pointer gently shoos them away.
        const dx = f.x - pointer.x;
        const dy = f.y - pointer.y;
        const distance = Math.hypot(dx, dy);
        if (distance < 90 && distance > 0.1) {
          const push = (1 - distance / 90) * 0.8;
          vx += (dx / distance) * push;
          vy += (dy / distance) * push;
        }
        f.x += vx;
        f.y += vy;
        const outside = f.x < -20 || f.x > width + 20 || f.y < -20 || f.y > height + 20;
        if (f.age >= f.life || outside) Object.assign(f, spawn(false));
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
