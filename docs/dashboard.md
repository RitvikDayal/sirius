# Dashboard

`sirius view` serves a page at http://127.0.0.1:8765. It only listens on the local machine.

## Panels

| Panel | Shows |
|---|---|
| Header | frames per second for the whole loop and each camera, depth method and its time, detector time, step time, calibration state, camera health, colour saturation of each camera, voice state, and the last sentence spoken |
| Left camera, right camera | the images the pipeline works on: rectified after calibration, resized before it |
| Depth | the depth map, warm colours near and cool colours far (0.3 to 6 m), black where there is no answer |
| Objects | the left image with a box per detected object, labelled with its distance. A `~` before the distance means it is a single-camera estimate. Box colour follows the zone: red urgent, orange near, green aware, grey otherwise |
| 3D view | a point cloud of the current frame. Drag to orbit, scroll to zoom |
| Mute button | silences the voice immediately and cuts off speech in progress |

Camera health turns red when a camera's frames are stale or dark, and the saturation figure
turns amber when the two cameras' colour differs by more than three times, which usually
means one board has switched to infrared.

With the full pipeline and voice on, the dashboard ran at about 15 to 16 frames per second
on the development laptop.

## How the 3D view is made

There is no 3D scanning involved. Each frame:

1. The depth model gives a depth value for every pixel of the left image.
2. Every third pixel is turned into a point in space using the camera's focal length and
   centre: `x = (u - cx) * z / fx - baseline/2`, `y = (v - cy) * z / fy`, and `z` from depth.
   The origin is the midpoint between the lenses.
3. Each point takes the colour of its pixel. Points with no depth, or further than 8 m, are
   skipped.
4. The points are sent to the browser as raw binary (a count, then float32 positions, then
   bytes for colour), and three.js draws them. The page fetches a new set about every 150 ms.

It is rebuilt from scratch every frame, so it shows what the cameras see right now. A map
that builds up as you walk around would need the rig's movement tracked between frames, which
is not part of Phase 1. Before calibration the 3D view uses the single-camera depth, so its
scale is wrong for anything close; see [depth.md](depth.md).

## Endpoints

| Path | Returns |
|---|---|
| `/` | the page |
| `/stream/<name>` | an MJPEG stream for `left`, `right`, `depth` or `objects` |
| `/stats` | the header values as JSON |
| `/points` | the current point cloud as binary |
| `/control` (POST) | `{"mute": true}` or `false`; returns the current controls |
| `/static/<file>` | the bundled three.js files |

The page loads three.js r160 from `/static/`, so it works without an internet connection.
