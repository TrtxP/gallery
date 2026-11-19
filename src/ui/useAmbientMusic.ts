import { useEffect, useRef, useState } from 'react'
import { MUSIC_URL } from '../gallery/data'

const STORAGE_KEY = 'gallery:music'
const VOLUME = 0.45

function readPreference(): boolean {
  try {
    return window.localStorage.getItem(STORAGE_KEY) !== 'off'
  } catch {
    return true
  }
}

function savePreference(on: boolean): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, on ? 'on' : 'off')
  } catch {
    /* private mode: the choice just isn't remembered */
  }
}

/**
 * Background music with a soft fade in/out.
 * Browsers only allow sound after a touch, so `start()` is called from the "Enter Exhibition" tap.
 */
export function useAmbientMusic() {
  const [enabled, setEnabled] = useState(readPreference)
  const audio = useRef<HTMLAudioElement | null>(null)
  const started = useRef(false)
  const fade = useRef<number | null>(null)

  const fadeTo = (el: HTMLAudioElement, to: number, ms: number, done?: () => void) => {
    if (fade.current !== null) cancelAnimationFrame(fade.current)
    const from = el.volume
    const t0 = performance.now()
    const step = (now: number) => {
      const k = Math.max(0, Math.min(1, (now - t0) / ms))
      el.volume = from + (to - from) * k
      if (k < 1) {
        fade.current = requestAnimationFrame(step)
      } else {
        fade.current = null
        done?.()
      }
    }
    fade.current = requestAnimationFrame(step)
  }

  const play = () => {
    if (!audio.current) {
      const el = new Audio(MUSIC_URL)
      el.loop = true
      el.preload = 'auto'
      el.volume = 0
      audio.current = el
    }
    const el = audio.current
    el.play().then(
      () => fadeTo(el, VOLUME, 1800),
      () => {
        /* sound was blocked: the Music button lets the visitor start it */
      },
    )
  }

  const start = () => {
    started.current = true
    if (enabled) play()
  }

  const stop = () => {
    started.current = false
    const el = audio.current
    if (el) fadeTo(el, 0, 600, () => el.pause())
  }

  const toggle = () => {
    const next = !enabled
    setEnabled(next)
    savePreference(next)
    if (!started.current) return
    if (next) {
      play()
    } else if (audio.current) {
      const el = audio.current
      fadeTo(el, 0, 700, () => el.pause())
    }
  }

  // pause when the tab / screen is hidden, resume when it comes back
  useEffect(() => {
    const onVisibility = () => {
      const el = audio.current
      if (!el || !started.current || !enabled) return
      if (document.hidden) el.pause()
      else void el.play().catch(() => undefined)
    }
    document.addEventListener('visibilitychange', onVisibility)
    return () => document.removeEventListener('visibilitychange', onVisibility)
  }, [enabled])

  useEffect(
    () => () => {
      if (fade.current !== null) cancelAnimationFrame(fade.current)
      audio.current?.pause()
    },
    [],
  )

  return { enabled, start, stop, toggle }
}
