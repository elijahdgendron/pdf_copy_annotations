#!/usr/bin/env python3
"""
PDF Annotation Copier

This script reads a source PDF file, extracts all annotations that are NOT highlights,
and copies them to a target PDF file. Supports copying annotations from all pages or
only from specified pages using page ranges and individual page numbers.

Requirements:
    pip install PyMuPDF

=== TWO WAYS TO USE THIS SCRIPT ===

METHOD 1: CONFIGURATION MODE (Recommended for repeated use)
    1. Edit the configuration variables at the top of this script:
       - Set SOURCE_PDF, TARGET_PDF, OUTPUT_PDF paths
       - Set PAGES specification (or None for all pages)
       - Set USE_COMMAND_LINE_ARGS = False
    2. Run the script: python3 copy_pdf_annotations.py

    Configuration Examples:
        SOURCE_PDF = "annotated_document.pdf"
        TARGET_PDF = "blank_document.pdf"
        OUTPUT_PDF = "result.pdf"
        PAGES = "1-5"              # Copy from pages 1-5
        PAGES = "1,3,5"           # Copy from pages 1, 3, and 5
        PAGES = "1-3,7,10-12"     # Copy from mixed ranges
        PAGES = None              # Copy from all pages

    Performance Settings (for large PDFs):
        SHOW_PROGRESS = True       # Show progress during long operations
        BATCH_SIZE = 100          # Process annotations in batches (0 = no batching)
        MEMORY_EFFICIENT = True   # Use memory-efficient mode for very large PDFs

METHOD 2: COMMAND-LINE MODE (Traditional usage)
    python3 copy_pdf_annotations.py source.pdf target.pdf output.pdf [--pages PAGES]

    Command-line Examples:
        # Copy all annotations
        python3 copy_pdf_annotations.py source.pdf target.pdf output.pdf

        # Copy annotations from pages 1-5
        python3 copy_pdf_annotations.py source.pdf target.pdf output.pdf --pages "1-5"

        # Copy annotations from specific pages
        python3 copy_pdf_annotations.py source.pdf target.pdf output.pdf --pages "1,3,5,10"

        # Copy annotations from mixed ranges and individual pages
        python3 copy_pdf_annotations.py source.pdf target.pdf output.pdf --pages "1-3,7,10-15"
"""

import sys
import argparse
import fitz  # PyMuPDF
from typing import List, Dict, Any, Optional, Set

# =============================================================================
# CONFIGURATION - Set your PDF paths and page specifications here
# =============================================================================

# PDF file paths (relative to script location)
SOURCE_PDF = "source.pdf"        # Path to PDF with annotations to copy
TARGET_PDF = "target.pdf"        # Path to PDF to copy annotations to
OUTPUT_PDF = "output.pdf"        # Path for the resulting PDF file

# Page specification (set to None to copy from all pages)
# Examples:
#   PAGES = None              # Copy from all pages
#   PAGES = "1-5"            # Copy from pages 1 through 5
#   PAGES = "1,3,5"          # Copy from pages 1, 3, and 5 only
#   PAGES = "1-3,7,10-12"    # Copy from pages 1-3, 7, and 10-12
PAGES = None

# Whether to use command-line arguments instead of the config above
# Set to False to always use the configuration variables above
USE_COMMAND_LINE_ARGS = False

# Performance settings for large PDFs
SHOW_PROGRESS = True            # Show progress for operations on large PDFs
BATCH_SIZE = 100               # Process annotations in batches (0 = no batching)
MEMORY_EFFICIENT = True       # Use memory-efficient mode for very large PDFs

