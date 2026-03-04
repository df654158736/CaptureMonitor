# Spec: Change Monitor

## ADDED Requirements

### Requirement: Configurable monitoring interval
The system SHALL allow users to configure the monitoring interval in seconds.

#### Scenario: Set monitoring interval
- **WHEN** user enters a value in the interval input field
- **THEN** system updates the monitoring interval to the specified value

#### Scenario: Default interval
- **WHEN** application starts
- **THEN** monitoring interval defaults to 2 seconds

### Requirement: Monitoring loop
The system SHALL continuously perform OCR on the selected region at the configured interval when monitoring is active.

#### Scenario: Start monitoring
- **WHEN** user clicks "Start Monitoring" button
- **THEN** system begins the monitoring loop
- **AND** performs OCR every N seconds (where N is the configured interval)

#### Scenario: Stop monitoring
- **WHEN** user clicks "Stop Monitoring" button
- **THEN** system stops the monitoring loop

### Requirement: Change detection
The system SHALL compare current OCR result with the previous result and detect changes.

#### Scenario: Detect text change
- **WHEN** current OCR text differs from previous OCR text
- **THEN** system triggers a change event with old and new values

#### Scenario: No change detected
- **WHEN** current OCR text is identical to previous OCR text
- **THEN** system does not trigger any change event

### Requirement: Plugin text processing
The system SHALL process OCR results through the active plugin before change detection.

#### Scenario: Process text through plugin
- **WHEN** OCR returns raw text
- **THEN** system calls the plugin's `process_text()` function
- **AND** uses the processed text for change detection

### Requirement: History recording
The system SHALL record all OCR results and changes to the history panel.

#### Scenario: Record successful OCR
- **WHEN** OCR completes successfully
- **THEN** system adds a timestamped entry to the history panel

#### Scenario: Record change event
- **WHEN** a change is detected
- **THEN** system formats the change using the plugin's `format_change()` function
- **AND** adds a highlighted entry to the history panel

### Requirement: History limit
The system SHALL maintain a maximum of 1000 history entries.

#### Scenario: Enforce history limit
- **WHEN** history reaches 1000 entries
- **THEN** system removes the oldest entry when adding a new entry
