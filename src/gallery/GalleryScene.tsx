/** @jsxRuntime classic */
import * as React from 'react'
import { Suspense } from 'react'
import { Canvas } from '@react-three/fiber'
import { FOV, stops } from './data'
import { CameraRig } from './CameraRig'
import { Room } from './Room'
import { SkyDome } from './SkyDome'
import { PerfProbe } from '../bonus/PerfProbe'

interface GallerySceneProps {
  index: number
  requestId: number
  showStats: boolean
  onReady: () => void
  onArrive: (requestId: number) => void
}

export function GalleryScene({ index, requestId, showStats, onReady, onArrive }: GallerySceneProps) {
  return (
    <Canvas
      // draw only when something changes (see CameraRig)
      frameloop="demand"
      // baked light must reach the screen untouched: no tone mapping
      flat
      dpr={[1, 2]}
      gl={{ antialias: true, powerPreference: 'high-performance' }}
      camera={{ fov: FOV, near: 0.05, far: 200, position: stops[0].position }}
      // gestures are handled by the UI layer, the canvas only draws
      style={{ pointerEvents: 'none' }}
    >
      <color attach="background" args={['#cfe0f5']} />
      <SkyDome />
      <Suspense fallback={null}>
        <Room onReady={onReady} />
      </Suspense>
      <CameraRig index={index} requestId={requestId} onArrive={onArrive} />
      {showStats && <PerfProbe />}
    </Canvas>
  )
}
