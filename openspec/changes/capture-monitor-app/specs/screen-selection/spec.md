# Spec: Screen Selection

## ADDED Requirements

### Requirement: Full-screen overlay window
The system SHALL provide a full-screen semi-transparent overlay window that covers the entire desktop area.

#### Scenario: Overlay window display
- **WHEN** user clicks "Show Monitor Frame" button
- **THEN** system displays a full-screen overlay window with semi-transparent background

#### Scenario: Overlay window persistence
- **WHEN** monitoring is stopped
- **THEN** overlay window remains visible (does not hide)

### Requirement: Draggable selection area
The system SHALL allow users to create and resize a rectangular selection area on the overlay window by dragging the mouse.

#### Scenario: Create selection area
- **WHEN** user clicks and drags on the overlay window
- **THEN** system creates a rectangular selection area following the mouse cursor

#### Scenario: Resize selection area
- **WHEN** user drags the edges or corners of an existing selection area
- **THEN** system updates the selection area dimensions accordingly

#### Scenario: Display selection coordinates
- **WHEN** a selection area exists
- **THEN** system displays the current coordinates (x, y, width, height) near the selection

### Requirement: Selection area data
The system SHALL maintain the current selection area coordinates for OCR capture.

#### Scenario: Get selection bounds
- **WHEN** OCR module requests the capture area
- **THEN** system returns the selection area as (x, y, width, height) coordinates

### Requirement: Independent window management
The overlay window SHALL operate independently from the main control window.

#### Scenario: Minimize main window
- **WHEN** user minimizes the main control window
- **THEN** overlay window remains visible and functional

#### Scenario: Toggle overlay visibility
- **WHEN** user clicks "Show/Hide Monitor Frame" button
- **THEN** system toggles the overlay window visibility
