// Copies the finished Blender export into the website and shrinks it for the web:
//   blender/build/gallery.glb   -> public/models/gallery.glb   (meshopt geometry + WebP textures)
//   blender/build/gallery.json  -> src/data/gallery.json       (camera stops, artwork info, obstacles)
//
// Usage:  npm run sync:blender
import { spawnSync } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const srcGlb = join(root, 'blender', 'build', 'gallery.glb')
const srcJson = join(root, 'blender', 'build', 'gallery.json')
const outGlb = join(root, 'public', 'models', 'gallery.glb')
const outJson = join(root, 'src', 'data', 'gallery.json')

const kb = (file) => `${(statSync(file).size / 1024).toFixed(0)} KB`

if (!existsSync(srcGlb) || !existsSync(srcJson)) {
  console.error('No Blender export found in blender/build/. Run build_gallery.py in Blender first (see blender/README_blender.md).')
  process.exit(1)
}

mkdirSync(dirname(outGlb), { recursive: true })
console.log(`Optimizing ${kb(srcGlb)} …`)
const result = spawnSync(
  'npx',
  [
    '--yes', '@gltf-transform/cli', 'optimize', srcGlb, outGlb,
    '--compress', 'meshopt',      // ~4x smaller geometry, decoded by three.js with no extra files
    '--texture-compress', 'webp', // ~3x smaller textures than JPEG/PNG
    '--texture-size', '2048',
    '--simplify', 'false',        // polygons were already reduced in Blender
  ],
  { stdio: 'inherit', shell: true, cwd: root },
)
if (result.status !== 0) process.exit(result.status ?? 1)

const data = JSON.parse(readFileSync(srcJson, 'utf8'))
if (!data.obstacles) {
  // exports made by an older build_gallery.py did not list the partition
  data.obstacles = [{ id: 'partition', center: [0, 0.5], size: [4.4, 0.12] }]
  console.warn('gallery.json had no "obstacles": added the default partition.')
}
writeFileSync(outJson, JSON.stringify(data, null, 2) + '\n')

console.log(`\nDone: public/models/gallery.glb (${kb(outGlb)}), src/data/gallery.json`)