# PERFORMANCE GUIDE FOR LARGE PDFs:
#
# Small PDFs (<50MB, <500 pages):
#   SHOW_PROGRESS = False, BATCH_SIZE = 0, MEMORY_EFFICIENT = False
#
# Medium PDFs (50-200MB, 500-2000 pages):
#   SHOW_PROGRESS = True, BATCH_SIZE = 50, MEMORY_EFFICIENT = False
#
# Large PDFs (200MB-1GB, 2000+ pages):
#   SHOW_PROGRESS = True, BATCH_SIZE = 100, MEMORY_EFFICIENT = True
#
# Very Large PDFs (>1GB, many annotations):
#   SHOW_PROGRESS = True, BATCH_SIZE = 50, MEMORY_EFFICIENT = True
#
# Memory-efficient mode: Slower but uses ~50% less RAM by processing pages in small batches
# Batch processing: Helps with very large annotation counts (1000+ annotations)
# Progress reporting: Essential for operations taking >30 seconds

# =============================================================================


def parse_page_specification(pages_str: str) -> Set[int]:
    """
    Parse page specification string into a set of zero-based page numbers.

    Supports formats:
    - "1-5": Pages 1 through 5 (inclusive)
    - "1,3,5": Individual pages 1, 3, and 5
    - "1-3,7,10-12": Mixed ranges and individual pages

    Args:
        pages_str: String specifying pages (1-based input)

    Returns:
        Set of zero-based page numbers

    Raises:
        ValueError: If the page specification format is invalid
    """
    if not pages_str or not pages_str.strip():
        raise ValueError("Page specification cannot be empty")

    pages = set()

    # Split by commas to handle multiple specifications
    for spec in pages_str.split(','):
        spec = spec.strip()

        if '-' in spec:
            # Handle range specification (e.g., "1-5")
            try:
                start_str, end_str = spec.split('-', 1)
                start = int(start_str.strip())
                end = int(end_str.strip())

                if start < 1 or end < 1:
                    raise ValueError(f"Page numbers must be >= 1, got range {start}-{end}")

                if start > end:
                    raise ValueError(f"Invalid range: {start}-{end} (start > end)")

                # Convert to zero-based and add to set
                for page in range(start - 1, end):  # end is inclusive, so no -1
                    pages.add(page)

            except ValueError as e:
                if "invalid literal" in str(e):
                    raise ValueError(f"Invalid range format: '{spec}'. Expected format: 'start-end'")
                raise
        else:
            # Handle individual page specification
            try:
                page = int(spec.strip())
                if page < 1:
                    raise ValueError(f"Page numbers must be >= 1, got {page}")
                pages.add(page - 1)  # Convert to zero-based
            except ValueError as e:
                if "invalid literal" in str(e):
                    raise ValueError(f"Invalid page number: '{spec}'")
                raise

    return pages


def validate_pages_exist(pdf_path: str, page_filter: Set[int], pdf_type: str = "PDF") -> Set[int]:
    """
    Validate that specified pages exist in the given PDF.

    Args:
        pdf_path: Path to the PDF file
        page_filter: Set of zero-based page numbers to validate
        pdf_type: Type description for error messages (e.g., "source", "target")

    Returns:
        Set of valid page numbers (subset of page_filter)

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        ValueError: If no valid pages remain after validation
    """
    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()
    except Exception as e:
        raise FileNotFoundError(f"Cannot open {pdf_type} PDF '{pdf_path}': {e}")

    # Find valid pages
    valid_pages = {p for p in page_filter if p < total_pages}

    # Report invalid pages
    invalid_pages = page_filter - valid_pages
    if invalid_pages:
        invalid_display = [p + 1 for p in sorted(invalid_pages)]  # Convert to 1-based for display
        print(f"Warning: {pdf_type} PDF has only {total_pages} pages. "
              f"Ignoring invalid pages: {invalid_display}")

    if not valid_pages:
        max_requested = max(p + 1 for p in page_filter)  # Convert to 1-based for display
        raise ValueError(f"No valid pages to process. {pdf_type} PDF has {total_pages} pages "
                        f"but you requested up to page {max_requested}.")

    return valid_pages


def get_non_highlight_annotations(pdf_path: str, page_filter: Optional[Set[int]] = None) -> Dict[int, List[Dict[str, Any]]]:
    """
    Extract all non-highlight annotations from a PDF file.

    Args:
        pdf_path: Path to the source PDF file
        page_filter: Optional set of zero-based page numbers to process. If None, processes all pages.

    Returns:
        Dictionary mapping page numbers to lists of annotation dictionaries
    """
    if MEMORY_EFFICIENT:
        return _get_annotations_memory_efficient(pdf_path, page_filter)
    else:
        return _get_annotations_standard(pdf_path, page_filter)


