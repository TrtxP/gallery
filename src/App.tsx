/** @jsxRuntime classic */
import * as React from 'react'
import { useCallback, useEffect, useState } from 'react'
import { useProgress } from '@react-three/drei'
import { GalleryScene } from './gallery/GalleryScene'
import { stops } from './gallery/data'
import { AUTOTOUR_STEP_MS, KIOSK_IDLE_MS, bonus } from './bonus/features'
import { useIdleReset } from './bonus/useIdleReset'
import { ErrorBoundary } from './ui/ErrorBoundary'
import { Intro } from './ui/Intro'
import { Tour } from './ui/Tour'
import { useAmbientMusic } from './ui/useAmbientMusic'
import { useSwipe } from './ui/useSwipe'

const LAST = stops.length - 1 // stops[0] is the overview, 1…LAST are the artworks

export default function App() {
  const [phase, setPhase] = useState<'intro' | 'tour'>('intro')
  const [{ index, requestId, arrived }, setNavigation] = useState({ index: 0, requestId: 0, arrived: true })
  const [ready, setReady] = useState(false)
  const [hint, setHint] = useState(false)
  const [autoOn, setAutoOn] = useState(false)
  const progress = useProgress((s) => s.progress)
  const music = useAmbientMusic()
  const { start: startMusic, stop: stopMusic } = music

  const go = useCallback((i: number) => {
    setNavigation((current) => {
      if (i === current.index) return current
      return { index: i, requestId: current.requestId + 1, arrived: false }
    })
    setHint(false)
  }, [])
  const next = useCallback(() => go(index >= LAST ? 1 : index + 1), [go, index])
  const prev = useCallback(() => go(index <= 1 ? LAST : index - 1), [go, index])

  const enter = useCallback(() => {
    setPhase('tour')
    go(1)
    setHint(true)
    startMusic() // a tap is the moment browsers allow sound to begin
  }, [go, startMusic])

  const backToStart = useCallback(() => {
    setPhase('intro')
    go(0)
    setAutoOn(false)
    stopMusic()
  }, [go, stopMusic])

  const swipe = useSwipe({ enabled: phase === 'tour', onLeft: next, onRight: prev })

  // arrow keys / Escape (handy on a desktop, harmless on a touch screen)
  useEffect(() => {
    if (phase !== 'tour') return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') next()
      else if (e.key === 'ArrowLeft') prev()
      else if (e.key === 'Escape') go(0)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [phase, next, prev, go])

  // the "swipe or tap" hint fades by itself
  useEffect(() => {
    if (!hint) return
    const id = window.setTimeout(() => setHint(false), 7000)
    return () => window.clearTimeout(id)
  }, [hint])

  // --- bonus features (off unless enabled, see src/bonus/features.ts) ---
  useEffect(() => {
    if (!autoOn || phase !== 'tour' || !arrived) return
    const id = window.setTimeout(next, AUTOTOUR_STEP_MS)
    return () => window.clearTimeout(id)
  }, [autoOn, phase, arrived, next])
  useIdleReset(bonus.kiosk && phase === 'tour', KIOSK_IDLE_MS, backToStart)

  const handleReady = useCallback(() => setReady(true), [])
  const handleArrive = useCallback((finishedRequest: number) => {
    setNavigation((current) => current.requestId === finishedRequest ? { ...current, arrived: true } : current)
  }, [])

  return (
    <ErrorBoundary>
      <div className="g-stage" {...swipe} onContextMenu={(e) => e.preventDefault()}>
        <div className="g-canvas" aria-hidden="true">
          <GalleryScene index={index} requestId={requestId} showStats={bonus.stats} onReady={handleReady} onArrive={handleArrive} />
        </div>

        <Intro visible={phase === 'intro'} ready={ready} progress={progress} onEnter={enter} />

        {phase === 'tour' && (
          <Tour
            index={index}
            arrived={arrived}
            hint={hint}
            musicOn={music.enabled}
            autoOn={autoOn}
            onPrev={prev}
            onNext={next}
            onGo={go}
            onToggleMusic={music.toggle}
            onToggleAuto={() => setAutoOn((v) => !v)}
          />
        )}
      </div>
    </ErrorBoundary>
  )
}
