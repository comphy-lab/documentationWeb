import os
import subprocess
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Any, Union

# Configuration
# Assume the script is in .github/scripts, REPO_ROOT is the parent of .github
REPO_ROOT = Path(__file__).parent.parent.parent
SOURCE_DIRS = ['src-local', 'testCases', 'postProcess']  # Directories within REPO_ROOT to scan
DOCS_DIR = REPO_ROOT / 'docs'
README_PATH = REPO_ROOT / 'README.md'
INDEX_PATH = DOCS_DIR / 'index.html'
# --- New configuration based on page2html ---
BASILISK_DIR = REPO_ROOT / 'basilisk'  # Assuming basilisk dir is at the root
DARCSIT_DIR = BASILISK_DIR / 'src' / 'darcsit'
TEMPLATE_PATH = REPO_ROOT / '.github' / 'assets' / 'custom_template.html'  # Use the modified local template
LITERATE_C_SCRIPT = DARCSIT_DIR / 'literate-c'  # Path to the literate-c script
BASE_URL = "/"  # Relative base URL for links within the site
CSS_PATH = REPO_ROOT / '.github' / 'assets' / 'custom_styles.css'  # Path to custom CSS


def extract_h1_from_readme(readme_path: Path) -> str:
    """
    Extracts the first h1 heading from README.md
    
    Args:
        readme_path: Path to the README.md file
        
    Returns:
        The extracted h1 text or default text if not found
    """
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Look for # Heading pattern
            h1_match = re.search(r'^# (.+)$', content, re.MULTILINE)
            if h1_match:
                return h1_match.group(1).strip()
            else:
                print("Warning: No h1 heading found in README.md")
                return "Documentation"
    except Exception as e:
        print(f"Error reading README.md: {e}")
        return "Documentation"


# Dynamically get the wiki title from README.md
WIKI_TITLE = extract_h1_from_readme(README_PATH)


def validate_config() -> bool:
    """
    Validates the essential configuration paths exist.
    
    Returns:
        True if all required paths exist, False otherwise
    """
    essential_paths = [
        (BASILISK_DIR, "BASILISK_DIR"),
        (DARCSIT_DIR, "DARCSIT_DIR"),
        (TEMPLATE_PATH, "TEMPLATE_PATH"),
        (LITERATE_C_SCRIPT, "literate-c script")
    ]

    for path, name in essential_paths:
        if not (path.is_dir() if name.endswith("DIR") else path.is_file()):
            print(f"Error: {name} not found at {path}")
            return False
    return True


def find_source_files(root_dir: Path, source_dirs: List[str]) -> List[Path]:
    """
    Finds all .c, .h, .py, and .sh files in the specified source directories.
    Also finds .sh files in the root directory.
    
    Args:
        root_dir: Root directory of the project
        source_dirs: List of directory names to search within
        
    Returns:
        List of Path objects for found source files
    """
    files = []
    # Search in source directories
    for dir_name in source_dirs:
        src_path = root_dir / dir_name
        if src_path.is_dir():
            files.extend(src_path.rglob('*.c'))
            files.extend(src_path.rglob('*.h'))
            files.extend(src_path.rglob('*.py'))
            files.extend(src_path.rglob('*.sh'))
    
    # Also search for .sh files directly in the root directory
    for sh_file in root_dir.glob('*.sh'):
        files.append(sh_file)
        
    return files


def process_markdown_file(file_path: Path) -> str:
    """
    Process markdown file content for HTML conversion.
    
    Args:
        file_path: Path to the markdown file
        
    Returns:
        Content ready for pandoc conversion
    
    Raises:
        Exception: If file reading fails
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        file_content = f.read()
    return file_content


def process_shell_file(file_path: Path) -> str:
    """
    Process shell file content for HTML conversion.
    Wraps the content in a bash code block.
    
    Args:
        file_path: Path to the shell file
        
    Returns:
        Content wrapped in bash code block
    
    Raises:
        Exception: If file reading fails
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        file_content = f.read()
    return f"```bash\n{file_content}\n```"


