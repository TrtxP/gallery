/**
 * Bonus features. They are OFF by default and never change the base behaviour.
 * Turn them on per visit with a URL flag:      http://localhost:5173/?bonus=autotour,kiosk,stats
 * or for a whole build with an env variable:   VITE_BONUS=autotour,kiosk npm run build
 *
 *   autotour  adds an "Auto tour" button that walks through the artworks by itself
 *   kiosk     returns to the start screen after 90 s without touches (for public screens)
 *   stats     shows draw calls / triangles / textures in the corner (performance check)
 */
const raw = new URLSearchParams(window.location.search).get('bonus') ?? import.meta.env.VITE_BONUS ?? ''
const enabled = new Set(
  String(raw)
    .split(',')
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean),
)

export const bonus = {
  autotour: enabled.has('autotour'),
  kiosk: enabled.has('kiosk'),
  stats: enabled.has('stats'),
} as const

export const KIOSK_IDLE_MS = 90_000
export const AUTOTOUR_STEP_MS = 7_000
