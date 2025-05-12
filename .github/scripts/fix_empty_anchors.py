#!/usr/bin/env python3
"""
Direct HTML Fix Script for Empty Anchors

This script directly removes empty anchor tags from HTML files that cause JavaScript syntax errors.
It uses pure string replacement instead of BeautifulSoup to be more reliable.

Usage:
    python fix_empty_anchors.py <path_to_html_file>
"""

import sys
import re
import os
import glob

def fix_html_file(file_path):
    """
    Removes empty anchor tags from an HTML file using direct string replacement.
    
    Args:
        file_path: Path to the HTML file to clean
        
    Returns:
        int: Number of replacements made
    """
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Store original content length for comparison
        initial_content_length = len(content)
        
        # Patterns for empty anchor tags with various combinations
        patterns = [
            r'<a\s+id=[\'"]?[\'"]?\s*href=[\'"]?#[\'"]?\s*>\s*</a>',
            r'<a\s+id=[\'"]?[\'"]?\s*href=[\'"]?#[\'"]?\s*>\s*\n*\s*</a>',
            r'<a\s+href=[\'"]?#[\'"]?\s*id=[\'"]?[\'"]?\s*>\s*</a>',
            r'<a\s+href=[\'"]?#[\'"]?\s*id=[\'"]?[\'"]?\s*>\s*\n*\s*</a>',
            r'<a\s+id=\s*href=#\s*>\s*</a>'
        ]
        
        # Apply all patterns
        for pattern in patterns:
            content = re.sub(pattern, '', content)
        
        # Calculate approximate number of replacements
        final_content_length = len(content)
        chars_removed = initial_content_length - final_content_length
        replacements = chars_removed // 20  # Approximate size of each anchor tag
        
        # Only write back if changes were made
        if replacements > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed {file_path}: removed approximately {replacements} empty anchor tags")
        
        return replacements
        
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return 0

def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_empty_anchors.py <path>")
        sys.exit(1)
    
    path = sys.argv[1]
    
    if os.path.isfile(path):
        # Fix a single file
        fix_html_file(path)
    elif os.path.isdir(path):
        # Fix all HTML files in the directory and subdirectories
        html_files = glob.glob(os.path.join(path, '**', '*.html'), recursive=True)
        total_files = len(html_files)
        fixed_files = 0
        total_replacements = 0
        
        for file in html_files:
            replacements = fix_html_file(file)
            if replacements > 0:
                fixed_files += 1
                total_replacements += replacements
        
        print(f"\nSummary: Fixed {fixed_files} out of {total_files} files, removing approximately {total_replacements} empty anchor tags")
    else:
        print(f"Error: {path} is not a valid file or directory")
        sys.exit(1)

if __name__ == '__main__':
    main()