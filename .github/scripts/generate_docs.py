import os
import subprocess
import re
import shutil
from pathlib import Path

# Configuration
REPO_ROOT = Path(__file__).parent.parent # Assumes script is in 'scripts/' directory
SOURCE_DIRS = ['src-local', 'testCases', 'postProcess']
DOCS_DIR = REPO_ROOT / 'docs'
README_PATH = REPO_ROOT / 'README.md'
INDEX_PATH = DOCS_DIR / 'index.html'
HTML_TEMPLATE_PATH = None # Optional: Path to a custom Pandoc HTML template
CSS_PATH = None # Optional: Path to a custom CSS file to copy


def find_source_files(root_dir, source_dirs):
    """Finds all .c and .h files in the specified source directories."""
    files = []
    for dir_name in source_dirs:
        src_path = root_dir / dir_name
        if src_path.is_dir():
            files.extend(src_path.rglob('*.c'))
            files.extend(src_path.rglob('*.h'))
    return files

def extract_documentation(file_path):
    """Extracts documentation comments (/** ... */) and code from a file."""
    content = file_path.read_text(encoding='utf-8', errors='ignore')
    # Basic extraction: treat /** */ blocks as Markdown, rest as code
    # A more sophisticated parser could handle inline comments, etc.
    # This regex finds /** ... */ blocks, making sure not to be too greedy
    # It assumes comments are properly formatted and don't contain '*/' inside.
    # It captures the comment content (group 1) and the code after it (group 2)
    # or just code if no comment precedes it (group 3).
    
    # Simplified approach: Extract /** */ as markdown, everything else as C code block
    in_doc_comment = False
    markdown_content = ""
    
    for line in content.splitlines():
        stripped_line = line.strip()
        if stripped_line.startswith('/**'):
            in_doc_comment = True
            # Remove start token, handle single-line comments
            comment_content = stripped_line[3:]
            if comment_content.endswith('*/'):
                 comment_content = comment_content[:-2].strip()
                 markdown_content += comment_content + "\n"
                 in_doc_comment = False
            else:
                 markdown_content += comment_content.strip() + "\n"
        elif in_doc_comment and stripped_line.endswith('*/'):
            in_doc_comment = False
            # Remove end token
            comment_content = stripped_line[:-2].strip()
            if comment_content:
                 markdown_content += comment_content + "\n"
        elif in_doc_comment:
            # Remove potential leading '*' often used in C comments
            if stripped_line.startswith('*'):
                markdown_content += stripped_line[1:].strip() + "\n"
            else:
                 markdown_content += stripped_line + "\n"
        elif not in_doc_comment and stripped_line:
            # This line is code. Wrap non-comment lines in a C code block later.
            # For now, just accumulate the raw content to ensure ordering is kept.
            # A better approach would be to structure markdown and code blocks distinctly.
            pass # We'll handle code formatting during Pandoc conversion

    # Create a basic Markdown structure: Doc comments + full code block
    # This needs refinement for better presentation.
    final_markdown = markdown_content
    final_markdown += "\n\n## Source Code\n"
    final_markdown += "\n```c\n"
    final_markdown += content # Add the original code
    final_markdown += "\n```\n"

    return final_markdown

def generate_html(markdown_content, output_html_path, file_path):
    """Converts Markdown content to HTML using Pandoc."""
    cmd = [
        'pandoc',
        '-f', 'markdown', # Input format
        '-t', 'html5',    # Output format
        '--metadata', f'title={file_path.name}', # Use filename as title
        '--standalone', # Create a full HTML document
        '--toc',        # Add table of contents
        '--highlight-style=pygments', # Syntax highlighting style
        '-o', str(output_html_path)
    ]
    if HTML_TEMPLATE_PATH:
        cmd.extend(['--template', str(HTML_TEMPLATE_PATH)])
    if CSS_PATH:
        cmd.extend(['--css', Path(CSS_PATH).name]) # Pandoc needs relative name if copied

    process = subprocess.run(cmd, input=markdown_content, text=True, capture_output=True, check=False)
    if process.returncode != 0:
        print(f"Error generating HTML for {file_path}:")
        print(process.stderr)
        return False
    return True

