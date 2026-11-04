/** @jsxRuntime classic */
import * as React from 'react'
import { artworkCount } from '../gallery/data'

interface IntroProps {
  visible: boolean
  ready: boolean
  progress: number
  onEnter: () => void
}

/** First screen: the empty room, a title, and the "Enter Exhibition" button. */
export function Intro({ visible, ready, progress, onEnter }: IntroProps) {
  return (
    <section className={`g-intro${visible ? '' : ' is-hidden'}`} aria-label="Welcome" inert={!visible}>
      <header className="g-intro__head">
        <h1>Last month’s exhibition</h1>
        <p>
          {artworkCount} contemporary works, shown one at a time. Swipe or use the arrows to move between them.
        </p>
      </header>

      <div className="g-intro__action">
        {ready ? (
          <button type="button" className="g-btn g-btn--primary" onClick={onEnter}>
            Enter Exhibition
          </button>
        ) : (
          <div className="g-loading" role="status" aria-live="polite">
            <span>Preparing the gallery…</span>
            <span className="g-progress" aria-hidden="true">
              <span style={{ transform: `scaleX(${Math.max(0.04, progress / 100)})` }} />
            </span>
          </div>
        )}
      </div>
    </section>
  )
}
