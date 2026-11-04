/** @jsxRuntime classic */
import * as React from 'react'
import { BackSide } from 'three/src/constants.js'
import { Float32BufferAttribute } from 'three/src/core/BufferAttribute.js'
import { SphereGeometry } from 'three/src/geometries/SphereGeometry.js'
import { Color } from 'three/src/math/Color.js'

/** Sky + soft landscape seen through the big window. Vertex colours only: no texture, no shader. */
function buildSkyGeometry(): SphereGeometry {
  const geometry = new SphereGeometry(90, 32, 20)
  const pos = geometry.getAttribute('position')
  const zenith = new Color('#6aa5ea')
  const horizon = new Color('#e4eefb')
  const haze = new Color('#b9c8b4')
  const ground = new Color('#6f8b66')
  const colors: number[] = []
  const c = new Color()
  for (let i = 0; i < pos.count; i++) {
    const y = pos.getY(i) / 90 // -1 … 1
    if (y >= 0) c.lerpColors(horizon, zenith, Math.pow(y, 0.55))
    else c.lerpColors(haze, ground, Math.pow(-y, 0.5))
    colors.push(c.r, c.g, c.b)
  }
  geometry.setAttribute('color', new Float32BufferAttribute(colors, 3))
  return geometry
}

const geometry = buildSkyGeometry()

export function SkyDome() {
  return (
    <mesh geometry={geometry} renderOrder={-1} frustumCulled={false}>
      <meshBasicMaterial vertexColors side={BackSide} depthWrite={false} toneMapped={false} />
    </mesh>
  )
}
