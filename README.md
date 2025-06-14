# PDF Editor

A feature-rich PDF editing tool written in Python.

## Features

* PDF whiteout functionality
* Text annotation capabilities
  - Add text anywhere on the PDF
  - Change text font size
  - Move text with drag and drop
  - Remove text annotations
* Page navigation with scrollbars
* Zoom in/out functionality
* Keyboard shortcuts for quick access
* Modern and intuitive user interface

## Requirements

* Python 3.x
* See `requirements.txt` for dependencies

## Usage

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the tool:
```bash
python pdf_whiteout.py
```

## Controls

### Text Mode
* Click 'Add Text' to enter text mode
* Click anywhere on the PDF to add text
* Left-click on existing text to change font size
* Right-click and drag to move text
* Use font size selector for new text
* Click 'Apply' to save text changes

### Erase Mode
* Use mouse drag to select area to erase
* Click 'Apply' to save erasures
* 'Unselect Latest' removes last selection
* 'Unselect All' clears all selections

### Navigation
* Up/Down Arrow: Navigate pages
* Mouse Wheel: Zoom In/Out
* Ctrl + S: Save PDF

## Project Structure

* `pdf_whiteout.py` - Main script for PDF editing
* `requirements.txt` - Python dependencies

---

**Repository:** https://github.com/medcharaf111/PDF-editor
