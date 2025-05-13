#!/usr/bin/env python3
"""
HTML Cleaner Script

This script removes empty anchor tags from HTML files that cause JavaScript syntax errors.
It specifically targets tags like <a id="" href="#"></a> which are being incorrectly inserted
during the documentation generation process.

Relationship to fix_empty_anchors.py:
    - clean_html.py: Uses BeautifulSoup for robust HTML parsing and sanitization. It can handle 
      malformed or complex HTML structure, including script tags. Requires the bs4 dependency.
      If BeautifulSoup is not available, falls back to using the same regex approach as 
      fix_empty_anchors.py.
    - fix_empty_anchors.py: A lightweight alternative using regex-only approach without external 
      dependencies. It works faster but is less robust with malformed HTML.

When to use which script:
    - Use clean_html.py when dealing with complex HTML or when you need robust sanitization
      (especially for HTML inside script tags)
    - Use fix_empty_anchors.py when you need a fast, dependency-free solution for well-formed HTML
      or when installing external dependencies is not possible

Dependencies:
    - beautifulsoup4 (BSD-licensed HTML/XML parser) - Optional
    - Install with: pip install -r requirements.txt

Usage:
    python clean_html.py --dir /path/to/html/files --verbose
"""

import os
import re
import argparse
import sys
import html
from html_cleaning_patterns import (
    EMPTY_ANCHOR_PATTERNS,
    SANITIZE_PATTERNS,
    SANITIZE_REPLACEMENTS,
    apply_empty_anchor_cleanup
)

# Check if BeautifulSoup is available
HAS_BEAUTIFULSOUP = False
try:
    from bs4 import BeautifulSoup
    HAS_BEAUTIFULSOUP = True
except ImportError:
    print("BeautifulSoup (bs4) not found. Falling back to regex-only approach.")
    HAS_BEAUTIFULSOUP = False

def sanitize_html(content):
    """
    Sanitize HTML content to prevent XSS vulnerabilities.

    Args:
        content: HTML content to sanitize

    Returns:
        str: Sanitized HTML content
    """
    if not content:
        return ""

    # First apply regex removals on the raw content
    sanitized_content = content
    
    # Apply all sanitization patterns from the shared module
    for key, pattern in SANITIZE_PATTERNS.items():
        replacement = SANITIZE_REPLACEMENTS[key]
        sanitized_content = re.sub(pattern, replacement, sanitized_content, flags=re.IGNORECASE)

    # Unescape first to prevent double-encoding from previous regex replacements
    sanitized_content = html.unescape(sanitized_content)
    
    # Finally, escape any remaining HTML special characters
    sanitized_content = html.escape(sanitized_content, quote=False)  # Don't escape quotes again

    return sanitized_content

def clean_html_file(file_path):
    """
    Removes empty anchor tags from an HTML file.
    Uses BeautifulSoup if available for robust handling of complex HTML,
    or falls back to direct regex replacement if BeautifulSoup is not available.

    Args:
        file_path: Path to the HTML file to clean

    Returns:
        Tuple (bool, int): Whether file was modified and count of tags removed
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Track initial length to estimate number of replacements
        initial_content_length = len(content)
        
        if HAS_BEAUTIFULSOUP:
            # BeautifulSoup approach - more robust but requires the dependency
            
            # First do a direct string replacement for empty anchor tags in the content
            # This is more reliable for script tags where BeautifulSoup might struggle
            content = apply_empty_anchor_cleanup(content)

            # Parse the HTML with BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')

            # Find all empty anchor tags
            empty_anchors = [a for a in soup.find_all('a') if not a.contents or (len(a.contents) == 1 and not a.contents[0].strip())]

            # Count the empty anchors before removing
            original_count = len(empty_anchors)

            # Remove the empty anchors found by BeautifulSoup if any exist
            for anchor in empty_anchors:
                anchor.decompose()

            # Special handling for script tags
            script_tags = soup.find_all('script')
            for script in script_tags:
                # Clean script content if it exists
                if script.string:
                    # First apply regex to remove problematic anchor tags with all their variations
                    script_content = script.string
                    script_content = apply_empty_anchor_cleanup(script_content)
                    
                    # Sanitize javascript: URLs as a safety measure
                    script_content = re.sub(SANITIZE_PATTERNS['javascript_urls'], 
                                           SANITIZE_REPLACEMENTS['javascript_urls'], 
                                           script_content, flags=re.IGNORECASE)
                    
                    # Update the script content
                    script.string = script_content

            # Convert the soup back to HTML
            cleaned_content = str(soup)

            # Perform a final direct replacement to catch any that might still remain
            # (especially within attributes or other places BeautifulSoup might miss)
            cleaned_content = apply_empty_anchor_cleanup(cleaned_content)
            
            # Approximate count of tags removed via regex
            regex_replacements = (initial_content_length - len(content)) // 20
            total_removed = original_count + regex_replacements
            
        else:
            # Regex-only approach - faster but less robust
            # Use the same approach as fix_empty_anchors.py for consistency
            cleaned_content = apply_empty_anchor_cleanup(content)
            
            # Calculate approximate number of replacements
            chars_removed = initial_content_length - len(cleaned_content)
            total_removed = chars_removed // 20  # Approximate size of each anchor tag

        # Write the cleaned content back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)

        return True, total_removed

    except Exception as e:
        print(f"Error cleaning {file_path}: {e}")
        return False, 0

def process_directory(directory, verbose=False):
    """
    Process all HTML files in a directory recursively.
    
    Args:
        directory: Root directory to search for HTML files
        verbose: Whether to print verbose output
    
    Returns:
        dict: Statistics about processed files
    """
    stats = {
        'total_files': 0,
        'modified_files': 0,
        'total_tags_removed': 0,
        'errors': 0
    }
    
    if verbose:
        print(f"Processing directory: {directory}")
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.html'):
                file_path = os.path.join(root, file)
                stats['total_files'] += 1
                
                try:
                    modified, tags_removed = clean_html_file(file_path)
                    
                    if modified:
                        stats['modified_files'] += 1
                        stats['total_tags_removed'] += tags_removed
                        
                        if verbose:
                            print(f"Cleaned {file_path}: removed {tags_removed} empty anchor tags")
                            
                except Exception as e:
                    stats['errors'] += 1
                    print(f"Error processing {file_path}: {e}")
    
    return stats

def main():
    """Main function to parse arguments and run the script."""
    parser = argparse.ArgumentParser(description='Clean HTML files by removing empty anchor tags')
    parser.add_argument('--dir', required=True, help='Directory containing HTML files to clean')
    parser.add_argument('--verbose', action='store_true', help='Print verbose output')
    args = parser.parse_args()
    
    if not os.path.isdir(args.dir):
        print(f"Error: {args.dir} is not a valid directory")
        sys.exit(1)
    
    stats = process_directory(args.dir, args.verbose)
    
    print("\nProcessing Summary:")
    print(f"Total files processed: {stats['total_files']}")
    print(f"Files modified: {stats['modified_files']}")
    print(f"Total empty anchor tags removed: {stats['total_tags_removed']}")
    print(f"Errors encountered: {stats['errors']}")
    
    if stats['modified_files'] > 0:
        print("\nEmpty anchor tags successfully removed from HTML files.")
    else:
        print("\nNo empty anchor tags found or all files were already clean.")

if __name__ == "__main__":
    main()