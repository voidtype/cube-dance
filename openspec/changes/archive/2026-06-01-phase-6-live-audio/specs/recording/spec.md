## ADDED Requirements

### Requirement: Recording is video-only for a live source

When recording with a live input source, the recorder SHALL produce a **video-only** clip
(no audio mux), because a live feed has no stored sample buffer to mux. Recording from a file
source SHALL continue to mux audio as before.

#### Scenario: Live recording has no audio mux

- **WHEN** a recording is made while running from the live input
- **THEN** the output clip is written video-only without attempting to mux file samples
