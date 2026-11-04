/** @jsxRuntime classic */
import * as React from 'react'
import type { SVGProps } from 'react'

const base: SVGProps<SVGSVGElement> = {
  width: 24,
  height: 24,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2.2,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
  focusable: false,
}

export const ChevronLeft = () => (
  <svg {...base}>
    <path d="M15 5l-7 7 7 7" />
  </svg>
)

export const ChevronRight = () => (
  <svg {...base}>
    <path d="M9 5l7 7-7 7" />
  </svg>
)

/** Four tiles: "see everything". */
export const OverviewIcon = () => (
  <svg {...base}>
    <rect x="4" y="4" width="6.5" height="6.5" rx="1" />
    <rect x="13.5" y="4" width="6.5" height="6.5" rx="1" />
    <rect x="4" y="13.5" width="6.5" height="6.5" rx="1" />
    <rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1" />
  </svg>
)

export const SoundOn = () => (
  <svg {...base}>
    <path d="M4 9.5v5h3.5L12 18.5v-13L7.5 9.5H4z" />
    <path d="M15.5 9a4 4 0 010 6M18 6.5a7.5 7.5 0 010 11" />
  </svg>
)

export const SoundOff = () => (
  <svg {...base}>
    <path d="M4 9.5v5h3.5L12 18.5v-13L7.5 9.5H4z" />
    <path d="M16 9.5l5 5M21 9.5l-5 5" />
  </svg>
)

export const PlayIcon = () => (
  <svg {...base}>
    <path d="M8 5.5v13l10-6.5-10-6.5z" />
  </svg>
)

export const PauseIcon = () => (
  <svg {...base}>
    <path d="M8.5 5.5v13M15.5 5.5v13" />
  </svg>
)
