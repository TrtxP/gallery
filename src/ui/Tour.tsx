/** @jsxRuntime classic */
import * as React from 'react'
import { artworkCount, stops } from '../gallery/data'
import { bonus } from '../bonus/features'
import { ChevronLeft, ChevronRight, PauseIcon, OverviewIcon, PlayIcon, SoundOff, SoundOn } from './icons'

interface TourProps {
  index: number
  arrived: boolean
  hint: boolean
  musicOn: boolean
  autoOn: boolean
  onPrev: () => void
  onNext: () => void
  onGo: (index: number) => void
  onToggleMusic: () => void
  onToggleAuto: () => void
}

/** Everything shown while visiting: arrows, wall label, progress, music. */
export function Tour({ index, arrived, hint, musicOn, autoOn, onPrev, onNext, onGo, onToggleMusic, onToggleAuto }: TourProps) {
  const stop = stops[index]
  const isOverview = index === 0
  const meta = isOverview ? 'Use the arrows or swipe to start the tour.' : [stop.artist, stop.year].filter(Boolean).join(', ')
  const announce = isOverview ? 'Overview of the gallery' : `Artwork ${index} of ${artworkCount}: ${stop.title}`

  return (
    <div className="g-tour">
      <div className="g-bar">
        <button type="button" className="g-btn" onClick={() => onGo(0)} aria-pressed={isOverview}>
          <OverviewIcon />
          Overview
        </button>
        <div className="g-bar__group">
          {bonus.autotour && (
            <button type="button" className="g-btn" onClick={onToggleAuto} aria-pressed={autoOn}>
              {autoOn ? <PauseIcon /> : <PlayIcon />}
              Auto tour
            </button>
          )}
          <button type="button" className="g-btn" onClick={onToggleMusic} aria-pressed={musicOn}>
            {musicOn ? <SoundOn /> : <SoundOff />}
            Music {musicOn ? 'on' : 'off'}
          </button>
        </div>
      </div>

      <button type="button" className="g-btn g-btn--round g-arrow g-arrow--prev" onClick={onPrev} aria-label="Previous artwork">
        <ChevronLeft />
      </button>
      <button type="button" className="g-btn g-btn--round g-arrow g-arrow--next" onClick={onNext} aria-label="Next artwork">
        <ChevronRight />
      </button>

      <p className={`g-hint${hint ? '' : ' is-hidden'}`} aria-hidden={!hint}>
        Swipe left or right, or tap an arrow
      </p>

      <div className="g-dock">
        <span className="g-sr" aria-live="polite" aria-atomic="true">{arrived ? announce : ''}</span>
        {arrived && (
          <div className="g-label">
            <h2 className="g-label__title">{stop.title}</h2>
            {meta && <p className="g-label__meta">{meta}</p>}
            {stop.description && <p className="g-label__text">{stop.description}</p>}
          </div>
        )}

        <nav className="g-dots" aria-label="Artworks">
          {stops.slice(1).map((s, i) => (
            <button
              key={s.id}
              type="button"
              className="g-dot"
              aria-label={`Go to ${s.title}`}
              aria-current={index === i + 1 ? 'true' : undefined}
              onClick={() => onGo(i + 1)}
            />
          ))}
        </nav>
      </div>
    </div>
  )
}