def process_python_file(file_path: Path) -> str:
    """
    Process Python file content for HTML conversion.
    Separates docstrings, comments and code for better documentation.
    
    Args:
        file_path: Path to the Python file
        
    Returns:
        Processed content ready for pandoc conversion
    
    Raises:
        Exception: If file reading fails
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        file_content = f.read()
    
    lines = file_content.split('\n')
    processed_lines = []
    in_code_block = False
    code_block = []
    in_docstring = False
    docstring_lines = []
    
    for line in lines:
        # Check for docstring comments (triple quotes)
        if line.strip().startswith('"""') or line.strip().startswith("'''"):
            # If we're in a docstring, end it
            if in_docstring:
                in_docstring = False
                # Add the docstring as text, but skip any lines that only contain quotes
                clean_docstring = []
                for doc_line in docstring_lines:
                    # Skip lines that only contain quotes
                    if doc_line.strip() in ('"""', "'''"):
                        continue
                    # Remove starting/ending quotes from lines that have content
                    doc_line = doc_line.strip()
                    if doc_line.startswith('"""') or doc_line.startswith("'''"):
                        doc_line = doc_line[3:]
                    if doc_line.endswith('"""') or doc_line.endswith("'''"):
                        doc_line = doc_line[:-3]
                    clean_docstring.append(doc_line.strip())
                
                # Only add non-empty lines
                if clean_docstring:
                    processed_lines.append("")
                    processed_lines.extend(clean_docstring)
                    processed_lines.append("")
                docstring_lines = []
            else:
                # Start a new docstring
                in_docstring = True
                # If we're in a code block, end it
                if in_code_block:
                    processed_lines.append("```python")
                    processed_lines.extend(code_block)
                    processed_lines.append("```")
                    code_block = []
                    in_code_block = False
            continue
        
        # If we're in a docstring, add the line to docstring_lines
        if in_docstring:
            docstring_lines.append(line)
            continue
        
        # For regular code lines (including # comments)
        if not in_code_block and line.strip():
            in_code_block = True
            code_block.append(line)
        elif in_code_block:
            code_block.append(line)
        else:
            # Empty line outside of a code block
            processed_lines.append(line)
    
    # End any remaining code block
    if in_code_block:
        processed_lines.append("```python")
        processed_lines.extend(code_block)
        processed_lines.append("```")
    
    # End any remaining docstring
    if in_docstring:
        processed_lines.append("")
        processed_lines.extend(docstring_lines)
        processed_lines.append("")
    
    # Join the processed lines
    return '\n'.join(processed_lines)


def process_c_file(file_path: Path, literate_c_script: Path) -> str:
    """
    Process C/C++ file content for HTML conversion using literate-c.
    
    Args:
        file_path: Path to the C/C++ file
        literate_c_script: Path to the literate-c script
        
    Returns:
        Processed content ready for pandoc conversion
    
    Raises:
        Exception: If literate-c processing fails
    """
    literate_c_cmd = [str(literate_c_script), str(file_path), '0']  # Use magic=0 for standard C files
    
    # Run literate-c, capture its output
    preproc_proc = subprocess.Popen(
        literate_c_cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        text=True, 
        encoding='utf-8'
    )
    content, stderr = preproc_proc.communicate()

    if preproc_proc.returncode != 0:
        raise RuntimeError(f"literate-c preprocessing failed: {stderr}")
    
    # Replace the specific marker literate-c uses with standard pandoc 'c'
    content = content.replace('~~~literatec', '~~~c')

    # Handle case where preprocessing yields no output
    if not content.strip():
        raise ValueError("Preprocessing yielded empty content")

    return content


def prepare_pandoc_input(file_path: Path, literate_c_script: Path) -> str:
    """
    Prepare content for pandoc conversion based on file type.
    
    Args:
        file_path: Path to the source file
        literate_c_script: Path to the literate-c script
        
    Returns:
        Content ready for pandoc conversion
    
    Raises:
        Exception: If processing fails
    """
    file_suffix = file_path.suffix.lower()
    
    if file_suffix == '.md':
        return process_markdown_file(file_path)
    elif file_suffix == '.py':
        return process_python_file(file_path)
    elif file_suffix == '.sh':
        return process_shell_file(file_path)
    else:  # C/C++ files
        return process_c_file(file_path, literate_c_script)


