## ADDED Requirements

### Requirement: Spatial region groupings

The model SHALL expose **spatial region groupings** as pixel-index sets derived from pixel
positions: **left/right** (X < 0 / X > 0), **bottom/top** (Y), and **front/back** (Z).
Together with the existing per-edge, per-corner, and edge/corner group sets, these let a
visual address regions such as "left corners" or "the beams" without re-deriving geometry.
Each grouping SHALL partition the pixels into its two halves (a pixel is in exactly one
side of each axis split).

#### Scenario: Left/right split covers all pixels once

- **WHEN** the left and right region sets are taken
- **THEN** every pixel is in exactly one of them, matching the sign of its X coordinate

#### Scenario: Region intersection targets a sub-region

- **WHEN** the corner pixels are intersected with the left region
- **THEN** the result is exactly the pixels of the left-hand corners
