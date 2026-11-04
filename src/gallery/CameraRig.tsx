import { useEffect, useRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { FOV, obstacles, room, stops } from './data'
import { fitPose, startTravel, stepTravel, type Pose, type Travel } from './cameraPath'

interface CameraRigProps {
  /** Index into `stops` the camera should be at (0 = overview). */
  index: number
  /** Called once when a glide has finished. */
  onArrive: () => void
}

const bounds = { halfWidth: room.width / 2, halfLength: room.length / 2 }
const prefersReducedMotion = (): boolean => window.matchMedia('(prefers-reduced-motion: reduce)').matches

/**
 * Moves the camera between the stops. The scene is rendered "on demand" (frameloop="demand"),
 * so nothing is drawn while the visitor is just looking at a picture: it only renders while
 * a glide is running. That keeps a kiosk cool and battery-friendly.
 */
export function CameraRig({ index, onArrive }: CameraRigProps) {
  const camera = useThree((s) => s.camera)
  const width = useThree((s) => s.size.width)
  const height = useThree((s) => s.size.height)
  const invalidate = useThree((s) => s.invalidate)

  const pose = useRef<Pose>({ position: camera.position.clone(), target: camera.position.clone() })
  const travel = useRef<Travel | null>(null)
  const lastIndex = useRef<number | null>(null)

  useEffect(() => {
    const to = fitPose(stops[index], width / height, FOV, bounds)
    const isNewStop = lastIndex.current !== null && lastIndex.current !== index
    lastIndex.current = index

    if (isNewStop) {
      travel.current = startTravel(pose.current, to, obstacles, prefersReducedMotion())
    } else {
      // first placement, or only the window was resized: jump straight to the framed pose
      travel.current = null
      pose.current.position.copy(to.position)
      pose.current.target.copy(to.target)
      camera.position.copy(to.position)
      camera.lookAt(to.target)
    }
    invalidate()
  }, [index, width, height, camera, invalidate])

  useFrame(() => {
    const current = travel.current
    if (!current) return
    const arrived = stepTravel(current, performance.now(), pose.current)
    camera.position.copy(pose.current.position)
    camera.lookAt(pose.current.target)
    if (arrived) {
      travel.current = null
      onArrive()
    } else {
      invalidate()
    }
  })

  return null
}
