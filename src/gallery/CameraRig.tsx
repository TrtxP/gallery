import { useLayoutEffect, useRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { FOV, obstacles, room, stops } from './data'
import { fitPose, startTravel, stepTravel, type Pose, type Travel } from './cameraPath'

interface CameraRigProps {
  /** Index into `stops` the camera should be at (0 = overview). */
  index: number
  requestId: number
  onArrive: (requestId: number) => void
}

const bounds = { halfWidth: room.width / 2, halfLength: room.length / 2 }
const prefersReducedMotion = (): boolean => window.matchMedia('(prefers-reduced-motion: reduce)').matches

/**
 * Moves the camera between the stops. The scene is rendered "on demand" (frameloop="demand"),
 * so nothing is drawn while the visitor is just looking at a picture: it only renders while
 * a glide is running. That keeps a kiosk cool and battery-friendly.
 */
export function CameraRig({ index, requestId, onArrive }: CameraRigProps) {
  const camera = useThree((s) => s.camera)
  const width = useThree((s) => s.size.width)
  const height = useThree((s) => s.size.height)
  const invalidate = useThree((s) => s.invalidate)

  const pose = useRef<Pose>({ position: camera.position.clone(), target: camera.position.clone() })
  const travel = useRef<{ path: Travel; requestId: number } | null>(null)
  const lastRequest = useRef<number | null>(null)

  useLayoutEffect(() => {
    const to = fitPose(stops[index], width / height, FOV, bounds)
    const isNewRequest = lastRequest.current !== null && lastRequest.current !== requestId
    lastRequest.current = requestId

    if (isNewRequest) {
      travel.current = { path: startTravel(pose.current, to, obstacles, prefersReducedMotion()), requestId }
    } else {
      const interrupted = travel.current
      travel.current = null
      pose.current.position.copy(to.position)
      pose.current.target.copy(to.target)
      camera.position.copy(to.position)
      camera.lookAt(to.target)
      if (interrupted) onArrive(interrupted.requestId)
    }
    invalidate()
  }, [index, requestId, width, height, camera, invalidate, onArrive])

  useFrame(() => {
    const current = travel.current
    if (!current) return
    const arrived = stepTravel(current.path, performance.now(), pose.current)
    camera.position.copy(pose.current.position)
    camera.lookAt(pose.current.target)
    if (arrived) {
      travel.current = null
      onArrive(current.requestId)
    } else {
      invalidate()
    }
  })

  return null
}