def generate_index(readme_path, index_path, generated_files, docs_dir, repo_root):
    """Generates index.html from README.md and adds links to generated files."""
    if not readme_path.exists():
        print(f"Warning: README.md not found at {readme_path}")
        readme_content = "# Project Documentation\n"
    else:
        readme_content = readme_path.read_text(encoding='utf-8')

    # Simple placeholder replacement or append links
    # You might want a specific marker like <!-- DOC_LINKS_START -->
    links_markdown = "\n## Generated Documentation\n\n"
    
    # Group links by top-level directory (src-local, testCases, etc.)
    grouped_links = {}
    for original_path, html_path in generated_files.items():
        relative_html_path = html_path.relative_to(docs_dir)
        relative_original_path = original_path.relative_to(repo_root)
        top_dir = relative_original_path.parts[0]
        if top_dir not in grouped_links:
            grouped_links[top_dir] = []
        grouped_links[top_dir].append(f"- [{relative_original_path}]({relative_html_path})")

    for top_dir in sorted(grouped_links.keys()):
         if top_dir in SOURCE_DIRS: # Only include specified source dirs
             links_markdown += f"### {top_dir}\n\n"
             links_markdown += "\n".join(sorted(grouped_links[top_dir]))
             links_markdown += "\n\n"

    # Append links to the end for simplicity, or use a placeholder
    final_readme_content = readme_content + links_markdown

    # Convert the combined README + links to HTML for index.html
    cmd = [
        'pandoc',
        '-f', 'markdown',
        '-t', 'html5',
        '--metadata', 'title=Project Documentation',
        '--standalone',
        '--toc',
        '--highlight-style=pygments',
        '-o', str(index_path)
    ]
    if CSS_PATH:
        cmd.extend(['--css', Path(CSS_PATH).name])

    process = subprocess.run(cmd, input=final_readme_content, text=True, capture_output=True, check=False)
    if process.returncode != 0:
        print("Error generating index.html:")
        print(process.stderr)
        return False
    return True

def main():
    """Main function to orchestrate documentation generation."""
    print("Starting documentation generation...")
    if DOCS_DIR.exists():
        print(f"Cleaning existing docs directory: {DOCS_DIR}")
        shutil.rmtree(DOCS_DIR)
    DOCS_DIR.mkdir(parents=True)

    source_files = find_source_files(REPO_ROOT, SOURCE_DIRS)
    print(f"Found {len(source_files)} source files to document.")

    generated_files = {}
    errors = 0

    for file_path in source_files:
        print(f"Processing: {file_path.relative_to(REPO_ROOT)}")
        relative_path = file_path.relative_to(REPO_ROOT)
        output_html_path = DOCS_DIR / relative_path.with_suffix('.html')
        output_html_path.parent.mkdir(parents=True, exist_ok=True)

        markdown_content = extract_documentation(file_path)

        if generate_html(markdown_content, output_html_path, file_path):
            generated_files[file_path] = output_html_path
        else:
            errors += 1

    if errors > 0:
        print(f"\nEncountered {errors} errors during HTML generation.")

    print("\nGenerating index.html...")
    if CSS_PATH and Path(CSS_PATH).exists():
        print(f"Copying CSS: {CSS_PATH} to {DOCS_DIR}")
        shutil.copy(CSS_PATH, DOCS_DIR)
    
    if not generate_index(README_PATH, INDEX_PATH, generated_files, DOCS_DIR, REPO_ROOT):
         print("Failed to generate index.html.")
         return

    print("\nDocumentation generation complete.")
    print(f"Output generated in: {DOCS_DIR}")

if __name__ == "__main__":
    main()
