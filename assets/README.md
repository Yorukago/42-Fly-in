# Fly-in theme assets

Drop PNG files in here to reskin the viewer. Anything you don't provide
falls back to the default colored shapes, so you can theme incrementally.

Recognized filenames (all optional):

- `background.png` — full window background, stretched to fit (900x700)
- `drone.png` — drone sprite, scaled to fit (roughly 16x16, square works best)
- `zone_normal.png` — normal zones (roughly 44x44)
- `zone_blocked.png` — blocked zones
- `zone_restricted.png` — restricted zones
- `zone_priority.png` — priority zones

Use PNG with a transparent background for round/irregular icons — square
images with alpha corners work fine too. Exact source resolution doesn't
matter much; images are scaled to fit automatically, but drawing them
reasonably close to the sizes above avoids blurry upscaling.
