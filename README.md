# PDF Annotation Copier

A Python script that copies all non-highlight annotations from one PDF file to another PDF file with the same number of pages.

## Features

- Extracts all annotations except highlights from a source PDF
- Copies annotations to corresponding pages in a target PDF
- Preserves annotation properties like colors, borders, opacity, and text formatting
- Supports various annotation types: text notes, drawings, stamps, etc.

## Installation

1. Install the required dependency:
```bash
pip install -r requirements.txt
```

Or install directly:
```bash
pip install PyMuPDF
```

## Usage

```bash
python copy_pdf_annotations.py <source.pdf> <target.pdf> <output.pdf>
```

### Parameters:
- `source.pdf`: The PDF file containing the annotations you want to copy
- `target.pdf`: The PDF file where you want to paste the annotations (must have same number of pages)
- `output.pdf`: The name for the resulting PDF file with copied annotations

### Example:
```bash
python copy_pdf_annotations.py annotated_document.pdf blank_document.pdf result_with_annotations.pdf
```

## Supported Annotation Types

The script copies all annotation types EXCEPT highlights, including:
- Text notes/comments
- Free text annotations
- Drawings and shapes
- Stamps
- Ink/pen annotations
- Geometric shapes (rectangles, circles, etc.)

## Requirements

- Python 3.6 or higher
- PyMuPDF library
- Both PDFs must have the same number of pages

## Error Handling

The script includes error handling for:
- Missing input files
- PDF reading/writing errors
- Page count mismatches
- Individual annotation copying failures

## Notes

- Highlights are specifically excluded as they often interfere with readability
- Annotations are copied to the same page numbers in the target PDF
- If the source PDF has more pages than the target, extra annotations are skipped with a warning
- Original PDFs are not modified - only the output file is created# pdf_copy_annotations
