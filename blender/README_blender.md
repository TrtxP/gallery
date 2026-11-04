# Gallery — Blender workflow

`build_gallery.py` builds the complete 3D gallery in one run and prepares the files for Three.js.

## What the script does

| Item | Implementation |
| --- | --- |
| Scene setup | A 10 × 14 × 4 m gallery with a 6 m window and mullions, a central partition, and baseboards. The camera is at eye level (1.6 m); paintings are at 1.55 m |
| Lighting and textures | Sunlight through the window, sky, ceiling lighting, and a spotlight for each painting. Procedural textures include plank flooring, plaster, wood, and ceramic |
| Custom models | A wooden chair (tapered legs, slatted back, stretchers) and a vase turned from a profile and placed on a pedestal |
| External models | Imports `.glb/.gltf` files from `assets/models/`, scales them automatically by height, places them on the floor, and decimates them if they exceed 25,000 triangles |
| Baking | Bakes lighting and textures into 3 atlases (floor, shell, props). No lighting is needed in Three.js |
| Navigation | `gallery.json` contains 7 viewpoints (overview + 6 paintings) in Three.js coordinates |

## Running the script

Blender 4.2 LTS or newer is required.

```bash
# Windows (adjust the path for your Blender version)
"C:\\Program Files\\Blender Foundation\\Blender 4.2\\blender.exe" --background --python build_gallery.py -- --quick --preview

# macOS
/Applications/Blender.app/Contents/MacOS/Blender --background --python build_gallery.py -- --quick --preview

# Linux
blender --background --python build_gallery.py -- --quick --preview
```

1. **Start with `--quick --preview`** (about a minute). It uses small textures and writes `preview_*.png` files to `build/`. Check the composition and brightness.
2. Download models (see below) and optionally add your own paintings.
3. **Run the final build without `--quick`**: `... -- --preview`. On a CPU, this takes 10–40 minutes because the floor is baked at 2560 × 3584.

| Flag | Description |
| --- | --- |
| `--quick` | Test mode: textures at 1/8 resolution, 16 samples |
| `--res-scale 0.5` | Set all texture dimensions to a fraction of full resolution |
| `--samples N` | Number of baking samples (128 by default; denoising is enabled) |
| `--exposure 1.4` | Brighten the scene (use 0.7 to darken it) |
| `--reuse-bakes` | Reuse existing `build/textures/bake_*.png` files instead of baking again. Use only if that object's geometry and lighting have not changed |
| `--gpu` | Bake on the GPU (OptiX/CUDA/HIP/Metal). If no GPU is found, the script falls back to the CPU |
| `--preview` | Render `build/preview_*.png` from the baked textures to show how the scene will look in Three.js |
| `--out DIR` | Write output to a different directory |

## External models (required by the project brief)

Download at least one model, for example from [Poly Haven Models](https://polyhaven.com/models) (CC0, glTF format, 1k), and place it in `assets/models/`:

```text
assets/models/armchair.glb          (or armchair.gltf, or an armchair/ folder with .gltf + textures)
assets/models/sculpture.glb         (optional)
```

File names, positions, and heights are configured in the `EXTERNAL_MODELS` list near the top of the script. If a file is missing, the script skips that model and prints a warning.

## Your own paintings

Place `art_01.jpg … art_06.jpg` in `assets/artworks/`. The script preserves their aspect ratios and adjusts the frames automatically. If a file is missing, a generated abstract image is used instead. Edit titles, artists, and years in the `ARTWORKS` list.

## Output in `build/`

```text
gallery.glb      scene (Floor, Shell, Props, Art_01…Art_06, Viewpoint_00…06)
gallery.json     viewpoints: position/target + title/artist/year/artwork
gallery.blend    editable Blender project
textures/        baked atlases and paintings in PNG format (for inspection)
preview_*.png    previews (only with --preview)
```

## Getting the scene into the site

From the project root, run `npm run sync:blender`. The script takes `blender/build/gallery.glb`, compresses it (meshopt + WebP) into `public/models/gallery.glb`, and copies `gallery.json` to `src/data/gallery.json`. See the root `README.md` for details.

## Using the scene in Three.js

- Replace materials on `Floor`, `Shell`, and `Props` with `MeshBasicMaterial({ map })`, because lighting has already been baked. Do the same for `Art_*`.
- Set the texture color space with `texture.colorSpace = SRGBColorSpace`.
- Set the scene background to a sky color (for example, `#bcd6ff`), visible through the window.
- To reduce file size after export, run: `npx @gltf-transform/cli optimize build/gallery.glb public/gallery.glb --texture-compress webp`.
