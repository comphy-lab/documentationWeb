#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Define the project root relative to the script location
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
PROJECT_ROOT="$SCRIPT_DIR"
DOCS_DIR="$PROJECT_ROOT/docs"
PYTHON_SCRIPT="$PROJECT_ROOT/scripts/generate_docs.py"

echo "Running documentation generation script..."
python3 "$PYTHON_SCRIPT"

if [ $? -ne 0 ]; then
    echo "Documentation generation failed."
    exit 1
fi

echo "Documentation generated successfully in $DOCS_DIR"

# Check if docs directory exists
if [ ! -d "$DOCS_DIR" ]; then
    echo "Error: Docs directory '$DOCS_DIR' not found after generation."
    exit 1
fi

# Change to the docs directory
cd "$DOCS_DIR"

echo "Starting local web server in $PWD on port 8000..."
echo "Access the site at http://localhost:8000 or http://127.0.0.1:8000"
echo "Press Ctrl+C to stop the server."

# Start the server in the foreground
python3 -m http.server 8000
