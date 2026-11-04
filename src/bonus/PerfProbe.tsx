import { useEffect } from 'react'
import { useFrame, useThree } from '@react-three/fiber'

/** Bonus "stats": live renderer counters, written straight into a DOM node (no React re-renders). */
export function PerfProbe() {
  const gl = useThree((s) => s.gl)

  useEffect(() => {
    const el = document.createElement('pre')
    el.id = 'perf-probe'
    el.className = 'g-perf'
    document.body.appendChild(el)
    return () => el.remove()
  }, [])

  useFrame(() => {
    const el = document.getElementById('perf-probe')
    if (!el) return
    const { render, memory } = gl.info
    el.textContent = `draw calls  ${render.calls}\ntriangles   ${render.triangles}\ntextures    ${memory.textures}\ngeometries  ${memory.geometries}`
  })

  return null
}
