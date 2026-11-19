// Copies the finished Blender export into the website and shrinks it for the web:
//   blender/build/gallery.glb   -> public/models/gallery.glb   (meshopt geometry + WebP textures)
//   blender/build/gallery.json  -> src/data/gallery.json       (camera stops, artwork info, obstacles)
//
// Usage:  npm run sync:blender
import { spawnSync } from 'node:child_process'
import { existsSync, mkdirSync, mkdtempSync, readFileSync, renameSync, rmdirSync, rmSync, statSync, writeFileSync } from 'node:fs'
import { dirname, join, relative } from 'node:path'
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
function transform(command, input, output, ...options) {
  const result = spawnSync(
    'npx', ['--yes', '@gltf-transform/cli', command, relative(root, input), relative(root, output), ...options],
    { stdio: 'inherit', shell: true, cwd: root },
  )
  if (result.error) throw result.error
  if (result.status !== 0) throw new Error(`glTF Transform ${command} failed`)
}

const temp = mkdtempSync(join(dirname(outGlb), '.gallery-'))
const resized = join(temp, 'resized.glb')
const textured = join(temp, 'textured.glb')
const optimized = join(temp, 'optimized.glb')
try {
  transform('resize', srcGlb, resized, '--width', '3072', '--height', '3072')
  // Encode once from the baked PNGs to keep gradients and brush strokes free of visible blocks.
  transform('webp', resized, textured, '--quality', '94', '--effort', '80')
  transform('optimize', textured, optimized, '--compress', 'meshopt', '--texture-compress', 'false', '--simplify', 'false')
  renameSync(optimized, outGlb)
} finally {
  for (const file of [resized, textured, optimized]) rmSync(file, { force: true })
  rmdirSync(temp)
}

const data = JSON.parse(readFileSync(srcJson, 'utf8'))
if (!data.obstacles) {
  // exports made by an older build_gallery.py did not list the partition
  data.obstacles = [{ id: 'partition', center: [0, 0.5], size: [4.4, 0.12] }]
  console.warn('gallery.json had no "obstacles": added the default partition.')
}
writeFileSync(outJson, JSON.stringify(data, null, 2) + '\n')

console.log(`\nDone: public/models/gallery.glb (${kb(outGlb)}), src/data/gallery.json`)
