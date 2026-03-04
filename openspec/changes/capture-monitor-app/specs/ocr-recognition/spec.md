# Spec: OCR Recognition

## ADDED Requirements

### Requirement: Multiple OCR engines
The system SHALL support at least two OCR engines: PaddleOCR and Windows OCR API.

#### Scenario: Select OCR engine
- **WHEN** user selects an OCR engine from the dropdown
- **THEN** system uses the selected engine for all OCR operations

#### Scenario: Default OCR engine
- **WHEN** application starts for the first time
- **THEN** system defaults to PaddleOCR engine

### Requirement: Chinese text recognition
The system SHALL accurately recognize Chinese text from captured images.

#### Scenario: Recognize Chinese text
- **WHEN** OCR engine processes an image containing Chinese characters
- **THEN** system returns the recognized text with at least 90% accuracy for clear text

### Requirement: Text extraction from screen region
The system SHALL capture the specified screen region and extract text content.

#### Scenario: Capture and OCR
- **WHEN** monitor module requests OCR on a region (x, y, width, height)
- **THEN** system captures that screen region and returns the recognized text as a string

#### Scenario: Handle empty region
- **WHEN** OCR is performed on a region with no text
- **THEN** system returns an empty string

### Requirement: OCR error handling
The system SHALL handle OCR engine failures gracefully.

#### Scenario: OCR engine failure
- **WHEN** OCR engine fails to process an image
- **THEN** system logs the error and returns an empty string
- **AND** system continues monitoring without crashing

#### Scenario: OCR engine unavailable
- **WHEN** selected OCR engine is not available
- **THEN** system displays an error message to the user
- **AND** suggests switching to the available OCR engine
