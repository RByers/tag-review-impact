import { readdirSync } from 'node:fs';
import { getPriority, setPriority } from 'node:os';

const NICE_STEP = 5;

/**
 * Drop this test run's CPU priority by 5 nice levels, relative to whatever launched it, so it
 * yields to interactive sessions on the shared machine under contention without being starved
 * (and costs nothing when the machine is idle).
 *
 * Every vitest config calls this at load, so the workers and browsers vitest spawns afterwards
 * inherit it. Linux nice is per thread, and threads already running by then (vite's transform
 * workers, libuv's pool) keep their own, so each one is reniced; elsewhere tid 0 is the whole
 * process. Call it once per process: each call lowers the priority another step.
 */
export function lowerTestPriority(): void {
  const nice = Math.min(19, getPriority() + NICE_STEP);
  let threads = [0];
  try {
    threads = readdirSync('/proc/self/task').map(Number);
  } catch {
    /* no /proc: not Linux */
  }
  for (const tid of threads) {
    try {
      setPriority(tid, nice);
    } catch {
      /* not permitted, or the thread has exited: leave it at the caller's priority */
    }
  }
}
