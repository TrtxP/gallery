/** Shapes of `src/data/gallery.json`, which is written by `blender/build_gallery.py`. */
export type Vec3 = [number, number, number]

export interface ArtworkInfo {
  /** Name of the picture mesh inside gallery.glb */
  node: string
  /** Picture size in metres */
  width: number
  height: number
}

export interface Viewpoint {
  id: string
  title: string
  artist: string
  year: number | null
  description: string
  /** Where the visitor stands (Three.js coordinates, Y up) */
  position: Vec3
  /** What the visitor looks at */
  target: Vec3
  /** `null` for the overview */
  artwork: ArtworkInfo | null
}

/** A box on the floor plan the camera must walk around (centre / size in the X-Z plane). */
export interface Obstacle {
  id: string
  center: [number, number]
  size: [number, number]
}

export interface GalleryData {
  room: { width: number; length: number; height: number }
  eyeHeight: number
  suggestedFov: number
  viewpoints: Viewpoint[]
  obstacles?: Obstacle[]
}
