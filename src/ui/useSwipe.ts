import { useRef, type PointerEvent } from 'react'

interface SwipeOptions {
  enabled: boolean
  onLeft: () => void
  onRight: () => void
}

const MIN_DISTANCE = 56 // px
const MAX_DURATION = 900 // ms

/**
 * Horizontal swipe → next / previous.
 * A swipe may start anywhere, even on a button: a tap moves < 56 px and is never a swipe,
 * so the two cannot be confused.
 */
export function useSwipe({ enabled, onLeft, onRight }: SwipeOptions) {
  const start = useRef<{ x: number; y: number; t: number } | null>(null)

  return {
    onPointerDown(e: PointerEvent<HTMLElement>) {
      if (!enabled) return
      start.current = { x: e.clientX, y: e.clientY, t: performance.now() }
    },
    onPointerUp(e: PointerEvent<HTMLElement>) {
      const s = start.current
      start.current = null
      if (!s || !enabled) return
      const dx = e.clientX - s.x
      const dy = e.clientY - s.y
      const fast = performance.now() - s.t < MAX_DURATION
      if (fast && Math.abs(dx) >= MIN_DISTANCE && Math.abs(dx) > Math.abs(dy) * 1.6) {
        if (dx < 0) onLeft()
        else onRight()
      }
    },
    onPointerCancel() {
      start.current = null
    },
  }
}