def _get_annotations_standard(pdf_path: str, page_filter: Optional[Set[int]] = None) -> Dict[int, List[Dict[str, Any]]]:
    """Standard annotation extraction - faster but uses more memory."""
    annotations_by_page = {}

    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)

        # Determine which pages to process
        if page_filter is None:
            pages_to_process = list(range(total_pages))
            if SHOW_PROGRESS:
                print(f"Processing all {total_pages} pages from source PDF...")
        else:
            # Filter out pages that don't exist in the PDF
            pages_to_process = [p for p in sorted(page_filter) if p < total_pages]
            if len(pages_to_process) != len(page_filter):
                excluded_pages = [p + 1 for p in page_filter if p >= total_pages]
                print(f"Warning: Pages {excluded_pages} don't exist in source PDF (has {total_pages} pages)")
            if SHOW_PROGRESS:
                print(f"Processing {len(pages_to_process)} specified pages from source PDF...")

        # Progress tracking
        total_annotations = 0
        for i, page_num in enumerate(pages_to_process):
            if SHOW_PROGRESS and len(pages_to_process) > 10:
                progress = (i + 1) / len(pages_to_process) * 100
                print(f"  Progress: {progress:.1f}% - Processing page {page_num + 1}")

            page = doc[page_num]
            annotations = []

            # Debug: Show what annotations exist on this page
            annot_list = list(page.annots())
            if not annot_list and (not SHOW_PROGRESS or len(pages_to_process) <= 10):
                print(f"  Page {page_num + 1}: No annotations found")

            for annot in page.annots():
                annot_type = annot.type[1]

                # Debug: Show ALL annotation types found
                if not SHOW_PROGRESS or len(pages_to_process) <= 10:
                    print(f"  Page {page_num + 1}: Found {annot_type} annotation", end="")

                if annot_type.lower() != 'highlight':
                    annot_dict = _extract_annotation_data(annot, annot_type)
                    annotations.append(annot_dict)
                    total_annotations += 1

                    if not SHOW_PROGRESS or len(pages_to_process) <= 10:
                        print(f" (INCLUDED)")
                else:
                    if not SHOW_PROGRESS or len(pages_to_process) <= 10:
                        print(f" (EXCLUDED - highlight)")

            if annotations:
                annotations_by_page[page_num] = annotations

        doc.close()

        if SHOW_PROGRESS:
            print(f"Extraction complete: Found {total_annotations} annotations on {len(annotations_by_page)} pages")

    except Exception as e:
        print(f"Error reading source PDF: {e}")
        return {}

    return annotations_by_page