def run_pandoc(pandoc_input: str, output_html_path: Path, template_path: Path, 
               base_url: str, wiki_title: str, page_url: str, page_title: str) -> str:
    """
    Run pandoc to convert input content to HTML.
    
    Args:
        pandoc_input: Content to convert
        output_html_path: Target HTML output path
        template_path: Path to the HTML template
        base_url: Base URL for links
        wiki_title: Title for the wiki
        page_url: URL for the current page
        page_title: Title for the current page
        
    Returns:
        Generated HTML content
    
    Raises:
        Exception: If pandoc fails
    """
    pandoc_cmd = [
        'pandoc',
        '-f', 'markdown+smart+raw_html',  # Use markdown input with smart typography extension and raw HTML
        '-t', 'html5',
        '--katex',          # Enable KaTeX for math
        '--toc',            # Generate Table of Contents
        '--preserve-tabs',
        '--standalone',     # Create full HTML doc
        '--template', str(template_path),
        # Variables passed to the template (-V key=value)
        '-V', f'wikititle={wiki_title}',
        '-V', f'base={base_url}',
        '-V', f'pageUrl={page_url}',
        '-V', f'pagetitle={page_title}',
        '-V', 'sitenav=true',
        '-V', 'pagetools=true',
    ]

    pandoc_proc = subprocess.Popen(
        pandoc_cmd, 
        stdin=subprocess.PIPE, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        text=True, 
        encoding='utf-8'
    )
    stdout, stderr = pandoc_proc.communicate(input=pandoc_input)

    if pandoc_proc.returncode != 0:
        raise RuntimeError(f"Pandoc processing failed: {stderr}")
    
    if not stdout:
        raise ValueError("Pandoc generated empty output")
    
    return stdout


def post_process_python_shell_html(html_content: str) -> str:
    """
    Post-process HTML generated from Python or Shell files.
    Adds code block containers for the copy button functionality.
    
    Args:
        html_content: Original HTML content
        
    Returns:
        Processed HTML content
    """
    # Fix any <pre><code> blocks by wrapping them in a container div
    def wrap_pre_code_with_container(match):
        pre_content = match.group(0)
        return f'<div class="code-block-container">{pre_content}</div>'
    
    # Wrap <pre><code> blocks with a container div
    processed_html = re.sub(
        r'<pre[^>]*><code[^>]*>.*?</code></pre>', 
        wrap_pre_code_with_container, 
        html_content, 
        flags=re.DOTALL | re.IGNORECASE
    )
    
    # Also handle code blocks created by pandoc (with sourceCode class)
    def wrap_source_code_with_container(match):
        div_contents = match.group(1)
        return f'<div class="code-block-container">{div_contents}</div>'
    
    processed_html = re.sub(
        r'<div class="sourceCode" id="cb\d+"[^>]*>(.*?)</div>', 
        wrap_source_code_with_container, 
        processed_html, 
        flags=re.DOTALL | re.IGNORECASE
    )
    
    return processed_html


def run_awk_post_processing(html_content: str, file_path: Path, 
                            repo_root: Path, darcsit_dir: Path) -> str:
    """
    Run awk post-processing for C files using decl_anchors.awk.
    
    Args:
        html_content: HTML content to process
        file_path: Original source file path
        repo_root: Root directory of the repository
        darcsit_dir: Directory containing darcsit scripts
        
    Returns:
        Processed HTML content
    
    Raises:
        Exception: If awk processing fails
    """
    decl_anchors_script = darcsit_dir / 'decl_anchors.awk'
    if not decl_anchors_script.is_file():
        raise FileNotFoundError(f"decl_anchors.awk script not found at {decl_anchors_script}")
    
    # Construct the expected tags file path relative to the repo root for awk
    relative_tags_path = file_path.relative_to(repo_root).with_suffix(file_path.suffix + '.tags')
    
    # Create a temporary file to store the output
    temp_output_path = Path(f"{file_path}.temp.html")
    
    try:
        with open(temp_output_path, 'w', encoding='utf-8') as f_out:
            postproc_cmd = ['awk', '-v', f'tags={relative_tags_path}', '-f', str(decl_anchors_script)]
            postproc_proc = subprocess.Popen(
                postproc_cmd, 
                stdin=subprocess.PIPE, 
                stdout=f_out, 
                stderr=subprocess.PIPE, 
                text=True, 
                encoding='utf-8'
            )
            _, stderr = postproc_proc.communicate(input=html_content)

            if postproc_proc.returncode != 0:
                raise RuntimeError(f"Awk post-processing failed: {stderr}")
        
        # Read the processed content from the temporary file
        with open(temp_output_path, 'r', encoding='utf-8') as f:
            processed_content = f.read()
        
        return processed_content
    finally:
        # Remove the temporary file
        if temp_output_path.exists():
            temp_output_path.unlink()


