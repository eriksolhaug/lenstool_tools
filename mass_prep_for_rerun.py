#!/usr/bin/env python3
"""Create mass/ subdir, copy sample*.par files, set xmin/xmax/ymin/ymax to ±100."""
import shutil
from pathlib import Path
import re

mass_dir = Path("mass")
mass_dir.mkdir(exist_ok=True)

for par_file in Path(".").glob("sample*.par"):
    content = par_file.read_text()
    content = re.sub(r'potent(?:iel|ial)\s+O6[\s\S]*?limit\s+O6[\s\S]*?end\n', '', content)
    content = re.sub(r'^\s*(ampli|dpl|poten)\s+.*$\n', '', content, flags=re.MULTILINE)
    # Decrease nlens_opt by 1
    def decrease_nlens_opt(match):
        value = int(match.group(1))
        return f'nlens_opt   {value - 1}'
    content = re.sub(r'nlens_opt\s+(\d+)', decrease_nlens_opt, content)
    content = re.sub(r'xmin\s+[\d.-]+', 'xmin                -100.00', content)
    content = re.sub(r'xmax\s+[\d.-]+', 'xmax                 100.00', content)
    content = re.sub(r'ymin\s+[\d.-]+', 'ymin                -100.00', content)
    content = re.sub(r'ymax\s+[\d.-]+', 'ymax                 100.00', content)
    (mass_dir / par_file.name).write_text(content)
    print(f"Copied and modified: {par_file.name}")
