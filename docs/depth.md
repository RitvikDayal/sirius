# Depth

SIRIUS has three ways to work out how far away things are. They share one interface,
`DepthEstimator`, and each returns a distance for every pixel (NaN where it has no answer),
measured from the midpoint between the two lenses.

| Method | `--depth` | Kind | Time per frame at 640x360 | Notes |
|---|---|---|---|---|
| SGBM | `sgbm` | stereo | 16.7 ms median, 17.9 ms p90 | Classical matching from OpenCV. Fast, no GPU needed. |
| Fast-FoundationStereo | `ffs` | stereo | 132.8 ms median, 142.0 ms p90 | NVIDIA's learned stereo model, run through onnxruntime on the GPU. |
| Depth Anything V2 metric indoor small | `mono` | single camera | about 14 ms | Guesses depth from one image. Used for comparison and as a stand-in before calibration. |

Times were measured on an RTX 5090 Laptop GPU.

## SGBM, with a near-range fix

Stereo matching searches a fixed range of pixel shifts (128 at 640 pixels wide, which on this
rig means anything closer than roughly 0.4 m is out of range). A test showed that when
something is closer than that, plain SGBM does not just fail: some pixels get matched to the
wrong place and come back reading about 3 m away. For a navigation aid that is the worst
possible error.

SIRIUS runs SGBM twice: once at full working resolution and once at half resolution, where
the same search range covers twice the shift. Where the half-resolution pass sees something
beyond the full pass's range, its value is used. Where the two disagree by more than 25%, the
pixel is marked invalid. The test `test_too_close_is_never_reported_far` places a surface at
0.27 m and checks that nothing in it reads further than 1 m and that the median is within 10%.
The second pass adds about a quarter to SGBM's time.

## Fast-FoundationStereo

The model comes from `nvidia/c-fast-foundationstereo` as an ONNX file with dynamic image size.
Inputs are two RGB images as float tensors; the output is a disparity map. Images are padded
on the bottom and right to a multiple of 32 so the camera geometry stays valid, and columns
where a match would fall outside the right image are marked invalid.

The published numbers (about 50 ms) are for smaller research checkpoints on an RTX 3090. The
downloadable model is the large variant and takes 133 ms here, over the 100 ms budget. It is
kept in the comparison for accuracy; speeding it up with TensorRT is only worth doing if it
clearly wins.

## Single-camera depth, and why it is not trusted

The single-camera model needs no calibration, which is why the dashboard uses it until the
stereo pair is calibrated. Its distances are estimates of scale from appearance, and on this
rig they are badly wrong up close. With a person about 0.45 m from the cameras (estimated from
the width of their face in the image), it reported 1.83 m live. Offline on the same frame, the
small model said 1.69 m and the base model 1.78 m. A bigger model of the same kind did not fix
it.

So SIRIUS never speaks a single-camera distance unless `speak_approx_distances = true`, and
then always with the word "about".

## Comparing the methods

The bake-off (`eval/bakeoff.py`) puts a printed ArUco marker at taped distances (0.5, 1, 2, 3
and 5 m), finds the marker in each frame, takes the median distance over its central 60%, and
compares that with the tape. It reports the error per method and distance, plus timing. The
default depth method is chosen by rule:

- only stereo methods qualify
- 90th-percentile time must be 100 ms or less
- error must be 10% or less up to 3 m and 20% or less at 5 m
- among those that pass, the one with the smallest worst-case error wins

If none qualifies, the command says so and leaves the choice to a person. The bake-off needs a
calibrated rig and has not been run yet.
