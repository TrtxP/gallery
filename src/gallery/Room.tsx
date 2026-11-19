import { createElement, useLayoutEffect } from 'react'
import { useGLTF } from '@react-three/drei'
import { useThree } from '@react-three/fiber'
import { MeshBasicMaterial, type Material, type Mesh, type Object3D } from 'three/src/Three.js'
import { MODEL_URL } from './data'

/**
 * Everything in the exported scene is lit by Blender: the light is baked into the textures.
 * Current exports declare unlit materials. Older exports need their base-color texture
 * copied into an unlit material so they display with the same baked lighting.
 */
function prepareRoomMaterials(root: Object3D, maxAnisotropy: number): void {
  root.traverse((obj) => {
    const mesh = obj as Mesh
    if (!mesh.isMesh) return
    const old = mesh.material as Material | Material[]
    if (Array.isArray(old)) return

    const map = (old as { map?: MeshBasicMaterial['map'] }).map ?? null
    if (map) map.anisotropy = Math.min(8, maxAnisotropy) // sharp wooden floor at grazing angles
    if ((old as MeshBasicMaterial).isMeshBasicMaterial) {
      old.toneMapped = false
    } else {
      mesh.material = new MeshBasicMaterial({ map, toneMapped: false })
      old.dispose()
    }

    // the room never moves: skip per-frame matrix updates
    mesh.updateMatrix()
    mesh.matrixAutoUpdate = false
  })
}

interface RoomProps {
  onReady: () => void
}

useGLTF.preload(MODEL_URL, false)

export function Room({ onReady }: RoomProps) {
  // `false`: no Draco (so no CDN download). Meshopt decoding is built in.
  const { scene } = useGLTF(MODEL_URL, false)
  const maxAnisotropy = useThree((s) => s.gl.capabilities.getMaxAnisotropy())

  useLayoutEffect(() => {
    prepareRoomMaterials(scene, maxAnisotropy)
    onReady()
  }, [scene, maxAnisotropy, onReady])

  return createElement('primitive', { object: scene })
}
