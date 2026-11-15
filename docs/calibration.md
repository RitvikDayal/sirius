# Calibration

Stereo depth works by measuring how far each point shifts between the left and right image.
That only gives real distances if the software knows each camera's focal length and lens
distortion, and exactly where the two cameras sit relative to each other. Calibration
measures all of that from pictures of a printed board with a known pattern.

On this rig it also has a second job: the two lenses point about 4 degrees apart vertically
and are rolled about 2.2 degrees relative to each other. Calibration produces a correction
that warps both images so that matching points lie on the same row, which is what the depth
algorithms expect.

## The board

SIRIUS uses a ChArUco board: a chessboard with small coded markers in the white squares. The
markers let the detector identify each corner even when part of the board is out of view.

| Setting in `config/rig.toml` | Default |
|---|---|
| `charuco.cols`, `charuco.rows` | 7 x 5 squares |
| `charuco.square_mm` | 35.0 |
| `charuco.marker_mm` | 26.0 |
| `charuco.dictionary` | `DICT_5X5_100` |

## Steps

1. Generate the board: `sirius board`. It writes `data/board.png` and `data/board.pdf`.
2. Print the PDF at 100% ("actual size", not "fit to page") on A4 landscape, and glue it to
   something flat and stiff. The board can also be shown full screen on a tablet.
3. Measure one black square and one marker with a ruler, to 0.1 mm, and put both numbers in
   the config. Printers and screens rarely reproduce sizes exactly, and every distance
   SIRIUS reports scales with this number.
4. Measure the distance between the two lens centres to 1 mm and set
   `baseline_mm_measured`.
5. Run `sirius calib-capture --out data/calib/<date>` and move the board slowly in front of
   the rig: near and far, left and right, tilted different ways. It saves a pair each time
   both cameras see at least 20 of the same corners and the board has moved more than 80
   pixels or changed size by more than 20% since the last save. It stops at 30 pairs.
6. Run `sirius calibrate data/calib/<date>`. It prints the reprojection error for each camera
   and the pair, and the baseline it measured, and saves `calib.npz`. Set `calibration` in the
   config to that file.
7. Run `sirius baseline-check`. It passes if the calibrated baseline is within 2% of your ruler
   measurement and if live rectified images line up to under 1 pixel vertically. Before
   calibration the offset is about 62 pixels.

After a passing check, do not touch the rig. Any shift of a board on the ruler invalidates the
calibration.

## How it works

`calib/stereo.py` calibrates each camera on its own first (focal length, centre, distortion),
then solves for the rotation and offset between them using only the corners both cameras saw
in the same picture. `cv2.stereoRectify` turns that into the two warps, and `calib/rectify.py`
applies them to every frame, then scales the images to the working resolution (640x360 by
default, `depth_scale = 0.5`).

The test `tests/test_calibration.py` renders the board into two virtual cameras that have
this rig's exact misalignment and checks that calibration finds the right spacing. It
recovers 117.87 mm for a true 117.0 mm (0.74% off) with a reprojection error of 0.31 pixels.

Real-rig calibration has not been run yet; see [status.md](status.md).
