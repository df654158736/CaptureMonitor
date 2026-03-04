# Spec: Plugin System

## ADDED Requirements

### Requirement: Plugin discovery
The system SHALL automatically discover all Python files (.py) in the `./plugins/` directory at startup.

#### Scenario: Discover plugins on startup
- **WHEN** application starts
- **THEN** system scans the `./plugins/` directory
- **AND** loads all valid Python files as plugins

### Requirement: Plugin contract
Each plugin MUST be a Python file that implements the following functions:
- `plugin_info()`: Returns plugin metadata (name, description, version)
- `process_text(text: str) -> str`: Processes raw OCR text
- `format_change(old: str, new: str) -> str`: Formats change for display

#### Scenario: Valid plugin structure
- **WHEN** a Python file contains all required functions
- **THEN** system loads it as an available plugin

#### Scenario: Invalid plugin structure
- **WHEN** a Python file is missing required functions
- **THEN** system skips the file and logs a warning

### Requirement: Plugin selection
The system SHALL allow users to select an active plugin from a dropdown menu.

#### Scenario: Display available plugins
- **WHEN** user views the plugin dropdown
- **THEN** system displays all discovered plugins by name

#### Scenario: Select plugin
- **WHEN** user selects a plugin from the dropdown
- **THEN** system sets that plugin as the active plugin
- **AND** uses it for all subsequent text processing

### Requirement: Plugin error handling
The system SHALL handle plugin errors gracefully without crashing the application.

#### Scenario: Plugin process_text error
- **WHEN** active plugin's `process_text()` raises an exception
- **THEN** system logs the error
- **AND** returns the original unprocessed text

#### Scenario: Plugin format_change error
- **WHEN** active plugin's `format_change()` raises an exception
- **THEN** system logs the error
- **AND** uses a default format: "old → new"

### Requirement: Plugin identification
Each plugin SHALL be identified by its filename (without .py extension).

#### Scenario: Plugin ID from filename
- **WHEN** system loads `subtitle.py`
- **THEN** plugin ID is "subtitle"