def post_process_c_html(html_content: str, file_path: Path, 
                       repo_root: Path, darcsit_dir: Path, docs_dir: Path) -> str:
    """
    Post-process HTML generated from C/C++ files.
    Adds code block containers and fixes include links.
    
    Args:
        html_content: Original HTML content
        file_path: Original source file path
        repo_root: Root directory of the repository
        darcsit_dir: Directory containing darcsit scripts
        docs_dir: Output documentation directory
        
    Returns:
        Processed HTML content
    """
    # Remove trailing line numbers added by literate-c
    cleaned_html = re.sub(
        r'(\s*(?:<span class="[^"]*">\s*\d+\s*</span>|\s+\d+)\s*)+(\s*</span>)', 
        r'\2', 
        html_content
    )
    
    # Wrap <pre><code> blocks with a container div
    def wrap_pre_code_with_container(match):
        pre_content = match.group(0)
        return f'<div class="code-block-container">{pre_content}</div>'
    
    cleaned_html = re.sub(
        r'<pre[^>]*><code[^>]*>.*?</code></pre>', 
        wrap_pre_code_with_container, 
        cleaned_html, 
        flags=re.DOTALL | re.IGNORECASE
    )
    
    # Process the sourceCode divs
    def wrap_source_code_with_container(match):
        # Get the div's contents (which includes the pre/code)
        div_contents = match.group(1)
        # Return the pre/code wrapped in our container div
        return f'<div class="code-block-container">{div_contents}</div>'
    
    # Replace the standard sourceCode div with our container div
    cleaned_html = re.sub(
        r'<div class="sourceCode" id="cb\d+"[^>]*>(.*?)</div>', 
        wrap_source_code_with_container, 
        cleaned_html, 
        flags=re.DOTALL | re.IGNORECASE
    )
    
    # Add links to #include statements
    def create_include_link(match):
        prefix = match.group(1)  # e.g., <span class="pp">#include </span>
        span_tag_open = match.group(2)  # e.g., <span class="im">
        filename = match.group(3)  # e.g., filename.h or path/filename.h
        span_tag_close = match.group(4)  # </span>
        
        # Reconstruct original full span tag assuming literal quotes
        original_span_tag = f'{span_tag_open}\"{filename}\"{span_tag_close}'
        
        # Split filename by '/' and take the last part for checking in src-local root
        check_filename = filename.split('/')[-1]
        local_file_path = repo_root / 'src-local' / check_filename
        
        if local_file_path.is_file():
            # Link to local generated HTML file
            target_html_path = (docs_dir / 'src-local' / check_filename).with_suffix(local_file_path.suffix + '.html')
            # Calculate relative path from the *current* HTML file's directory
            try:
                relative_link = os.path.relpath(target_html_path, start=file_path.parent)
                link_url = relative_link.replace('\\', '/')  # Ensure forward slashes
            except ValueError:
                # Handle cases where paths are on different drives (should not happen here)
                link_url = target_html_path.as_uri()  # Fallback to absolute URI
            link_title = f"Link to local documentation for {filename}"
        else:
            # Link to basilisk.fr, preserving original path if present
            link_url = f"http://basilisk.fr/src/{filename}"
            link_title = f"Link to Basilisk source for {filename}"
        
        # Return the prefix span, followed by the link wrapping the filename span
        return f'{prefix}<a href="{link_url}" title="{link_title}">{original_span_tag}</a>'
    
    # Corrected regex: Find pp span followed by im span, allowing flexible space
    # and handle potential HTML entity quotes (&quot;)
    include_pattern = r'(<span class="pp">#include\s*</span>)(<span class=\"im\">)(?:\"|&quot;)(.*?)(?:\"|&quot;)(</span>)'
    cleaned_html = re.sub(include_pattern, create_include_link, cleaned_html, flags=re.DOTALL)
    
    return cleaned_html


