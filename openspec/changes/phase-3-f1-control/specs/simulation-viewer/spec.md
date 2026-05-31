## ADDED Requirements

### Requirement: Controls overlay toggle

The viewer SHALL toggle the virtual F1 controls overlay with the **`C`** key. While the
overlay is shown, the viewer SHALL **release the mouse** (detach fly-mode look) and
**freeze camera movement** so the cursor drives the panel instead of the camera. Hiding the
overlay SHALL restore the previous navigation behaviour.

#### Scenario: C shows the panel and frees the mouse

- **WHEN** the user presses `C`
- **THEN** the controls overlay appears, the mouse is released (no fly-look), and camera
  movement is frozen
- **WHEN** the user presses `C` again
- **THEN** the overlay hides and normal navigation resumes
