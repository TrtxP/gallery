# Gallery — Blender scene and review guide

This guide explains how to install Blender, inspect the existing gallery, regenerate its 3D scene, and test the result in the website. The main [README](../README.md) covers cloning and running the web application.

## Before you begin

1. Install Git and [Git LFS](https://git-lfs.com/), run `git lfs install`, and clone the repository as described in the main README. If it was cloned before Git LFS was installed, run `git lfs pull` from the project root. Models, artwork, audio, and the `.blend` file are stored with Git LFS.
2. Install **Blender 4.2 LTS or newer**. The current scene was tested with Blender 5.2 LTS. Check the [system requirements](https://www.blender.org/download/requirements/) for your version and hardware.
3. To run the website or synchronize a new export, install Node.js 20 or newer and run `npm install` in the project root.

### Install Blender

Download Blender from the [official download page](https://www.blender.org/download/) or choose a specific release from [previous versions](https://www.blender.org/download/previous-versions/).

- **Windows:** download the Windows installer, run it, and follow its installation steps. Alternatively, extract the portable ZIP. Note the location of `blender.exe`.
- **macOS:** download the version for your Mac, open the downloaded package, and move Blender to Applications. If macOS asks for permission the first time, approve it in the system settings.
- **Linux:** download and extract the Linux archive, then run the `blender` executable from the extracted directory. You can also use your distribution's package manager if it provides a compatible version.

Start Blender once to confirm it opens. For terminal commands, either add its installation directory to your `PATH` or use the full executable path. The project uses Blender's bundled Python and NumPy; a separate Python installation is not needed.

## Inspect the existing scene

You do not need to rebuild the scene to review it.

1. In Blender, choose **File → Open** and open `blender/build/gallery.blend` from the cloned project. Alternatively, open Blender first and use **File → Import → glTF 2.0** to inspect `blender/build/gallery.glb`.
2. Use the Outliner to find the room objects `Floor`, `Shell`, and `Props`, the `Armchair`, `Horse_Head`, and `Vase` models, the six `Art_01`–`Art_06` objects, and `Viewpoint_00`–`Viewpoint_06`. The `.blend` packs the source textures and retains the original materials, lights, and gallery camera. The GLB uses baked, unlit materials.
3. Orbit with the middle mouse button and zoom with the wheel. Select an object in the Outliner to inspect it; use **View → Frame Selected** to focus on it. Switch the viewport to **Material Preview** to inspect textures.
4. Check `blender/build/gallery.json` for the room dimensions, partition obstacle, and seven viewpoints. Coordinates are exported for glTF/Three.js with Y up; the conversion from Blender is `(x, z, -y)`.

The generated `blender/build/textures/` directory is ignored by Git. Fresh `.blend` builds pack their images and can be opened on their own.

## Scene overview

| Area | Implementation |
| --- | --- |
| Architecture | A 10 × 14 × 4 m room with floor, walls, ceiling, a 6 m wide window, and a freestanding partition. The visitor's eye height is 1.6 m; artwork centers are at 1.55 m. |
| Artwork | Six framed paintings use images from `assets/artworks/`. Their position, maximum size, title, artist, and year are configured in `ARTWORKS` in `build_gallery.py`. |
| Models | The script creates a wooden chair and two stands. It imports [Modern Arm Chair 01](https://polyhaven.com/a/modern_arm_chair_01) by Vibrant Nordic, [Horse Head](https://polyhaven.com/a/horse_head) by Tina, and [Antique Ceramic Vase 01](https://polyhaven.com/a/antique_ceramic_vase_01) by James Ray Cock (Poly Haven, CC0). |
| Lighting | Sunlight and soft window light mix with broad ceiling fill and warm track spots. The paintings and imported models have their own spots. |
| Baking | Cycles bakes the floor, shell, props, armchair, bust, and vase into six textures and maps the highlights with AgX. The imported models have dedicated atlases that retain the response of their source normal, roughness, and metallic maps. The vase uses its original UV layout for the bake. Artwork images are exported individually. |
| Navigation | The JSON export describes an overview and six artwork viewpoints, plus the partition obstacle. The web camera uses these data to frame the artworks and route around the partition. |

At full resolution, the floor atlas is 2560 × 3584 pixels. The shell and each imported model use a 2048 × 2048 atlas, and the props atlas is 1536 × 1536. Baking can take considerable time and memory, depending on the computer and settings.

## Generate a review copy

Run the following commands **from the project root**. The `--` separates Blender's options from the script's options. The example uses a separate `blender/review-build` directory so it does not overwrite the checked-in `blender/build` files.

Windows PowerShell (adjust the Blender path to your installation):

```powershell
& "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe" --background --python-exit-code 1 --python blender/build_gallery.py -- --quick --preview --out blender/review-build
```

macOS, when Blender is installed in Applications:

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python blender/build_gallery.py -- --quick --preview --out blender/review-build
```

Linux, or any system with `blender` on `PATH`:

```bash
blender --background --python-exit-code 1 --python blender/build_gallery.py -- --quick --preview --out blender/review-build
```

The quick mode uses smaller bake textures and fewer samples, so it is useful for checking the workflow rather than final image quality. Wait for the `[gallery] ALL DONE` message, then inspect:

```text
blender/review-build/
  gallery.blend         editable generated scene
  gallery.glb           exported scene with embedded resources
  gallery.json          room, obstacle, and viewpoint metadata
  textures/             baked texture atlases and generated images
  preview_overview.png  overview render
  preview_art_01.png    first artwork render
  preview_art_03.png    third artwork render
  preview_art_06.png    Weather Report render
  preview_window.png    window render
  preview_horse_head.png  bronze bust and plinth
  preview_armchair.png    oak and leather armchair
  preview_vase.png        glazed ceramic vase and pedestal
```

Open the preview images and the generated `.blend` or GLB to check composition, lighting, models, and artwork framing. The preview renders simulate the baked, unlit appearance used by the site. The review directory is a local generated output and may appear as untracked files in Git.

## Build options

Add these options after `--` in the commands above:

| Option | Effect |
| --- | --- |
| `--quick` | Use 1/8-scale bake textures and 16 samples by default. |
| `--res-scale 0.5` | Scale bake texture dimensions; without `--quick`, the default is `1.0`. This option overrides the quick-mode scale. |
| `--samples 64` | Set the number of bake samples; the defaults are 128 normally and 16 in quick mode. |
| `--exposure 1.4` | Multiply light power; use a lower value such as `0.7` for a darker result. The default is `1.0`. |
| `--gpu` | Try GPU baking using an available OptiX, CUDA, HIP, Metal, or oneAPI device; the script falls back to CPU if none is usable. |
| `--reuse-bakes` | Reuse existing `textures/bake_*.png` files in the chosen output directory. Use only when the relevant geometry, lighting, and desired resolution have not changed. |
| `--preview` | Render the overview, three artworks, the window, and the three imported models after export. |
| `--out DIR` | Choose the output directory. Without this option the script writes to `blender/build/`. |

For a higher-quality build, remove `--quick`, optionally set `--res-scale` and `--samples`, and keep a separate output directory until you are ready to update the project. Do not use `--reuse-bakes` after changing the scene's geometry or lighting: old textures can hide those changes.

## Change artwork or external models

- The `Weather Report` texture (`assets/artworks/art_06.png`, 1499 × 1049 pixels) was created with the built-in ImageGen tool using the previous image as a reference.

  <details>
  <summary>Weather Report image prompt</summary>

  > Use case: style-transfer. Redesign the reference as the high-resolution image texture of the fictional contemporary gallery painting Weather Report. Keep the reference's continuous abstract golden weather field, warm yellow-ochre light coming through atmospheric charcoal masses, with restrained earthy olive at a few edges, no literal horizon, silhouettes or objects. Translate the rounded low-resolution patches into a purposeful modern oil painting. Broad expressive layered storm bands sweeping across the canvas, fine visible bristle strokes, dry brush marks and variations in pigment at close range, rich dark indigo-brown, warm muted ochre and small areas of pale honey. Painterly full-bleed flat scan, landscape 10:7 composition, high resolution and crisp organic texture, direct frontal orthographic image with even capture lighting. No text, frame, border, wall, signature or mockup. Fill entire image with the artwork.

  </details>

- The repository already contains six placeholder images under `blender/assets/artworks/`. Replace them with `art_01` through `art_06` in JPG, JPEG, PNG, or WebP format. The script checks extensions in that order, so remove an older file with a higher-priority extension if it should no longer be used. It preserves each image's aspect ratio inside the configured frame. If an image is missing, the script generates a placeholder.
- Edit `ARTWORKS` in `blender/build_gallery.py` to change titles, artists, years, positions, and maximum sizes. Regenerate the scene to apply these changes.
- The supplied models are in `blender/assets/models/armchair/`, `blender/assets/models/sculpture/`, and `blender/assets/models/vase/`. The vase includes Poly Haven's 4K base color, normal, and packed material textures. The `EXTERNAL_MODELS` list controls the names, base positions, rotations, and target heights. The script looks for a matching `.glb` or `.gltf` either directly in `assets/models/` or inside a matching subdirectory. Keep any referenced `.bin` and texture files alongside a `.gltf` model.
- Imported meshes are scaled to their configured height and reduced when they exceed the target of 25,000 triangles per model. If a model is missing, the script logs a message and skips it; check the terminal output when reviewing the scene.

## Test the scene in the website

To review the existing website without changing generated files, run the following from the project root:

```bash
npm install
npm run dev
```

Open the local address printed by Vite. Enter the exhibition and check the overview, all six artworks, the previous/next arrows, dots, swipes on a touch device, and the music toggle. Check that the camera travels around the partition and that artwork remains framed in portrait and landscape layouts. You can also run `npm run build` and `npm run lint` from the root.

To put a **new** Blender export into the site, first generate it in `blender/build/` by using `--out blender/build` or omitting `--out`; this overwrites the existing generated Blender outputs. Then run from the project root:

```bash
npm run sync:blender
npm run build
npm run dev
```

The sync script reads only `blender/build/gallery.glb` and `blender/build/gallery.json`; it does not automatically use `blender/review-build`. It optimizes the GLB with meshopt and WebP into `public/models/gallery.glb` and writes the metadata to `src/data/gallery.json`, overwriting both website files. It invokes `@gltf-transform/cli` through `npx`, which may need network access on the first run. Review the changes with `git status` and retest the exhibition after synchronization.

## Troubleshooting

- **Files contain text beginning with `version https://git-lfs.github.com/spec/v1`:** they are LFS pointers. Install Git LFS, then run `git lfs install` and `git lfs pull` in the repository.
- **`blender` is not recognized:** use the full executable path as in the examples or add its directory to `PATH`.
- **Missing textures in the `.blend`:** regenerate the scene and keep the new `.blend` with its output `textures/` folder, or inspect the GLB instead.
- **A model is missing:** check the terminal log and confirm the model's configured name, `.gltf`/`.glb`, and any referenced textures and `.bin` files are present.
- **A rebuild is slow or runs out of resources:** start with `--quick`, try fewer `--samples`, or test `--gpu` with compatible drivers. Use full resolution only when needed.
- **Website still shows the old scene:** a separate review build does not update the website. Follow the synchronization steps above only when you intend to replace the checked-in outputs.
