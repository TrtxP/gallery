import { useEffect } from 'react'

/** Bonus "kiosk": calls `onIdle` after `ms` without any touch, click or key press. */
export function useIdleReset(active: boolean, ms: number, onIdle: () => void): void {
  useEffect(() => {
    if (!active) return
    let timer = window.setTimeout(onIdle, ms)
    const restart = () => {
      window.clearTimeout(timer)
      timer = window.setTimeout(onIdle, ms)
    }
    const events = ['pointerdown', 'pointermove', 'keydown'] as const
    events.forEach((e) => window.addEventListener(e, restart, { passive: true }))
    return () => {
      window.clearTimeout(timer)
      events.forEach((e) => window.removeEventListener(e, restart))
    }
  }, [active, ms, onIdle])
}
