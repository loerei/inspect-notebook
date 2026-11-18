"""CLI utility to inspect Jupyter notebook cells, source lines, and saved outputs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def _format_output(out: dict) -> str:
    """Format a single Jupyter cell output (stream, execute_result, display_data, or error)."""
    out_type = out.get("output_type", "")
    if out_type == "error":
        tb = "\n".join(out.get("traceback", []))
        tb_clean = re.sub(r"\x1b\[[0-9;]*m", "", tb)
        return f"[ERROR] {out.get('ename')}: {out.get('evalue')}\n{tb_clean}"
    text = out.get("text") or out.get("data", {}).get("text/plain")
    if text:
        return "".join(text) if isinstance(text, list) else str(text)
    return f"[{out_type}]"


def _export_cells(notebook_path: Path, out_path: Path, cell_type: str, marker_fmt: str) -> None:
    """Export all cells of `cell_type` from `notebook_path` into `out_path` with cell markers."""
    nb = json.loads(notebook_path.read_text(encoding="utf-8"))
    cells = nb.get("cells", [])
    chunks: list[str] = []
    cur_line = 1
    for idx, cell in enumerate(cells):
        if cell.get("cell_type") != cell_type:
            continue
        src = "".join(cell.get("source", [])).rstrip("\n")
        header = marker_fmt.format(idx=idx)
        block = f"{header}\n{src}\n"
        line_count = block.count("\n")
        print(f"  Cell {idx:2d} -> {out_path}:L{cur_line}-L{cur_line + line_count - 1}")
        chunks.append(block)
        cur_line += line_count + 1
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(chunks), encoding="utf-8")
    print(f"Exported {len(chunks)} {cell_type} cell(s) to {out_path}")


def _import_cells(notebook_path: Path, src_path: Path, cell_type: str, marker_regex: str, backup: bool = False) -> None:
    """Sync marked blocks from `src_path` back into `notebook_path` cells of `cell_type`."""
    import ast
    import shutil

    text = src_path.read_text(encoding="utf-8")
    nb = json.loads(notebook_path.read_text(encoding="utf-8"))
    cells = nb.get("cells", [])

    parts = re.split(marker_regex, text)
    if parts[0] != "":
        raise ValueError(f"Unexpected content before first cell marker in {src_path}")

    updated = 0
    for i in range(1, len(parts), 2):
        cell_idx = int(parts[i])
        body = parts[i + 1]
        if body.endswith("\n\n"):
            body = body[:-1]
        if cell_idx < 0 or cell_idx >= len(cells) or cells[cell_idx].get("cell_type") != cell_type:
            raise ValueError(f"Cell {cell_idx} is missing or not a {cell_type} cell in {notebook_path}")
        old_src = "".join(cells[cell_idx].get("source", []))
        if old_src.rstrip("\n") != body.rstrip("\n"):
            cells[cell_idx]["source"] = body.splitlines(keepends=True)
            updated += 1

    for idx, cell in enumerate(cells):
        if cell.get("cell_type") == "code":
            ast.parse("".join(cell.get("source", [])), filename=f"cell_{idx}")

    if backup and updated > 0:
        bak_path = notebook_path.with_suffix(notebook_path.suffix + ".bak")
        shutil.copy2(notebook_path, bak_path)
        print(f"Created backup: {bak_path}")

    notebook_path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Synced {updated} updated {cell_type} cell(s) into {notebook_path} (all code cells ast.parse clean)")


def inspect_notebook(
    notebook_path: Path,
    cell_index: int | None = None,
    pattern: str | None = None,
    show_outputs: bool = False,
) -> None:
    """Print cell summaries, matching lines, or outputs from a notebook."""
    nb = json.loads(notebook_path.read_text(encoding="utf-8"))
    cells = nb.get("cells", [])
    print(f"Notebook: {notebook_path} | Total cells: {len(cells)}")

    if cell_index is not None:
        if cell_index < 0 or cell_index >= len(cells):
            raise IndexError(f"Cell index {cell_index} out of range [0, {len(cells) - 1}]")
        cell = cells[cell_index]
        print(f"\n=== CELL {cell_index} ({cell.get('cell_type')}) ===")
        for idx, line in enumerate("".join(cell.get("source", [])).splitlines(), start=1):
            print(f"{idx:4d}: {line}")
        if show_outputs and cell.get("outputs"):
            print(f"\n--- Outputs ({len(cell['outputs'])}) ---")
            for out in cell["outputs"]:
                print(_format_output(out))
        return

    regex = re.compile(pattern) if pattern else None
    if show_outputs and not regex:
        for idx, cell in enumerate(cells):
            outs = cell.get("outputs", [])
            if outs:
                print(f"\n=== CELL {idx} OUTPUTS ({len(outs)}) ===")
                for out in outs:
                    print(_format_output(out))
        return
    for idx, cell in enumerate(cells):
        src = "".join(cell.get("source", []))
        lines = src.splitlines()
        if regex:
            matches = [(ln, text) for ln, text in enumerate(lines, start=1) if regex.search(text)]
            if matches:
                print(f"\n=== CELL {idx} ({cell.get('cell_type')}, {len(lines)} lines) ===")
                for ln, text in matches:
                    print(f"  L{ln:4d}: {text}")
        else:
            first_line = lines[0] if lines else ""
            out_count = len(cell.get("outputs", []))
            print(f"[{idx:2d}] {cell.get('cell_type'):8s} | {len(lines):4d} lines | outputs={out_count} | {first_line[:80]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect, export, or sync a Jupyter notebook (.ipynb).")
    parser.add_argument("notebook", type=Path, help="Path to the .ipynb file.")
    parser.add_argument("--cell", type=int, default=None, help="Dump full source of a specific cell index.")
    parser.add_argument("--pattern", type=str, default=None, help="Regex pattern to search across cell sources.")
    parser.add_argument("--outputs", action="store_true", help="Include cell outputs when dumping a cell or notebook.")
    parser.add_argument("--export-py", type=Path, default=None, help="Export all code cells into a .py file with `# %% Cell <idx>` markers.")
    parser.add_argument("--import-py", type=Path, default=None, help="Sync `# %% Cell <idx>` code blocks from a .py file back into the notebook.")
    parser.add_argument("--export-md", type=Path, default=None, help="Export all markdown cells into a .md file with `<!-- %% Cell <idx> -->` markers.")
    parser.add_argument("--import-md", type=Path, default=None, help="Sync `<!-- %% Cell <idx> -->` markdown blocks from a .md file back into the notebook.")
    parser.add_argument("--backup", action="store_true", help="Create a .bak copy before modifying the notebook with --import-py or --import-md.")
    args = parser.parse_args()
    if args.export_py is not None:
        _export_cells(args.notebook, args.export_py, "code", "# %% Cell {idx}")
        return
    if args.import_py is not None:
        _import_cells(args.notebook, args.import_py, "code", r"(?m)^# %% Cell (\d+)\n", backup=args.backup)
        return
    if args.export_md is not None:
        _export_cells(args.notebook, args.export_md, "markdown", "<!-- %% Cell {idx} -->")
        return
    if args.import_md is not None:
        _import_cells(args.notebook, args.import_md, "markdown", r"(?m)^<!-- %% Cell (\d+) -->\n", backup=args.backup)
        return
    inspect_notebook(
        args.notebook,
        cell_index=args.cell,
        pattern=args.pattern,
        show_outputs=args.outputs,
    )


if __name__ == "__main__":
    main()
