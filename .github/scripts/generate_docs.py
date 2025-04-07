import os
import subprocess
import re
import shutil
from pathlib import Path
import shlex # Import shlex for safe command splitting

# Configuration
# Assume the script is in .github/scripts, REPO_ROOT is the parent of .github
REPO_ROOT = Path(__file__).parent.parent.parent
SOURCE_DIRS = ['src-local', 'testCases', 'postProcess'] # Directories within REPO_ROOT to scan
DOCS_DIR = REPO_ROOT / 'docs'
README_PATH = REPO_ROOT / 'README.md'
INDEX_PATH = DOCS_DIR / 'index.html'
# --- New configuration based on page2html ---
BASILISK_DIR = REPO_ROOT / 'basilisk' # Assuming basilisk dir is at the root
DARCSIT_DIR = BASILISK_DIR / 'src' / 'darcsit'
TEMPLATE_PATH = REPO_ROOT / '.github' / 'assets' / 'custom_template.html' # Use the modified local template
LITERATE_C_SCRIPT = DARCSIT_DIR / 'literate-c' # Path to the literate-c script
BASE_URL = "/" # Relative base URL for links within the site
WIKI_TITLE = "CoMPhy-Lab Documentation"
# Check if essential directories/files exist
if not BASILISK_DIR.is_dir():
    print(f"Error: BASILISK_DIR not found at {BASILISK_DIR}")
    exit(1)
if not DARCSIT_DIR.is_dir():
    print(f"Error: DARCSIT_DIR not found at {DARCSIT_DIR}")
    exit(1)
if not TEMPLATE_PATH.is_file():
    print(f"Error: TEMPLATE_PATH not found at {TEMPLATE_PATH}")
    exit(1)
if not LITERATE_C_SCRIPT.is_file():
    print(f"Error: literate-c script not found at {LITERATE_C_SCRIPT}")
    exit(1)
# --- End new configuration ---

CSS_PATH = REPO_ROOT / '.github' / 'assets' / 'custom_styles.css' # Path to custom CSS


def find_source_files(root_dir, source_dirs):
    """Finds all .c and .h files in the specified source directories."""
    files = []
    for dir_name in source_dirs:
        src_path = root_dir / dir_name
        if src_path.is_dir():
            files.extend(src_path.rglob('*.c'))
            files.extend(src_path.rglob('*.h'))
    return files

