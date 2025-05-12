#!/usr/bin/env python3
"""
HTML Cleaner Script

This script removes empty anchor tags from HTML files that cause JavaScript syntax errors.
It specifically targets tags like <a id="" href="#"></a> which are being incorrectly inserted
during the documentation generation process.

Usage:
    python clean_html.py --dir /path/to/html/files --verbose
"""

import os
import argparse
import sys
from bs4 import BeautifulSoup

def clean_html_file(file_path):
    """
    Removes empty anchor tags from an HTML file using BeautifulSoup.
    
    Args:
        file_path: Path to the HTML file to clean
        
    Returns:
        Tuple (bool, int): Whether file was modified and count of tags removed
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse the HTML with BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find all empty anchor tags
        empty_anchors = [a for a in soup.find_all('a') if not a.contents or (len(a.contents) == 1 and not a.contents[0].strip())]
        
        # Count the empty anchors before removing
        original_count = len(empty_anchors)
        
        if original_count == 0:
            return False, 0
            
        # Remove the empty anchors
        for anchor in empty_anchors:
            anchor.decompose()
        
        # Special handling for script tags
        script_tags = soup.find_all('script')
        for script in script_tags:
            # Find any anchor tags within script content and remove them
            if script.string:
                # Keep the original script content as a reference
                script_content = script.string
                
                # Create a temporary soup object for the script content
                # This is a safe way to parse and modify the script content
                script_soup = BeautifulSoup(f"<div>{script_content}</div>", 'html.parser')
                
                # Find and remove any anchor tags in the script content
                for anchor in script_soup.find_all('a'):
                    anchor.decompose()
                
                # Get the cleaned content (excluding the wrapping div)
                cleaned_script = script_soup.div.decode_contents() if script_soup.div else ""
                
                # Update the script content
                script.string = cleaned_script
        
        # Convert the soup back to HTML
        cleaned_content = str(soup)
        
        # Write the cleaned content back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
            
        return True, original_count
    
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