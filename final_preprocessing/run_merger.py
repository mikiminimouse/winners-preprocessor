from pathlib import Path
from docprep.engine.merger import Merger
from docprep.core.config import get_data_paths, get_cycle_paths

protocol_date = "2025-03-18"
data_paths = get_data_paths(protocol_date)
output_dir = data_paths["ready2docling"]
merge_base = data_paths["merge"]

# Список директорий для сборки
merge_dirs = []

# Merge_0 (Direct)
merge_0 = merge_base / "Merge_0"
if merge_0.exists():
    merge_dirs.append(merge_0)

# Merge_1, 2, 3
for cycle_num in range(1, 4):
    cycle_paths = get_cycle_paths(cycle_num, merge_base=merge_base)
    merge_dirs.append(cycle_paths["merge"])

print(f"Merging from: {merge_dirs}")
print(f"Target: {output_dir}")

merger = Merger()
result = merger.collect_units(merge_dirs, output_dir)

print(f"Processed: {result['units_processed']}")
print(f"Errors: {len(result.get('errors', []))}")
