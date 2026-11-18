# navigo-models

The 3D vehicles Navigo shows during navigation: one per way of travelling,
from a matatu to the SGR. Each model is **built from code**. A Python script
describes the vehicle (its shape, materials and Kenyan details) and Blender,
running headless in Docker, turns it into a `.glb` file the app bundles.

Nothing is bought or downloaded from model stores, so the models are Navigo's
own, and any of them can be changed by editing its script and rebuilding.

- [Quick start](#quick-start)
- [The models](#the-models)
- [Everyday tasks](#everyday-tasks)
- [Add a new model](#add-a-new-model)
- [How the app uses the models](#how-the-app-uses-the-models)
- [How a build works](#how-a-build-works)
- [Rules every model follows](#rules-every-model-follows)
- [Troubleshooting](#troubleshooting)

---

## Quick start

### What you need

| | |
|---|---|
| **Docker** | Docker Desktop on Windows or macOS, Docker Engine on Linux. About 5 GB of free disk. |
| **A bash shell** | On Windows, use **Git Bash** (comes with Git for Windows) or WSL. The scripts don't run in PowerShell or cmd. |
| **Node.js 18+** | Only for the 3D viewer. |
| **The app next to this repo** | The build writes into `../app/assets/models` by default, so keep the usual workspace layout: |

```
navigo/
├── app/              ← receives the .glb files (assets/models/)
├── mobile/           ← can receive them too (OUT=, see below)
└── navigo-models/    ← this repo
```

### Build everything, in 3 commands

```bash
cd navigo-models

# 1. Once: build the Blender image (downloads Blender 4.2, about 350 MB; 3 to 10 minutes)
docker build -t navigo-blender .

# 2. Build every model into ../app/assets/models (10 to 12 minutes, previews included)
./build.sh

# 3. Look at the result
ls out/                  # matatu.png, bus.png… one contact sheet per model
```

Each `out/<model>.png` shows the model three ways: three-quarter front,
three-quarter rear, and from the navigation camera. That's how to check a
change before it reaches the app.

---

## The models

| File | Model | Size, m (L × W × H) | Triangles | File size |
|---|---|---|---|---|
| `matatu.glb` | Matatu, 14-seater (Toyota HiAce class) | 5.51 × 2.22 × 2.25 | 20,356 | 571 KB |
| `bus.glb` | Nganya, 33-seater (Isuzu NQR class) | 8.34 × 2.76 × 3.17 | 31,761 | 1,338 KB |
| `car.glb` | Car, compact wagon (Toyota Probox class) | 4.32 × 2.02 × 1.95 | 16,870 | 478 KB |
| `boda.glb` | Boda boda with rider and passenger | 1.99 × 0.78 × 1.80 | 13,882 | 732 KB |
| `bicycle.glb` | Bicycle (roadster) with rider | 1.89 × 0.82 × 1.83 | 6,724 | 399 KB |
| `train_sgr_loco.glb` | SGR locomotive (DF11 class) | 22.41 × 3.36 × 4.78 | 13,520 | 658 KB |
| `train_sgr_coach.glb` | SGR coach (25G class) | 26.94 × 3.13 × 4.58 | 8,138 | 373 KB |
| `train_commuter.glb` | Nairobi commuter train car (DMU) | 20.02 × 2.82 × 3.92 | 8,624 | 408 KB |
| `ferry.glb` | Likoni ferry, cars aboard | 72.0 × 18.1 × 17.6 | 10,310 | 523 KB |
| `plane.glb` | Narrow-body jet, no airline branding | 37.7 × 34.5 × 9.7 | 1,804 | 274 KB |
| `puck.glb` | Walking marker (arrow on a glowing disc) | 2.5 × 2.5 × 0.3 | 572 | 33 KB |

Sizes include mirrors and racks. The details people know on Nairobi's roads are
modelled: the matatu's sliding door on the nearside, the NTSA yellow band, white
front and yellow rear plates, the nganya's graffiti and neon, the boda rider's
reflective vest, the SGR's white and orange.

---

## Everyday tasks

### Rebuild one model after editing its script

```bash
./build.sh matatu            # one
./build.sh matatu bus car    # several
```

The script prints one line per model: triangles, file size, dimensions. A Python
error in a script prints its traceback instead; fix it and run the same command again.

### Build faster, without previews

```bash
RENDER=0 ./build.sh          # 6 to 8 minutes for all 11; no out/*.png or out/*_hero.jpg
```

A model takes about 25 seconds to build, and its previews about 20 more. The `.glb` files and `out/<model>.json` (the specs) are still written.

### Build for the mobile app (or anywhere else)

```bash
OUT=../mobile/assets/models ./build.sh
OUT=/tmp/models ./build.sh matatu
```

### See the models in 3D

The viewer shows every model in real time: a showroom, the navigation camera
(the vehicle drives along a road; trains run as full sets, the ferry on water,
the plane in the air), day, dusk and night light, and route or paint colours.

```bash
node build-viewer.js site            # page + models + studio renders into site/
npx --yes serve site                 # then open http://localhost:3000
```

Serve it as shown. Opening `site/index.html` straight from disk doesn't work,
because browsers block a local page from loading its own files. The studio
renders come from `./build.sh` with previews, so run it once without `RENDER=0` first.

A shared copy lives as a private Claude artifact ("Navigo Vehicle Models"). Its owner
can share it from the page's **Share** menu.

### Ship new or changed models to the app

The app follows the workspace's Git rules: a branch and a pull request, never a
commit on `main`.

```bash
./build.sh                                   # writes ../app/assets/models/*.glb
cd ../app
git checkout -b chore/update-vehicle-models
git add assets/models/*.glb
git commit -m "chore(models): rebuild the navigation models"
git push -u origin chore/update-vehicle-models
gh pr create                                 # describe what changed
```

Commit the models together with the script change in this repo, so the two never
drift apart.

---

## Add a new model

Say a tuk-tuk. Five steps here, three in the app.

**1. Write the script** `models/tuktuk.py`. Start from the closest existing
model (`car.py` for a road vehicle, `train_commuter.py` for a rail car). The
smallest working model looks like this:

```python
"""Tuk-tuk: a Bajaj RE-class three-wheeler (2.6 x 1.3 m)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bmesh  # noqa: E402

from kit import Kit, box  # noqa: E402

k = Kit("tuktuk", "Tuk-tuk")                       # file name, title
paint = k.mat("paint", "#F2C200", rough=0.25, coat=0.6)
glass = k.mat("glass", "#0B1118", rough=0.04)

bm = bmesh.new()
box(bm, (0, 0, 0.85), (1.30, 2.60, 1.20), 0, bevel=0.08)   # centre, size (m), material index
k.add("shell", bm, [paint])                         # parts go to the "body" group

bm = bmesh.new()
box(bm, (0, -1.31, 1.10), (1.10, 0.01, 0.50), 0)    # windscreen, at the front (-Y)
k.add("glass", bm, [glass], smooth=False, group="glass")

k.finish(bake={"body": 1024})                       # bake the body's texture, export, previews
```

The helpers in `kit.py` (`box`, `tube`, `lathe` for wheels, `loft`, `fillet` for
rounded profiles, `k.text` for plates and names) and in `people.py` (riders) cover
everything the existing models use. Read one existing script end to end before
writing a new one.

**2. Add it to the build.** Put `tuktuk` in the `ALL` list in `build.sh`.

**3. Build it and look:**

```bash
./build.sh tuktuk && open out/tuktuk.png      # or open the PNG from the file explorer
```

**4. Check the line it prints:** triangles under 35,000, file under 1.5 MB, and
no `WARNING`.

**5. Add it to the viewer:** an entry in `ITEMS` in `build-viewer.js` (title,
lede, speed in m/s, details).

**In the app** (`app/components/map/`):

1. `nav3d.ts`: add `"tuktuk"` to `VehicleModel`, its real length and on-screen
   size to `SIZE`, and the mode that uses it in `vehicleFor`.
2. `navModelAssets.ts`: `tuktuk: require("@/assets/models/tuktuk.glb")`.
3. `__tests__/nav3d.test.ts`: the mode returns the new model.

---

## How the app uses the models

| What | Where in `app/` |
|---|---|
| Which model a leg shows | `nav3d.ts` → `vehicleFor(mode, routeId)`. About one bus route in three shows the nganya (stable per route). Trains are drawn car by car along the line (`trainConsist`, `trainCars`). |
| How big it looks | `SIZE` in `nav3d.ts`: real length and on-screen length (px). The same on-screen size at every zoom. |
| Which way it faces | `MODEL_YAW_OFFSET = 180` in `nav3d.ts`. If a device shows models driving backwards, change this one number. |
| Glow at night | Materials named `headlight`, `taillight`, `indicator`, `neon…`, `beacon` glow with Mapbox's `modelEmissiveStrength` (`EMISSIVE` in `nav3d.ts`). |
| Loading | Bundled with the app (`navModelAssets.ts`), registered with the map only while navigating, and only the journey's models. |

The `livery` material (the matatu's route colour) and `paint` (the car's
colour) are separate materials on purpose, so they can be recoloured. The viewer
does it already; the app shows the default colours for now.

---

## How a build works

```
models/matatu.py  ──► kit.py: shapes, materials ──► merge parts by group
                                                   │
        out/matatu.png ◄── previews (Cycles) ◄── export .glb ◄── bake one texture per group:
        out/matatu.json ◄── specs                                ambient occlusion × dust (+ procedural art)
```

1. **Shapes.** The script builds parts with the kit. Most bodies are a side
   profile (with rounded corners and wheel arches) extruded to the vehicle's width,
   then rounded with a bevel. Wheels are lathed; trains and the plane are lofted.
2. **Groups.** Parts are merged per group: `body` by default, `glass` and
   `lights` (never baked), and one group per wheel or rider when they need their own
   texture. Repeated parts (wheels) are instances of one mesh.
3. **Bake.** Each baked group gets one texture: ambient occlusion (the soft
   shadows in wheel arches and under trim) times a light red-brown dust near the
   ground. It's multiplied into the materials' colours, so the models look grounded
   in any renderer. Procedural art (the nganya's graffiti, the plane's windows) is
   baked into the same texture.
4. **Export.** glTF binary, textures as JPEG (quality 80).
5. **Previews and specs.** A Cycles render from three angles, and a JSON file
   with the triangle count, file size, dimensions and materials.

---

## Rules every model follows

| Rule | Why |
|---|---|
| Metres. Blender Z up, the vehicle facing **-Y**. | The exported glTF then faces +Z (glTF's forward), which the app's yaw offset expects. |
| Origin on the ground, at the centre of the footprint (top of the rail for trains, the waterline for the ferry). | The app places a model's origin on the user's position. Nothing below the ground: the map has no water or underground. |
| Material names: `livery`, `paint` (recolourable); `headlight`, `taillight`, `indicator`, `neon…`, `beacon` (emissive); `glass…` (never baked). | The app and the viewer find materials by name. |
| No required glTF extensions. | Mapbox loads them. Clear-coat paint is used where supported and ignored elsewhere. |
| Budget: under 35,000 triangles and 1.5 MB. Textures at 1024 px, 2048 only for art. | Several models can be on screen, on low-end Android phones too. |
| No real brands or people: no logos, no airline or SACCO marks, faces hidden by helmets. | Licensing and taste. |

---

## Troubleshooting

| You see | Do this |
|---|---|
| `docker build` stops while downloading Blender (`unexpected eof`, `SSL`) | Run it again. The download resumes and retries on its own. |
| `pull access denied for navigo-blender` | The image isn't built yet: `docker build -t navigo-blender .` |
| `WARNING: nothing named 'x' to bake` | A name in `bake={…}` isn't a group. Parts go to `body` unless you gave them `group=…`; use those names. |
| A model is white or untextured | The bake didn't run (see the warning above), or a material's colour comes from shader nodes that weren't baked. |
| `Traceback (most recent call last)` | An error in the model's script; the last lines name the file and line. Fix it and rebuild that one model. |
| Paths like `C:\Program Files\Git\work` in Docker errors (Windows) | Run `build.sh` from Git Bash, which handles Windows paths (`cygpath`, `MSYS_NO_PATHCONV`). Not from PowerShell. |
| The viewer says "Couldn't load" | Serve it (`npx --yes serve site`) instead of opening the file. |
| Models drive backwards in the app | `MODEL_YAW_OFFSET` in `app/components/map/nav3d.ts`. |
| A model looks too big or too small in the app | Its entry in `SIZE` in `app/components/map/nav3d.ts`. |
| A file is too large | Lower its texture size in `k.finish(bake={…})` (1024 or 512), or simplify the geometry. |

---

## Files

| File | What |
|---|---|
| `models/*.py` | One script per model |
| `kit.py` | Shared helpers: profiles, lathes, lofts, boxes, tubes, text, the bake, the export, previews |
| `people.py` | Riders and passengers, posed so hands reach the grips and feet the pegs |
| `rail.py` | Rail car bodies, window rows, bogies |
| `build.sh` | Builds models (`OUT=`, `RENDER=0`, `IMAGE=`) |
| `Dockerfile` | Blender 4.2 LTS, headless |
| `build-viewer.js`, `viewer.template.html` | The 3D viewer |
| `out/` | Previews and specs (not committed) |

## Licence

The models and scripts are Navigo's own. Text on plates and signs uses
Blender's built-in font (DejaVu Sans, free licence), converted to geometry.
