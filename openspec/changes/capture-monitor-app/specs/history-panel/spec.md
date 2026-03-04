# Spec: History Panel

## ADDED Requirements

### Requirement: Independent draggable window
The history panel SHALL be an independent window that users can drag to any position on screen.

#### Scenario: Drag history panel
- **WHEN** user clicks and drags the history panel title bar
- **THEN** panel moves with the mouse cursor
- **AND** maintains its new position after release

#### Scenario: Default position
- **WHEN** history panel is first displayed
- **THEN** panel appears below the monitoring selection area

### Requirement: History display
The system SHALL display all OCR results and changes in chronological order with timestamps.

#### Scenario: Display entry
- **WHEN** a new OCR result is recorded
- **THEN** system adds an entry with format "[HH:MM:SS] plugin_name: content"

#### Scenario: Display change entry
- **WHEN** a change is detected
- **THEN** system adds a highlighted entry with the formatted change
- **AND** includes a warning symbol (⚠️)

### Requirement: History scrolling
The history panel SHALL support scrolling to view all entries.

#### Scenario: Scroll history
- **WHEN** user scrolls the history panel
- **THEN** panel displays entries within the visible range

#### Scenario: Auto-scroll to latest
- **WHEN** a new entry is added
- **THEN** panel automatically scrolls to show the latest entry

### Requirement: History limit enforcement
The system SHALL maintain a maximum of 1000 entries, removing oldest when limit is exceeded.

#### Scenario: Enforce 1000 entry limit
- **WHEN** history reaches 1000 entries
- **THEN** system removes the oldest entry before adding a new entry

### Requirement: Clear history
The system SHALL provide a button to clear all history entries.

#### Scenario: Clear all entries
- **WHEN** user clicks "Clear" button
- **THEN** system removes all history entries
- **AND** displays an empty history panel

### Requirement: Export history
The system SHALL provide a button to export history entries to a file.

#### Scenario: Export to text file
- **WHEN** user clicks "Export" button
- **THEN** system opens a file save dialog
- **AND** saves all history entries to the selected file in plain text format

### Requirement: Panel persistence
The history panel SHALL remain visible when the main control window is minimized.

#### Scenario: Main window minimized
- **WHEN** user minimizes the main control window
- **THEN** history panel remains visible and functional