def insert_css_link_in_html(html_file_path: Path, css_path: Path, is_root: bool = True) -> bool:
    """
    Insert a CSS link tag in the HTML file's head section.
    
    Args:
        html_file_path: Path to the HTML file
        css_path: Path to the CSS file
        is_root: Whether the HTML file is in the root directory or a subdirectory
    
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Define the CSS path - relative to the HTML file
        if is_root:
            css_link = f'<link href="{Path(css_path).name}" rel="stylesheet" type="text/css" />'
        else:
            css_link = f'<link href="../{Path(css_path).name}" rel="stylesheet" type="text/css" />'
        
        # Find the head section to insert the CSS link
        head_end_idx = content.find('</head>')
        if head_end_idx == -1:
            print(f"Warning: Could not find </head> tag in {html_file_path}")
            return False
        
        # Check if the CSS link is already included
        if 'link href="' + Path(css_path).name + '"' in content or 'link href="../' + Path(css_path).name + '"' in content:
            # CSS link is already included, no need to add it
            return True
        
        # Insert the CSS link tag just before the closing head tag
        modified_content = content[:head_end_idx] + '    ' + css_link + '\n    ' + content[head_end_idx:]
        
        # Write back the modified content
        with open(html_file_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        
        return True
    except Exception as e:
        print(f"Error inserting CSS link in {html_file_path}: {e}")
        return False


def insert_javascript_in_html(html_file_path: Path) -> bool:
    """
    Insert JavaScript for copy functionality in the HTML file.
    
    Args:
        html_file_path: Path to the HTML file
    
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # JavaScript for copy functionality
        copy_js = '''
    <script type="text/javascript">
    document.addEventListener('DOMContentLoaded', function() {
        // Add copy button to each code block container
        const codeBlocks = document.querySelectorAll('.code-block-container pre');
        codeBlocks.forEach(function(codeBlock, index) {
            // Create button element
            const button = document.createElement('button');
            button.className = 'copy-button';
            button.textContent = 'Copy';
            button.setAttribute('aria-label', 'Copy code to clipboard');
            button.setAttribute('data-copy-state', 'copy');
            
            // Get the code block container (parent of the pre)
            const container = codeBlock.parentNode;
            
            // Add the button to the container
            container.appendChild(button);
            
            // Set up click event
            button.addEventListener('click', function() {
                // Create a textarea element to copy from
                const textarea = document.createElement('textarea');
                // Get the text content from the pre element (the actual code)
                textarea.value = codeBlock.textContent;
                document.body.appendChild(textarea);
                textarea.select();
                
                try {
                    // Execute copy command
                    document.execCommand('copy');
                    // Update button state
                    button.textContent = 'Copied!';
                    button.classList.add('copied');
                    
                    // Reset button state after 2 seconds
                    setTimeout(function() {
                        button.textContent = 'Copy';
                        button.classList.remove('copied');
                    }, 2000);
                } catch (err) {
                    console.error('Copy failed:', err);
                    button.textContent = 'Error!';
                }
                
                // Clean up
                document.body.removeChild(textarea);
            });
        });
    });
    </script>
        '''
        
        # Find the body end to insert the JavaScript
        body_end_idx = content.find('</body>')
        if body_end_idx == -1:
            print(f"Warning: Could not find </body> tag in {html_file_path}")
            return False
        
        # Check if the JavaScript is already included
        if 'class="copy-button"' in content:
            # JavaScript is already included, no need to add it
            return True
        
        # Insert the JavaScript code just before the closing body tag
        modified_content = content[:body_end_idx] + copy_js + content[body_end_idx:]
        
        # Write back the modified content
        with open(html_file_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        
        return True
    except Exception as e:
        print(f"Error inserting JavaScript in {html_file_path}: {e}")
        return False


def process_file_with_page2html_logic(file_path: Path, output_html_path: Path, repo_root: Path, 
                                     basilisk_dir: Path, darcsit_dir: Path, template_path: Path, 
                                     base_url: str, wiki_title: str, literate_c_script: Path, docs_dir: Path) -> bool:
    """
    Process a source file using logic similar to page2html, calling literate-c directly.
    
    Args:
        file_path: Path to the source file
        output_html_path: Path where the HTML output should be saved
        repo_root: Root directory of the repository
        basilisk_dir: Directory containing Basilisk
        darcsit_dir: Directory containing darcsit scripts
        template_path: Path to the HTML template
        base_url: Base URL for links
        wiki_title: Title for the wiki
        literate_c_script: Path to the literate-c script
        docs_dir: Output documentation directory
        
    Returns:
        True if processing succeeded, False otherwise
    """
    print(f"  Processing {file_path.relative_to(repo_root)} -> {output_html_path.relative_to(repo_root / 'docs')}")

    try:
        # Prepare pandoc input based on file type
        pandoc_input_content = prepare_pandoc_input(file_path, literate_c_script)
        
        # Calculate relative URL path for the page
        # Ensure URL starts with / and uses forward slashes
        page_url = (base_url + output_html_path.relative_to(repo_root / 'docs').as_posix()).replace('//', '/')
        page_title = file_path.relative_to(repo_root).as_posix()  # Use relative path as title
        
        # Run pandoc to convert to HTML
        pandoc_stdout = run_pandoc(
            pandoc_input_content, 
            output_html_path, 
            template_path, 
            base_url, 
            wiki_title, 
            page_url, 
            page_title
        )
        
        # Determine file type for post-processing
        is_python_file = file_path.suffix.lower() == '.py'
        is_shell_file = file_path.suffix.lower() == '.sh'
        is_markdown_file = file_path.suffix.lower() == '.md'
        
        # Apply appropriate post-processing based on file type
        if is_python_file or is_shell_file or is_markdown_file:
            # For Python, Shell, and Markdown files
            with open(output_html_path, 'w', encoding='utf-8') as f_out:
                f_out.write(pandoc_stdout)
            
            # Then post-process the HTML
            with open(output_html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            processed_html = post_process_python_shell_html(html_content)
            
            with open(output_html_path, 'w', encoding='utf-8') as f_out:
                f_out.write(processed_html)
        else:
            # For C/C++ files, use awk for post-processing
            processed_html = run_awk_post_processing(pandoc_stdout, file_path, repo_root, darcsit_dir)
            
            # Further post-process the HTML
            cleaned_html = post_process_c_html(processed_html, file_path, repo_root, darcsit_dir, docs_dir)
            
            with open(output_html_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_html)
        
        # Insert CSS link and JavaScript for all file types
        is_root = output_html_path.parent == docs_dir
        insert_css_link_in_html(output_html_path, CSS_PATH, is_root)
        insert_javascript_in_html(output_html_path)
        
        return True
    
    except Exception as e:
        print(f"  Error processing {file_path}: {e}")
        return False


def convert_directory_tree_to_html(readme_content: str) -> str:
    """
    Converts a plain text directory tree in the README.md to an HTML site map.
    
    Args:
        readme_content: The content of README.md
        
    Returns:
        Modified README content with HTML site map
    """
    # Find the directory tree section
    tree_pattern = r'```\s*\n(├.*?\n.*?└.*?)\n```'
    tree_match = re.search(tree_pattern, readme_content, re.DOTALL)
    
    if not tree_match:
        return readme_content  # No tree found, return original content
        
    tree_text = tree_match.group(1)
    
    # Parse the directory tree
    html_structure = ['<div class="repository-structure">']
    
    # Track parent directories and their indentation levels for proper nesting
    path_stack = []
    prev_indent = -1
    
    for line in tree_text.split('\n'):
        # Skip empty lines
        if not line.strip():
            continue
            
        # Determine indentation level based on the structure symbols
        indent_level = 0
        
        if '│   ' in line:
            indent_level = line.count('│   ')
        elif '    ' in line and ('├── ' in line or '└── ' in line):
            # Handle case where │ might be missing but spacing is present
            spaces_before_item = len(line) - len(line.lstrip(' '))
            indent_level = spaces_before_item // 4
        
        # Clean up the line by removing directory tree symbols
        clean_line = line.replace('├── ', '').replace('└── ', '').replace('│   ', '')
        
        # Get the path and description
        parts = clean_line.strip().split(None, 1)
        path = parts[0]
        description = parts[1] if len(parts) > 1 else ''
        
        # Determine if it's a directory or file based on path ending with /
        is_dir = path.endswith('/')
        
        # Update the path stack based on indentation changes
        if indent_level > prev_indent:
            # Going deeper, add the previous item to the stack
            if path_stack and prev_indent >= 0:
                path_stack.append(path_stack[-1])
        elif indent_level < prev_indent:
            # Going up, remove items from stack
            for _ in range(prev_indent - indent_level):
                if path_stack:
                    path_stack.pop()
        
        # Generate proper indentation for HTML output
        indent = '  ' * indent_level
        
        # Generate the HTML list item
        item_html = f"{indent}* "
        
        if is_dir:
            # For directories
            dir_name = path.rstrip('/')
            # Special case for basilisk/src/ which should not be linked
            if dir_name == "basilisk/src":
                item_html += f"**{path}** - {description}"
            else:
                # For other directories, create links
                item_html += f"**[{path}]({dir_name})** - {description}"
            
            # Update the path stack for children
            if len(path_stack) <= indent_level:
                path_stack.append(dir_name)
            else:
                path_stack[indent_level] = dir_name
        else:
            # For files
            # Determine the parent directory path
            parent_path = path_stack[indent_level-1] if indent_level > 0 and path_stack else ""
            
            # Create HTML link with extension preserved in the filename
            file_path = f"{parent_path}/{path}" if parent_path else path
            file_path = file_path.lstrip('/')
            
            # Preserve the original file extension in the link
            item_html += f"**[{path}]({file_path}.html)** - {description}"
        
        html_structure.append(item_html)
        prev_indent = indent_level
    
    html_structure.append('</div>')
    
    # Replace the tree section with the HTML structure
    html_tree = '\n'.join(html_structure)
    modified_content = readme_content.replace(tree_match.group(0), html_tree)
    
    return modified_content


def generate_index(readme_path: Path, index_path: Path, generated_files: Dict[Path, Path], 
                  docs_dir: Path, repo_root: Path) -> bool:
    """
    Generates index.html from README.md and adds links to generated files.
    
    Args:
        readme_path: Path to README.md
        index_path: Path where index.html should be saved
        generated_files: Dictionary mapping original file paths to generated HTML paths
        docs_dir: Directory where documentation is generated
        repo_root: Root directory of the repository
        
    Returns:
        True if index.html was successfully generated, False otherwise
    """
    if not readme_path.exists():
        print(f"Warning: README.md not found at {readme_path}")
        readme_content = "# Project Documentation\n"
    else:
        readme_content = readme_path.read_text(encoding='utf-8')
        
    # Convert the directory tree to HTML before generating index
    readme_content = convert_directory_tree_to_html(readme_content)

    # Add documentation links section
    links_markdown = "\n\n## Generated Documentation\n\n"
    
    # Group links by top-level directory (src-local, testCases, etc.)
    grouped_links = {}
    for original_path, html_path in generated_files.items():
        relative_html_path = html_path.relative_to(docs_dir)
        relative_original_path = original_path.relative_to(repo_root)
        
        # Handle files in the root directory
        if len(relative_original_path.parts) == 1:  # File is directly in the root
            top_dir = "root"
        else:
            top_dir = relative_original_path.parts[0]
            
        if top_dir not in grouped_links:
            grouped_links[top_dir] = []
        
        # Make sure the html_path has the correct format with preserved extension
        grouped_links[top_dir].append(f"- [{relative_original_path}]({relative_html_path})")

    # Add a section for files in the root directory
    if 'root' in grouped_links and grouped_links['root']:
        links_markdown += f"### Root Directory\n\n"
        links_markdown += "\n".join(sorted(grouped_links['root']))
        links_markdown += "\n\n"
    
    # Add sections for files in the source directories
    for top_dir in sorted(grouped_links.keys()):
        if top_dir in SOURCE_DIRS:  # Source dirs
            links_markdown += f"### {top_dir}\n\n"
            links_markdown += "\n".join(sorted(grouped_links[top_dir]))
            links_markdown += "\n\n"

    # Append links to the end for simplicity
    final_readme_content = readme_content + links_markdown

    # Convert the combined README + links to HTML for index.html
    cmd = [
        'pandoc',
        '-f', 'markdown+tex_math_dollars+raw_html',  # Add raw_html to preserve HTML
        '-t', 'html5',
        '--standalone',
        '--mathjax',
        '--template', str(TEMPLATE_PATH),
        '-V', f'wikititle={WIKI_TITLE}',
        '-V', f'base={BASE_URL}',
        '-o', str(index_path)
    ]

    print(f"  [Debug Index] Target path: {index_path}")
    print(f"  [Debug Index] Command: {' '.join(cmd)}")

    process = subprocess.run(cmd, input=final_readme_content, text=True, capture_output=True, check=False)

    # Print results unconditionally for debugging
    print(f"  [Debug Index] Pandoc Return Code: {process.returncode}")
    if process.stdout:
        print(f"  [Debug Index] Pandoc STDOUT:\n{process.stdout}")
    if process.stderr:
        print(f"  [Debug Index] Pandoc STDERR:\n{process.stderr}")

    if process.returncode != 0:
        print("Error generating index.html:")
        return False
    
    # Post-process index.html for code blocks
    try:
        with open(index_path, 'r', encoding='utf-8') as f_in:
            index_html_content = f_in.read()
        
        processed_html = post_process_python_shell_html(index_html_content)
        
        with open(index_path, 'w', encoding='utf-8') as f_out:
            f_out.write(processed_html)
            
    except Exception as e:
        print(f"Warning: Failed to process code blocks in {index_path}: {e}")
        # Continue even if processing fails, the base file was generated

    # Insert CSS and JavaScript
    insert_css_link_in_html(index_path, CSS_PATH, True)
    insert_javascript_in_html(index_path)
    
    return True


def main():
    """
    Main function to orchestrate documentation generation.
    
    This function:
    1. Validates configuration
    2. Prepares the output directory
    3. Finds source files
    4. Processes each source file to generate HTML
    5. Generates the index.html file
    """
    print("Starting documentation generation...")
    
    # Validate configuration
    if not validate_config():
        print("Configuration validation failed. Exiting.")
        return
    
    # Prepare output directory
    if DOCS_DIR.exists():
        print(f"Cleaning existing docs directory: {DOCS_DIR}")
        shutil.rmtree(DOCS_DIR)
    DOCS_DIR.mkdir(parents=True)

    # Find source files
    source_files = find_source_files(REPO_ROOT, SOURCE_DIRS)
    print(f"Found {len(source_files)} source files to document.")

    # Track processed files and errors
    generated_files = {}
    errors = 0

    # Copy CSS file to docs directory
    if CSS_PATH and CSS_PATH.is_file():
        print(f"Copying CSS: {CSS_PATH} to {DOCS_DIR}")
        shutil.copy(CSS_PATH, DOCS_DIR)
    else:
        print("Warning: Custom CSS file not found or not specified. Code blocks might not have custom styling.")

    # Process each source file
    for file_path in source_files:
        relative_path = file_path.relative_to(REPO_ROOT)
        # Create a parallel structure in docs/ with original extension preserved
        output_html_path = DOCS_DIR / relative_path.with_suffix(file_path.suffix + '.html')
        output_html_path.parent.mkdir(parents=True, exist_ok=True)

        # Process the file
        if process_file_with_page2html_logic(
            file_path, output_html_path,
            REPO_ROOT, BASILISK_DIR, DARCSIT_DIR, TEMPLATE_PATH, BASE_URL, WIKI_TITLE, LITERATE_C_SCRIPT, DOCS_DIR
        ):
            generated_files[file_path] = output_html_path
        else:
            errors += 1
            print(f"-> Failed processing {file_path.relative_to(REPO_ROOT)}")

    # Report errors
    if errors > 0:
        print(f"\nEncountered {errors} errors during HTML generation.")

    # Generate index.html
    print("\nGenerating index.html...")
    if not generate_index(README_PATH, INDEX_PATH, generated_files, DOCS_DIR, REPO_ROOT):
        print("Failed to generate index.html.")
        return

    print("\nDocumentation generation complete.")
    print(f"Output generated in: {DOCS_DIR}")


if __name__ == "__main__":
    main()