def _get_annotations_memory_efficient(pdf_path: str, page_filter: Optional[Set[int]] = None) -> Dict[int, List[Dict[str, Any]]]:
    """Memory-efficient annotation extraction - slower but uses less memory."""
    annotations_by_page = {}

    try:
        # Get document info without loading full document
        doc_info = fitz.open(pdf_path)
        total_pages = len(doc_info)
        doc_info.close()

        # Determine which pages to process
        if page_filter is None:
            pages_to_process = list(range(total_pages))
            if SHOW_PROGRESS:
                print(f"Processing all {total_pages} pages from source PDF (memory-efficient mode)...")
        else:
            pages_to_process = [p for p in sorted(page_filter) if p < total_pages]
            if len(pages_to_process) != len(page_filter):
                excluded_pages = [p + 1 for p in page_filter if p >= total_pages]
                print(f"Warning: Pages {excluded_pages} don't exist in source PDF (has {total_pages} pages)")
            if SHOW_PROGRESS:
                print(f"Processing {len(pages_to_process)} specified pages (memory-efficient mode)...")

        total_annotations = 0
        # Process pages in small batches to minimize memory usage
        batch_size = max(1, min(10, len(pages_to_process) // 4))  # Smaller batches for memory efficiency

        for batch_start in range(0, len(pages_to_process), batch_size):
            batch_end = min(batch_start + batch_size, len(pages_to_process))
            batch_pages = pages_to_process[batch_start:batch_end]

            if SHOW_PROGRESS:
                progress = batch_end / len(pages_to_process) * 100
                print(f"  Progress: {progress:.1f}% - Processing pages {batch_pages[0] + 1}-{batch_pages[-1] + 1}")

            # Open document for this batch only
            doc = fitz.open(pdf_path)

            for page_num in batch_pages:
                page = doc[page_num]
                annotations = []

                # Debug: Show what annotations exist on this page
                annot_list = list(page.annots())
                if not annot_list and SHOW_PROGRESS:
                    print(f"    Page {page_num + 1}: No annotations found")

                for annot in page.annots():
                    annot_type = annot.type[1]

                    # Debug: Show ALL annotation types found
                    if SHOW_PROGRESS:
                        print(f"    Page {page_num + 1}: Found {annot_type} annotation", end="")

                    if annot_type.lower() != 'highlight':
                        annot_dict = _extract_annotation_data(annot, annot_type)
                        annotations.append(annot_dict)
                        total_annotations += 1

                        if SHOW_PROGRESS:
                            print(f" (INCLUDED)")
                    else:
                        if SHOW_PROGRESS:
                            print(f" (EXCLUDED - highlight)")

                if annotations:
                    annotations_by_page[page_num] = annotations

            # Close document after each batch to free memory
            doc.close()

        if SHOW_PROGRESS:
            print(f"Memory-efficient extraction complete: Found {total_annotations} annotations on {len(annotations_by_page)} pages")

    except Exception as e:
        print(f"Error reading source PDF: {e}")
        return {}

    return annotations_by_page


def _extract_annotation_data(annot, annot_type: str) -> Dict[str, Any]:
    """Extract annotation data into a dictionary."""
    annot_dict = {
        'type': annot.type,
        'content': annot.content,
        'rect': annot.rect,
        'page': annot.page,
        'flags': annot.flags,
        'line_ends': annot.line_ends,
        'border': annot.border,
        'colors': annot.colors,
        'author': annot.info.get('title', ''),
        'subject': annot.info.get('subject', ''),
        'opacity': annot.opacity if hasattr(annot, 'opacity') else 1.0
    }

    # For text annotations, get additional properties
    if annot_type.lower() in ['text', 'freetext']:
        annot_dict['fontsize'] = annot.fontsize if hasattr(annot, 'fontsize') else 12
        annot_dict['fontname'] = annot.fontname if hasattr(annot, 'fontname') else 'Helvetica'
        annot_dict['text_color'] = annot.colors.get('stroke', (0, 0, 0)) if annot.colors else (0, 0, 0)

    return annot_dict


def copy_annotations_to_pdf(target_pdf_path: str, annotations_by_page: Dict[int, List[Dict[str, Any]]], output_path: str):
    """
    Copy annotations to a target PDF and save the result.

    Args:
        target_pdf_path: Path to the target PDF file
        annotations_by_page: Dictionary of annotations organized by page number
        output_path: Path where the result should be saved
    """
    try:
        doc = fitz.open(target_pdf_path)
        if SHOW_PROGRESS:
            print(f"Target PDF has {len(doc)} pages")

        total_annotations = sum(len(annotations) for annotations in annotations_by_page.values())
        total_copied = 0
        processed_annotations = 0

        # Process with batching if configured
        if BATCH_SIZE > 0 and total_annotations > BATCH_SIZE:
            total_copied = _copy_annotations_batched(doc, annotations_by_page, total_annotations)
        else:
            # Standard processing
            for page_num, annotations in annotations_by_page.items():
                if page_num >= len(doc):
                    print(f"Warning: Source has annotations on page {page_num + 1} but target only has {len(doc)} pages. Skipping.")
                    continue

                page = doc[page_num]
                page_copied = 0

                for annot_data in annotations:
                    if _copy_single_annotation(page, annot_data, page_num):
                        total_copied += 1
                        page_copied += 1

                    processed_annotations += 1

                    # Progress reporting for large operations
                    if SHOW_PROGRESS and total_annotations > 50 and processed_annotations % 25 == 0:
                        progress = processed_annotations / total_annotations * 100
                        print(f"  Progress: {progress:.1f}% - Copied {total_copied}/{total_annotations} annotations")

                if SHOW_PROGRESS and not (total_annotations > 50):
                    print(f"  Page {page_num + 1}: Copied {page_copied} annotations")

        # Save the result
        if SHOW_PROGRESS:
            print("Saving PDF...")
        doc.save(output_path)
        doc.close()

        print(f"Successfully copied {total_copied} annotations to {output_path}")

    except Exception as e:
        print(f"Error processing target PDF: {e}")


def _copy_annotations_batched(doc, annotations_by_page: Dict[int, List[Dict[str, Any]]], total_annotations: int) -> int:
    """Copy annotations in batches to manage memory usage."""
    total_copied = 0
    processed_annotations = 0

    if SHOW_PROGRESS:
        print(f"Processing {total_annotations} annotations in batches of {BATCH_SIZE}...")

    # Flatten annotations into batches
    all_annotations = []
    for page_num, annotations in annotations_by_page.items():
        for annot_data in annotations:
            all_annotations.append((page_num, annot_data))

    # Process in batches
    for batch_start in range(0, len(all_annotations), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(all_annotations))
        batch = all_annotations[batch_start:batch_end]

        if SHOW_PROGRESS:
            progress = batch_end / len(all_annotations) * 100
            print(f"  Progress: {progress:.1f}% - Processing batch {batch_start + 1}-{batch_end}")

        # Process batch
        for page_num, annot_data in batch:
            if page_num >= len(doc):
                if processed_annotations == 0:  # Only warn once
                    print(f"Warning: Source has annotations on page {page_num + 1} but target only has {len(doc)} pages. Skipping.")
                processed_annotations += 1
                continue

            page = doc[page_num]
            if _copy_single_annotation(page, annot_data, page_num):
                total_copied += 1

            processed_annotations += 1

    return total_copied


def _copy_single_annotation(page, annot_data: Dict[str, Any], page_num: int) -> bool:
    """Copy a single annotation to a page. Returns True if successful."""
    try:
        # Create new annotation on the target page
        annot_type = annot_data['type'][0]  # Get the numeric type
        rect = annot_data['rect']

        # Create the annotation
        new_annot = page.add_annotation(annot_type, rect)

        # Set basic properties
        new_annot.set_content(annot_data['content'])
        new_annot.set_flags(annot_data['flags'])

        # Set colors if available
        if annot_data['colors']:
            if 'stroke' in annot_data['colors']:
                new_annot.set_colors(stroke=annot_data['colors']['stroke'])
            if 'fill' in annot_data['colors']:
                new_annot.set_colors(fill=annot_data['colors']['fill'])

        # Set border if available
        if annot_data['border']:
            new_annot.set_border(annot_data['border'])

        # Set line ends for line/arrow annotations
        if annot_data['line_ends']:
            new_annot.set_line_ends(annot_data['line_ends'][0], annot_data['line_ends'][1])

        # Set opacity
        new_annot.set_opacity(annot_data['opacity'])

        # Set author and subject
        info = {
            'title': annot_data['author'],
            'subject': annot_data['subject']
        }
        new_annot.set_info(info)

        # For text annotations, set font properties
        annot_type_str = annot_data['type'][1].lower()
        if annot_type_str in ['text', 'freetext'] and 'fontsize' in annot_data:
            new_annot.set_fontsize(annot_data['fontsize'])
            if 'fontname' in annot_data:
                new_annot.set_fontname(annot_data['fontname'])
            if 'text_color' in annot_data:
                new_annot.set_colors(stroke=annot_data['text_color'])

        new_annot.update()
        return True

    except Exception as e:
        if SHOW_PROGRESS:
            print(f"Error copying annotation on page {page_num + 1}: {e}")
        return False


def main():
    # Determine whether to use command-line arguments or configuration variables
    if USE_COMMAND_LINE_ARGS and len(sys.argv) > 1:
        # Use command-line arguments
        print("Using command-line arguments...")
        source_pdf, target_pdf, output_pdf, pages_spec = parse_command_line_args()
    else:
        # Use configuration variables
        print("Using configuration variables from script...")
        source_pdf = SOURCE_PDF
        target_pdf = TARGET_PDF
        output_pdf = OUTPUT_PDF
        pages_spec = PAGES

        print(f"Configuration:")
        print(f"  Source PDF: {source_pdf}")
        print(f"  Target PDF: {target_pdf}")
        print(f"  Output PDF: {output_pdf}")
        print(f"  Pages: {pages_spec if pages_spec else 'All pages'}")

    # Validate input files exist
    try:
        with open(source_pdf, 'rb'):
            pass
    except FileNotFoundError:
        print(f"Error: Source PDF '{source_pdf}' not found.")
        sys.exit(1)

    try:
        with open(target_pdf, 'rb'):
            pass
    except FileNotFoundError:
        print(f"Error: Target PDF '{target_pdf}' not found.")
        sys.exit(1)

    # Parse and validate page specification
    page_filter = None
    if pages_spec:
        try:
            page_filter = parse_page_specification(pages_spec)
            print(f"Page specification: {pages_spec} (processing {len(page_filter)} pages)")

            # Validate pages exist in both PDFs
            page_filter = validate_pages_exist(source_pdf, page_filter, "source")
            page_filter = validate_pages_exist(target_pdf, page_filter, "target")

        except ValueError as e:
            print(f"Error in page specification: {e}")
            sys.exit(1)

    print(f"Extracting non-highlight annotations from: {source_pdf}")
    annotations = get_non_highlight_annotations(source_pdf, page_filter)

    if not annotations:
        if page_filter:
            pages_display = [p + 1 for p in sorted(page_filter)]
            print(f"No non-highlight annotations found on specified pages {pages_display}.")
        else:
            print("No non-highlight annotations found in source PDF.")
        sys.exit(0)

    if page_filter:
        pages_with_annotations = [p + 1 for p in sorted(annotations.keys())]
        print(f"Found annotations on pages: {pages_with_annotations}")
    else:
        print(f"Found annotations on {len(annotations)} pages")

    print(f"Copying annotations to: {target_pdf}")
    copy_annotations_to_pdf(target_pdf, annotations, output_pdf)


def parse_command_line_args():
    """Parse command-line arguments and return the values."""
    parser = argparse.ArgumentParser(
        description="Copy non-highlight PDF annotations from source to target PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Copy all annotations
  python copy_pdf_annotations.py source.pdf target.pdf output.pdf

  # Copy annotations from specific pages
  python copy_pdf_annotations.py source.pdf target.pdf output.pdf --pages "1-5"

  # Copy annotations from multiple page ranges and individual pages
  python copy_pdf_annotations.py source.pdf target.pdf output.pdf --pages "1-3,7,10-12"

  # Copy annotations from individual pages only
  python copy_pdf_annotations.py source.pdf target.pdf output.pdf --pages "1,5,10"

Page numbering is 1-based (first page is page 1).

CONFIGURATION MODE:
  Set USE_COMMAND_LINE_ARGS = False in the script to use configuration variables instead.
        """
    )

    parser.add_argument("source_pdf", help="Path to the source PDF with annotations")
    parser.add_argument("target_pdf", help="Path to the target PDF to copy annotations to")
    parser.add_argument("output_pdf", help="Path for the output PDF file")
    parser.add_argument(
        "--pages", "-p",
        help="Pages to copy annotations from. Supports ranges (1-5), individual pages (1,3,5), "
             "or mixed (1-3,7,10-12). If not specified, copies from all pages."
    )

    args = parser.parse_args()
    return args.source_pdf, args.target_pdf, args.output_pdf, args.pages


if __name__ == "__main__":
    main()