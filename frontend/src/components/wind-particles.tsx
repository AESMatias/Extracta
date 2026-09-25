"use client";

import clsx from "clsx";
import { useEffect, useRef } from "react";

const COLORS = ["16 185 129", "6 182 212", "47 111 237", "250 204 21"]; // green, cyan, blue, a touch of yellow
const COLOR_WEIGHTS = [0.34, 0.28, 0.3, 0.08];

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  alpha: number;
  color: string;
  drag: number; // heavier particles lag behind the wind
}

function pickColor(): string {
  let r = Math.random();
  for (let i = 0; i < COLORS.length; i++) {
    r -= COLOR_WEIGHTS[i] ?? 0;
    if (r <= 0) return COLORS[i] ?? "47 111 237";
  }
  return "47 111 237";
}

/**
 * Small squares with short trails, carried by a soft wind that gusts and swirls. Decorative only:
 * pauses off screen and in background tabs, and stays still for people who prefer reduced motion.
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
    let particles: Particle[] = [];
    let frame = 0;
    let running = false;
    let visible = true;
    let time = 0;
    const pointer = { x: -9999, y: -9999 };

    const spawn = (anywhere: boolean): Particle => ({
      x: anywhere ? Math.random() * width : -10,
      y: Math.random() * height,
      vx: 0.4 + Math.random() * 0.6,
      vy: 0,
      size: 1.5 + Math.random() * 2.2,
      alpha: 0.25 + Math.random() * 0.45,
      color: pickColor(),
      drag: 0.9 + Math.random() * 0.08,
    });

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = rect.width;
      height = rect.height;
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const count = Math.min(140, Math.round((width * height) / 9000));
      particles = Array.from({ length: count }, () => spawn(true));
    };

    const draw = () => {
      const dark = document.documentElement.classList.contains("dark");
      ctx.clearRect(0, 0, width, height);
      for (const p of particles) {
        const speed = Math.hypot(p.vx, p.vy);
        const trail = Math.min(18, speed * 7);
        const a = p.alpha * (dark ? 1 : 0.8);
        // The trail: a short line behind the particle, fading out.
        ctx.strokeStyle = `rgb(${p.color} / ${a * 0.35})`;
        ctx.lineWidth = Math.max(0.6, p.size * 0.45);
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
        ctx.lineTo(p.x - (p.vx / (speed || 1)) * trail, p.y - (p.vy / (speed || 1)) * trail);
        ctx.stroke();
        // The particle: a tiny square, rotated with its direction.
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(Math.atan2(p.vy, p.vx));
        ctx.fillStyle = `rgb(${p.color} / ${a})`;
        ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size);
        ctx.restore();
      }
    };

    const step = () => {
      time += 0.004;
      const gust = 0.55 + 0.45 * Math.sin(time * 0.9) * Math.sin(time * 0.37 + 1.3); // the wind rises and falls
      for (const p of particles) {
        // A smooth flow field: the wind swirls depending on where the particle is.
        const angle =
          Math.sin(p.x * 0.004 + time * 1.7) * 0.6 + Math.cos(p.y * 0.006 - time * 1.1) * 0.5 - 0.15;
        const force = 0.06 + gust * 0.09;
        p.vx = p.vx * p.drag + Math.cos(angle) * force * 1.6 + 0.02;
        p.vy = p.vy * p.drag + Math.sin(angle) * force;
        // The pointer pushes particles away, like a hand in the breeze.
        const dx = p.x - pointer.x;
        const dy = p.y - pointer.y;
        const distance = Math.hypot(dx, dy);
        if (distance < 110 && distance > 0.1) {
          const push = (1 - distance / 110) * 0.9;
          p.vx += (dx / distance) * push;
          p.vy += (dy / distance) * push;
        }
        p.x += p.vx;
        p.y += p.vy;
        if (p.x > width + 20 || p.y < -20 || p.y > height + 20) Object.assign(p, spawn(false));
        if (p.x < -20) p.x = width + 10;
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
