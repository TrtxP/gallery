import { CatmullRomCurve3, LineCurve3, MathUtils, Vector3, type Curve } from 'three/src/Three.js'
import type { Obstacle, Viewpoint } from './types'

/**
 * Pure camera maths (no React, no WebGL), so it is easy to reason about and test:
 *  - fitPose:   where the camera should stand for a stop, adapted to the screen shape
 *  - planRoute: a walkable route between two poses that goes AROUND obstacles
 *  - travel:    time-based, eased movement along that route
 */

export interface Pose {
  position: Vector3
  target: Vector3
}

export interface Bounds {
  halfWidth: number
  halfLength: number
}

/** Pictures sit a little above screen centre so the caption never covers them. */
const FRAMING_LIFT = 0.16
/** How far we may step back (m) when the screen is narrow, e.g. a portrait kiosk. */
const MAX_PULLBACK = 2.6
const WALL_MARGIN = 0.4
/** Free space (m) kept between the walking route and an obstacle. */
const ROUTE_MARGIN = 0.95

export const smootherstep = (t: number): number => t * t * t * (t * (t * 6 - 15) + 10)

export function fitPose(stop: Viewpoint, aspect: number, fovDeg: number, bounds: Bounds): Pose {
  const position = new Vector3(...stop.position)
  const target = new Vector3(...stop.target)
  if (!stop.artwork) return { position, target }

  const vfov = MathUtils.degToRad(fovDeg)
  const hfov = 2 * Math.atan(Math.tan(vfov / 2) * aspect)
  const needW = (stop.artwork.width * 1.55) / 2 / Math.tan(hfov / 2)
  const needH = (stop.artwork.height * 1.75) / 2 / Math.tan(vfov / 2)

  const away = position.clone().sub(target).setY(0)
  const base = away.length()
  away.normalize()
  const dist = MathUtils.clamp(Math.max(base, needW, needH), base, base + MAX_PULLBACK)

  position.x = MathUtils.clamp(target.x + away.x * dist, -bounds.halfWidth + WALL_MARGIN, bounds.halfWidth - WALL_MARGIN)
  position.z = MathUtils.clamp(target.z + away.z * dist, -bounds.halfLength + WALL_MARGIN, bounds.halfLength - WALL_MARGIN)
  target.y -= FRAMING_LIFT
  return { position, target }
}

/** Liang–Barsky: does the segment A→B touch the rectangle? (X-Z plane) */
function segmentHitsRect(ax: number, az: number, bx: number, bz: number, minX: number, minZ: number, maxX: number, maxZ: number): boolean {
  const dx = bx - ax
  const dz = bz - az
  const p = [-dx, dx, -dz, dz]
  const q = [ax - minX, maxX - ax, az - minZ, maxZ - az]
  let t0 = 0
  let t1 = 1
  for (let i = 0; i < 4; i++) {
    if (p[i] === 0) {
      if (q[i] < 0) return false
      continue
    }
    const r = q[i] / p[i]
    if (p[i] < 0) {
      if (r > t1) return false
      if (r > t0) t0 = r
    } else {
      if (r < t0) return false
      if (r < t1) t1 = r
    }
  }
  return true
}

const routeLength = (pts: Vector3[]): number => pts.slice(1).reduce((sum, p, i) => sum + p.distanceTo(pts[i]), 0)

/** Straight line when the way is free; otherwise around the nearer end of the obstacle. */
export function planRoute(from: Vector3, to: Vector3, obstacles: Obstacle[]): Vector3[] {
  for (const o of obstacles) {
    const [cx, cz] = o.center
    const hx = o.size[0] / 2 + ROUTE_MARGIN
    const hz = o.size[1] / 2 + ROUTE_MARGIN
    if (!segmentHitsRect(from.x, from.z, to.x, to.z, cx - hx, cz - hz, cx + hx, cz + hz)) continue

    const y = (from.y + to.y) / 2
    const startsInFront = from.z >= cz
    const side = (x: number): Vector3[] => {
      const near = new Vector3(x, y, startsInFront ? cz + hz : cz - hz)
      const far = new Vector3(x, y, startsInFront ? cz - hz : cz + hz)
      return [from, near, far, to]
    }
    const east = side(cx + hx)
    const west = side(cx - hx)
    return routeLength(east) <= routeLength(west) ? east : west
  }
  return [from, to]
}

export interface Travel {
  curve: Curve<Vector3>
  fromTarget: Vector3
  toTarget: Vector3
  /** seconds */
  duration: number
  /** `performance.now()` of the first rendered frame of this travel (null until then) */
  startedAt: number | null
}

export function startTravel(from: Pose, to: Pose, obstacles: Obstacle[], reducedMotion: boolean): Travel {
  const pts = planRoute(from.position.clone(), to.position.clone(), obstacles)
  const curve: Curve<Vector3> = pts.length === 2 ? new LineCurve3(pts[0], pts[1]) : new CatmullRomCurve3(pts, false, 'centripetal')
  const length = curve.getLength()
  return {
    curve,
    fromTarget: from.target.clone(),
    toTarget: to.target.clone(),
    duration: reducedMotion ? 0.45 : MathUtils.clamp(1.1 + 0.3 * length, 1.5, 3.8),
    startedAt: null,
  }
}

/**
 * Writes the pose for the moment `nowMs` into `out`. Returns true on arrival.
 * Uses wall-clock time, not frame count, so a glide lasts the same on a slow screen
 * (it just shows fewer frames) and never stalls after a long pause between frames.
 */
export function stepTravel(travel: Travel, nowMs: number, out: Pose): boolean {
  travel.startedAt ??= nowMs
  const elapsed = Math.min(travel.duration, (nowMs - travel.startedAt) / 1000)
  const k = smootherstep(elapsed / travel.duration)
  travel.curve.getPointAt(k, out.position)
  out.target.lerpVectors(travel.fromTarget, travel.toTarget, k)
  return elapsed >= travel.duration
}
