# Alerts and voice

The research behind SIRIUS kept pointing the same way: blind users want short, prioritised
information that leaves their ears free for traffic, not a running commentary. The rules
below try to do that.

## What gets said

An alert names the object, its distance in plain words, and its direction:

> person, one metre, ahead
>
> chair, two metres, left
>
> bottle, right

| Distance | Spoken as |
|---|---|
| under 0.75 m | half a metre |
| under 1.5 m | one metre |
| under 2.5 m | two metres |
| under 3.5 m | three metres |
| under 4.5 m | four metres |
| further | five metres |

Direction is "left" beyond 15 degrees to the left, "right" beyond 15 degrees to the right,
and "ahead" in between. Some labels are spoken more naturally: "dining table" becomes "table",
"potted plant" becomes "plant", "tv" becomes "TV".

Only these classes are announced: person, chair, couch, bed, dining table, bench, bicycle,
car, motorcycle, dog, potted plant, tv, laptop, backpack, suitcase, bottle, cup.

## Zones and priority

| Zone | Distance |
|---|---|
| urgent | under 1 m |
| near | 1 to 2.5 m |
| aware | 2.5 to 5 m |
| silent | 5 m or more |

Each frame produces at most one alert: the most urgent new thing. Ties go to the closer
object, then the one nearer straight ahead. Objects without a distance come last.

## When it stays quiet

- The same object is not announced again unless it changes zone or 5 seconds have passed.
- The same sentence is not repeated within 5 seconds, even if the detector briefly lost the
  object and now thinks it is a new one.
- An object announced without a distance is announced only once.
- If an alert is more than 1 second old by the time it could be spoken, measured by the wall
  clock from when the camera frame arrived, it is dropped. This covers slow frames as well as
  waiting for the voice.
- While the voice is speaking, a new alert waits as the single pending alert, and a newer one
  replaces it. A pending alert is dropped if its object leaves the zone or the view.
- An urgent alert interrupts whatever is being said.

## When distances are left out

The distance is dropped and only the object and direction are spoken when:

- either camera's newest frame is more than 200 ms old, or a camera image is dark (covered
  or failed)
- under half of the object's central area has valid depth
- the depth comes from the single-camera model, unless `speak_approx_distances` is on, in
  which case it is spoken with "about": "person, about two metres, ahead"

## The voice

Speech uses the Windows speech engine (SAPI) through `pywin32`. It runs offline. The first
phrase after start-up took 227 ms to begin because the audio device has to open, so SIRIUS
speaks a silent phrase at start-up. After that, speech starts in about 50 ms (median of 8
measurements, each interrupting the previous one).

The dashboard's mute button silences the voice and cuts off anything being said. Alerts keep
being decided while muted and are logged under `muted` rather than `spoken`.
