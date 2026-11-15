# Findings

Things that turned out differently than expected while building Phase 1. Each one changed
the code, and each has a measurement behind it.

## The cameras run at 25 FPS, not 30

ffmpeg reported 30 FPS from both cameras at first. Those numbers came from the timestamps the
camera driver writes into each frame, which are nominal. Timing frame arrivals with the wall
clock gave 40 ms per frame: 25 FPS. The boards stretch exposure in dim light. `sirius check`
therefore fails below 24 FPS and only warns between 24 and 28.

## OpenCV could not get full speed out of these cameras

`cv2.VideoCapture` with DirectShow either negotiated uncompressed YUY2, which runs at 10 FPS at
720p, or MJPEG capped at 25 FPS, depending on the order the properties were set. Setting
everything at open time gave the same 25. ffmpeg reached the cameras' full rate, so capture
goes through ffmpeg. That also lets SIRIUS open a camera by its device path instead of by an
index Windows can reshuffle.

## Raw video over a pipe was the bottleneck

Having ffmpeg decode to raw BGR and send it over a pipe managed about 23 FPS: two 720p streams
of raw pixels are around 83 MB/s each. Passing the camera's own JPEG frames through unchanged
and decoding them in Python reached the full rate. Windows pipes also return partial reads,
which the first frame splitter did not handle; there is now a test for it.

## Opening two identical cameras at once sometimes fails

Starting both cameras at the same instant occasionally made one of them refuse to open. The
live source now starts the left camera, waits for its first frame, then starts the right.

## Two GPU libraries fought over one file

onnxruntime-gpu 1.32 is built for CUDA 13; PyTorch here is the CUDA 12.8 build. Each brought its
own `cudnn64_9.dll`, and a Windows process can only load one, so whichever loaded second
crashed. Downloading the CUDA 13 build of PyTorch stalled twice, so the fix went the other way:
onnxruntime-gpu is pinned to 1.26, a CUDA 12 build, and `depth/ffs.py` imports PyTorch first so
onnxruntime reuses its libraries.

## SGBM reports near things as far away

See [depth.md](depth.md). A surface 0.27 m away, inside the matcher's blind range, came back
partly as about 3 m. The half-resolution second pass fixed it.

## Single-camera depth is far off up close

A person about 0.45 m away read as 1.7 to 1.8 m with both the small and base Depth Anything
models. See [depth.md](depth.md).

## The learned stereo model is slower than its paper suggests

The downloadable Fast-FoundationStereo model takes 133 ms per frame on this laptop, against
about 50 ms quoted for smaller research versions on an RTX 3090.

## Speech: slow frames and flickering detections

Two problems showed up in the live logs, each now covered by a test:

- The first frame after start-up took 2.2 seconds while the models warmed up, and its alert
  was still spoken, because "too old" was measured in frame time rather than wall-clock time.
  Staleness now uses the wall clock, and the models are warmed before the cameras start.
- The same sentence was said twice in a few seconds because the detector lost an object for a
  moment and the tracker gave it a new identity. Identical sentences are now held back for
  5 seconds.

## The lenses are not where the boards are

Both boards sat level on the ruler by a phone's level app, yet matched features showed a
62 to 65 pixel vertical offset and about 2.2 degrees of roll between the images. The offset was
the same for near and far objects, which points to the lens modules being tilted on their
circuit boards rather than the cameras sitting at different heights. Calibration handles it.