def process_file_with_page2html_logic(file_path: Path, output_html_path: Path, repo_root: Path, basilisk_dir: Path, darcsit_dir: Path, template_path: Path, base_url: str, wiki_title: str, literate_c_script: Path, docs_dir: Path):
    """Processes a source file using logic similar to page2html, calling literate-c directly."""
    print(f"  Processing {file_path.relative_to(repo_root)} -> {output_html_path.relative_to(repo_root / 'docs')}")

    # --- Call literate-c script for preprocessing --- 
    literate_c_cmd = [str(literate_c_script), str(file_path), '0'] # Use magic=0 for standard C files
    try:
        # Run literate-c, capture its output
        preproc_proc = subprocess.Popen(literate_c_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        pandoc_input_content, preproc_stderr = preproc_proc.communicate()

        if preproc_proc.returncode != 0:
            print(f"  Error during literate-c preprocessing for {file_path}:")
            print(f"  literate-c stderr: {preproc_stderr}")
            return False
        # Replace the specific marker literate-c uses with standard pandoc 'c'
        pandoc_input_content = pandoc_input_content.replace('~~~literatec', '~~~c')

        # Handle case where preprocessing yields no output
        if not pandoc_input_content.strip():
             print(f"  Warning: Preprocessing yielded empty content for {file_path}. Skipping.")
             # Optionally create an empty file or just skip
             # output_html_path.touch() 
             return True # Consider skipped as success

    except FileNotFoundError:
         print(f"  Error: literate-c script not found at {literate_c_script} or is not executable.")
         return False
    except Exception as e:
        print(f"  Error running literate-c preprocessing for {file_path}: {e}")
        return False

    # --- Pandoc Command Definition (remains mostly the same) ---
    # Note: Highlighting type (.c, .py etc) is now handled by literate-c outputting ~~~c
    # Determine file type for highlighting (simplified: only C for .c/.h)
    pandoc_lang_type = ".c" # Default to C
    if file_path.suffix.lower() == '.py':
        pandoc_lang_type = ".python"
    elif file_path.suffix.lower() == '.m':
         pandoc_lang_type = ".octave"
    # Add more types if needed based on page2html logic

    # --- Define Pandoc Command ---
    # Calculate relative URL path for the page
    # Ensure URL starts with / and uses forward slashes
    page_url = (base_url + output_html_path.relative_to(repo_root / 'docs').as_posix()).replace('//', '/')
    page_title = file_path.relative_to(repo_root).as_posix() # Use relative path as title

    pandoc_cmd = [
        'pandoc',
        '-f', 'markdown+smart', # Use markdown input with smart typography extension
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
        # Add other variables from page2html if needed (tabs, users, etc.)
        # '-V', 'tabs=<li class=selected><a href="$url">view</a></li><li><a href="$url?history">history</a></li>', # Example
        # '-V', 'javascripts=<script src="/js/status.js" type="text/javascript"></script>', # Example
        '-V', 'sitenav=true', # Assuming these are desired based on template
        '-V', 'pagetools=true',
    ]

    # Add CSS if specified - but we'll insert it directly later
    # if CSS_PATH and CSS_PATH.is_file():
    #     pandoc_cmd.extend(['--css', CSS_PATH.name]) # Use relative name

    # --- Define Postprocessing Command (cpostproc equivalent) ---
    # awk -v tags="$1.tags" -f $BASILISK/darcsit/decl_anchors.awk
    # Note: The .tags file generation is not included here, assuming decl_anchors handles its absence or it's not critical initially.
    decl_anchors_script = darcsit_dir / 'decl_anchors.awk'
    if not decl_anchors_script.is_file():
        print(f"  Error: decl_anchors.awk script not found at {decl_anchors_script}")
        return False
    # Construct the expected tags file path relative to the repo root for awk
    relative_tags_path = file_path.relative_to(repo_root).with_suffix(file_path.suffix + '.tags')
    postproc_cmd = ['awk', '-v', f'tags={relative_tags_path}', '-f', str(decl_anchors_script)]


    # --- Execute the pipeline: PANDOC | POSTPROC > output_file ---
    # We feed the preprocessed content directly to pandoc's stdin
    try:
        # Start pandoc process, pipe input from string, pipe output to postprocessor
        pandoc_proc = subprocess.Popen(pandoc_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        pandoc_stdout, pandoc_stderr = pandoc_proc.communicate(input=pandoc_input_content)

        if pandoc_proc.returncode != 0:
            print(f"  Error during pandoc processing for {file_path}:")
            print(f"  Pandoc stderr: {pandoc_stderr}")
            return False
        if not pandoc_stdout:
             print(f"  Warning: Pandoc generated empty output for {file_path}.")
             # return False # Decide if empty output is an error

        # Start postprocessor process, pipe input from pandoc's output, pipe output to final file
        with open(output_html_path, 'w', encoding='utf-8') as f_out:
            postproc_proc = subprocess.Popen(postproc_cmd, stdin=subprocess.PIPE, stdout=f_out, stderr=subprocess.PIPE, text=True, encoding='utf-8')
            postproc_stdout, postproc_stderr = postproc_proc.communicate(input=pandoc_stdout)

            if postproc_proc.returncode != 0:
                print(f"  Error during post-processing (awk) for {file_path}:")
                print(f"  Postproc stderr: {postproc_stderr}")
                # Attempt to remove the potentially corrupted output file
                try:
                    output_html_path.unlink()
                except OSError:
                    pass # Ignore error if file couldn't be removed
                return False

        # --- Post-process HTML to remove trailing line numbers added by literate-c ---
        try:
            with open(output_html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Regex to find space(s) + digit(s) + optional space(s) right before </span>
            # cleaned_html_content = re.sub(r'\s+\d+\s*</span>', '</span>', html_content)
            # Updated regex: accounts for optional inner span around the number (e.g., <span class="dv">35</span>)
            # cleaned_html_content = re.sub(r'\s*(?:<span class="[^"]*">\s*)?\d+\s*(?:</span>)?\s*</span>', '</span>', html_content)
            # Third attempt: Capture the closing span and replace the whole match (number part + closing span) with just the captured closing span.
            # cleaned_html_content = re.sub(r'(?:\s*<span class="[^"]*">\s*\d+\s*</span>|\s+\d+)(\s*</span>)', r'\1', html_content)
            # Fourth attempt: Match one or more number segments (group 1), capture final closing span (group 2), replace with group 2.
            cleaned_html_content = re.sub(r'(\s*(?:<span class="[^"]*">\s*\d+\s*</span>|\s+\d+)\s*)+(\s*</span>)', r'\2', html_content)

            # Remove the outer div.sourceCode wrapper generated by Pandoc
            # This keeps the <pre> tag and its contents intact.
            # Using re.DOTALL to ensure matching across potential newlines within the div.
            cleaned_html_content = re.sub(r'<div class="sourceCode" id="cb\d+"[^>]*>(.*?)</div>', r'\1', cleaned_html_content, flags=re.DOTALL | re.IGNORECASE)

            # --- Add links to #include statements ---
            def create_include_link(match):
                prefix = match.group(1) # e.g., <span class="pp">#include </span>
                span_tag_open = match.group(2) # e.g., <span class="im">
                filename = match.group(3) # e.g., filename.h or path/filename.h
                span_tag_close = match.group(4) # </span>

                # Reconstruct original full span tag assuming literal quotes
                # (Based on previous debug output, Pandoc uses literal quotes here)
                original_span_tag = f'{span_tag_open}\"{filename}\"{span_tag_close}'

                # Correctly handle potential paths in included filename for local check
                # Split filename by '/' and take the last part for checking in src-local root
                # Note: This assumes local includes are directly in src-local, not subdirs.
                # If includes can be in src-local/subdir/, adjust this logic.
                check_filename = filename.split('/')[-1]
                local_file_path = repo_root / 'src-local' / check_filename
                
                if local_file_path.is_file():
                    # Link to local generated HTML file
                    # Use the *original* filename (with path) for the link target
                    target_html_path = (docs_dir / 'src-local' / check_filename).with_suffix('.html')
                    # Calculate relative path from the *current* HTML file's directory
                    try:
                        relative_link = os.path.relpath(target_html_path, start=output_html_path.parent)
                        link_url = relative_link.replace('\\', '/') # Ensure forward slashes
                    except ValueError:
                        # Handle cases where paths are on different drives (should not happen here)
                        link_url = target_html_path.as_uri() # Fallback to absolute URI
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
            cleaned_html_content = re.sub(include_pattern, create_include_link, cleaned_html_content, flags=re.DOTALL)

            with open(output_html_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_html_content)
            
        except Exception as e:
            print(f"Error during HTML cleanup for {output_html_path}: {e}")
            return False
        # --- End post-processing --- 

        # --- Insert CSS link directly into the HTML file ---
        is_root = output_html_path.parent == DOCS_DIR
        insert_css_link_in_html(output_html_path, CSS_PATH, is_root)

        # print(f"  Successfully generated {output_html_path.relative_to(repo_root / 'docs')}")
        return True

    except FileNotFoundError as e:
        print(f"  Error: Command not found during processing of {file_path}. Is '{e.filename}' installed and in PATH?")
        print(f"  Failed command (or part of pipeline): {' '.join(pandoc_cmd)} | {' '.join(postproc_cmd)}")
        return False
    except Exception as e:
        print(f"  An unexpected error occurred processing {file_path}: {e}")
        return False


def generate_index(readme_path, index_path, generated_files, docs_dir, repo_root):
    """Generates index.html from README.md and adds links to generated files."""
    if not readme_path.exists():
        print(f"Warning: README.md not found at {readme_path}")
        readme_content = "# Project Documentation\n"
    else:
        readme_content = readme_path.read_text(encoding='utf-8')

    # Simple placeholder replacement or append links
    # You might want a specific marker like <!-- DOC_LINKS_START -->
    # Ensure blank line before heading for robust parsing
    links_markdown = "\n\n## Generated Documentation\n\n"
    
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
        '-f', 'markdown+tex_math_dollars',
        '-t', 'html5',
        '--standalone',
        '--mathjax',
        '--template', str(TEMPLATE_PATH),
        '-V', f'wikititle={WIKI_TITLE}',
        '-V', f'base={BASE_URL}',
        '-o', str(index_path)
    ]
    # Apply the same template to the index page? Optional.
    # if TEMPLATE_PATH.is_file():
    #     cmd.extend(['--template', str(TEMPLATE_PATH)])
    #     cmd.extend(['-V', f'wikititle={WIKI_TITLE}', '-V', f'base={BASE_URL}']) # Add vars if using template

    # Add CSS to index page command as well - but we'll insert it directly later
    # if CSS_PATH and CSS_PATH.is_file():
    #     cmd.extend(['--css', Path(CSS_PATH).name])

    print(f"  [Debug Index] Target path: {index_path}") # DEBUG
    print(f"  [Debug Index] Command: {' '.join(cmd)}") # DEBUG
    # print(f"  [Debug Index] Input Content:\n{final_readme_content[:200]}...") # DEBUG (optional, can be long)

    process = subprocess.run(cmd, input=final_readme_content, text=True, capture_output=True, check=False)

    # --- DEBUGGING: Print results unconditionally ---
    print(f"  [Debug Index] Pandoc Return Code: {process.returncode}")
    if process.stdout:
        print(f"  [Debug Index] Pandoc STDOUT:\n{process.stdout}")
    if process.stderr:
        print(f"  [Debug Index] Pandoc STDERR:\n{process.stderr}")
    # --- END DEBUGGING ---

    if process.returncode != 0:
        print("Error generating index.html:") # Keep original error message
        # print(process.stderr) # Already printed in debug block
        return False
    
    # --- Post-process index.html to remove div.sourceCode wrapper ---
    try:
        with open(index_path, 'r', encoding='utf-8') as f_in:
            index_html_content = f_in.read()
        
        # Use the same regex as in process_file_with_page2html_logic
        cleaned_index_html = re.sub(r'<div class="sourceCode" id="cb\d+"[^>]*>(.*?)</div>', r'\1', index_html_content, flags=re.DOTALL | re.IGNORECASE)

        with open(index_path, 'w', encoding='utf-8') as f_out:
            f_out.write(cleaned_index_html)
            
    except Exception as e:
        print(f"Warning: Failed to clean div.sourceCode from {index_path}: {e}")
        # Continue even if cleanup fails, the base file was generated

    # --- Insert CSS link directly into the index.html file ---
    insert_css_link_in_html(index_path, CSS_PATH, True)
    
    return True


# --- Define a custom function to add CSS link to each HTML file ---
def insert_css_link_in_html(html_file_path, css_path, is_root=True):
    """Insert the CSS link tag in the HTML file's head section."""
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

    # --- Copy CSS file to docs directory before processing files ---
    if CSS_PATH and CSS_PATH.is_file():
        print(f"Copying CSS: {CSS_PATH} to {DOCS_DIR}")
        shutil.copy(CSS_PATH, DOCS_DIR)
        # Make sure CSS is directly included in HTML rather than relying on --css flag
        with open(CSS_PATH, 'r') as css_file:
            css_content = css_file.read()
    else:
        print("Warning: Custom CSS file not found or not specified. Code blocks might not have custom styling.")
        css_content = ""

    for file_path in source_files:
        # print(f"Processing: {file_path.relative_to(REPO_ROOT)}") # Moved inside helper
        relative_path = file_path.relative_to(REPO_ROOT)
        # Create a parallel structure in docs/
        output_html_path = DOCS_DIR / relative_path.with_suffix('.html')
        output_html_path.parent.mkdir(parents=True, exist_ok=True)

        # --- Use the new processing function ---
        if process_file_with_page2html_logic(
            file_path, output_html_path,
            REPO_ROOT, BASILISK_DIR, DARCSIT_DIR, TEMPLATE_PATH, BASE_URL, WIKI_TITLE, LITERATE_C_SCRIPT, DOCS_DIR
        ):
            generated_files[file_path] = output_html_path
        else:
            errors += 1
            print(f"-> Failed processing {file_path.relative_to(REPO_ROOT)}") # Add failure marker


    if errors > 0:
        print(f"\nEncountered {errors} errors during HTML generation.")

    print("\nGenerating index.html...")
    # CSS is already copied, no need to copy again here
    # if CSS_PATH and Path(CSS_PATH).exists():
    #     print(f"Copying CSS: {CSS_PATH} to {DOCS_DIR}")
    #     shutil.copy(CSS_PATH, DOCS_DIR)
    
    if not generate_index(README_PATH, INDEX_PATH, generated_files, DOCS_DIR, REPO_ROOT):
         print("Failed to generate index.html.")
         return

    print("\nDocumentation generation complete.")
    print(f"Output generated in: {DOCS_DIR}")

if __name__ == "__main__":
    main()
