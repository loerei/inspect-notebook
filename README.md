# inspect-notebook

Edit `.ipynb` files without fighting raw JSON escapes. Dump code or markdown cells to plain `.py` / `.md` files with cell markers, patch them with your usual tools, and sync them back with automatic AST validation.

## Why

Raw `.ipynb` files are JSON arrays of escaped strings. Patching them directly breaks quotes or commas, and full-notebook rewrites risk corrupting cell metadata or outputs.

This script splits the workflow into three steps:

1. Export all code cells (`# %% Cell <idx>`) or markdown cells (`<!-- %% Cell <idx> -->`) to a regular file.
2. Edit that file normally (with any editor, linter, or AI patching tool).
3. Sync the modified blocks back into the original `.ipynb`, preserving cell metadata and outputs while running `ast.parse` on every code cell before writing.

## Requirements

- Python 3.10+ (standard library only, zero external dependencies).

## Usage

### 1. Inspect cells, search, or read outputs

```bash
# List all cells with execution counts, line counts, and output counts
python inspect_notebook.py notebook.ipynb

# Search across all cell sources by regex (add --outputs to also search cell outputs)
python inspect_notebook.py notebook.ipynb --pattern "roc_auc_score|FAST_EVAL" --outputs

# Print a specific cell (and its saved outputs, including error tracebacks and MIME sizes)
python inspect_notebook.py notebook.ipynb --cell 1 --outputs

# Print all non-empty cell outputs across the notebook
python inspect_notebook.py notebook.ipynb --outputs

# Export all non-empty cell outputs to a plain text log file
python inspect_notebook.py notebook.ipynb --export-outputs outputs.log
```

### 2. Export, edit, and sync code cells

```bash
# Export code cells to a .py file with `# %% Cell <idx>` markers
python inspect_notebook.py notebook.ipynb --export-py review.py

# Edit review.py, then sync changes back (with optional .bak backup)
python inspect_notebook.py notebook.ipynb --import-py review.py --backup
```

### 3. Export, edit, and sync markdown cells

```bash
# Export markdown cells to a .md file with `<!-- %% Cell <idx> -->` markers
python inspect_notebook.py notebook.ipynb --export-md review.md

# Edit review.md, then sync changes back
python inspect_notebook.py notebook.ipynb --import-md review.md --backup
```

a star on GitHub would be nice if you find it useful
