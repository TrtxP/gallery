import raw from '../data/gallery.json'
import type { GalleryData, Obstacle, Viewpoint } from './types'

const data = raw as unknown as GalleryData

/** URL of the exported Blender scene (works under any Vite `base`). */
export const MODEL_URL = `${import.meta.env.BASE_URL}models/gallery.glb`
export const MUSIC_URL = `${import.meta.env.BASE_URL}audio/ambient.mp3`

export const room = data.room
export const FOV = data.suggestedFov ?? 55

/** stops[0] is the overview, stops[1..] are the artworks in tour order. */
export const stops: Viewpoint[] = data.viewpoints
export const artworkCount = stops.length - 1

/** The freestanding partition. Older gallery.json files had no `obstacles`, so keep a fallback. */
export const obstacles: Obstacle[] = data.obstacles ?? [
  { id: 'partition', center: [0, 0.5], size: [4.4, 0.12] },
]
