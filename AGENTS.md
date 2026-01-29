# AGENTS

## Project Overview
This repository contains Basilisk CFD simulation cases and post-processing
tools for lid-driven cavity dye injection, plus generated documentation in
`.github/docs`.

## Layout
- `simulationCases/`: primary `.c` cases and Makefile
- `src-local/`: project-specific headers
- `postProcess/`: analysis scripts and notebooks
- `.github/docs`: generated documentation site output
- `.github/`: documentation assets, scripts, and workflows
- `*.params`, `*.sbatch`: run configurations and cluster scripts
- `basilisk/`: local Basilisk checkout (ignored; do not commit)

## Documentation workflow
- Install Python deps: `python3 -m venv .venv && source .venv/bin/activate && pip install -r .github/scripts/requirements.txt`
- Build docs: `.github/scripts/build.sh`
- Preview locally: `.github/scripts/deploy.sh`

## Editing guidance
- Do not commit the `basilisk/` directory or generated outputs outside `.github/docs`.
- Keep case output directories untouched unless explicitly requested.
- C/C++ style: 2-space indent, 80-char lines, use `/**` markdown comments (no leading `*` lines).
