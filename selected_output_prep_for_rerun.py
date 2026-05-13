#!/usr/bin/env python3
"""Create selected_output/ subdir, copy sample*.par files, remove all runmode modes, keep field unchanged."""
import shutil
from pathlib import Path
import re

selected_output_dir = Path("selected_output")
selected_output_dir.mkdir(exist_ok=True)

for par_file in Path(".").glob("sample*.par"):
    content = par_file.read_text()
    # Remove all runmode modes (ampli, dpl, poten, mass)
    content = re.sub(r'^\s*(ampli|dpl|poten|mass)\s+.*$\n', '', content, flags=re.MULTILINE)
    (selected_output_dir / par_file.name).write_text(content)
    print(f"Copied and modified: {par_file.name}")
