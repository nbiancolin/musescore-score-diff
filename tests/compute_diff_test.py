import xml.etree.ElementTree as ET
from pathlib import Path
import tempfile
from compute_diff import merge_musescore_files

def _count_top_level_parts_and_staves(score_elem):
    parts = score_elem.findall("./Part")
    staves = score_elem.findall("./Staff")
    return len(parts), len(staves)

def test_merge_doubles_parts_and_staves_with_suffix():
    fixtures = Path(__file__).parent / "fixtures"
    f1 = fixtures / "Test-Score/Test-Score.mscx"
    f2 = fixtures / "Test-Score-2/Test-Score-2.mscx"

    # Parse originals to know baseline counts
    score1 = ET.parse(f1).getroot().find("Score")
    score2 = ET.parse(f2).getroot().find("Score")
    p1, s1 = _count_top_level_parts_and_staves(score1)
    p2, s2 = _count_top_level_parts_and_staves(score2)

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "merged.mscx"
        merge_musescore_files(f1, f2, out)

        merged = ET.parse(out).getroot().find("Score")
        pm, sm = _count_top_level_parts_and_staves(merged)

        # Parts and staves should be the sum (we append all of file2)
        assert pm == p1 + p2, f"Expected {p1+p2} parts, got {pm}"
        assert sm == s1 + s2, f"Expected {s1+s2} staves, got {sm}"

        # All file2 staff ids should appear with "-1" suffix in merged
        f2_staff_ids = {s.get("id") for s in score2.findall("./Staff")}
        merged_staff_ids = {s.get("id") for s in merged.findall("./Staff")}
        for sid in f2_staff_ids:
            assert f"{sid}-1" in merged_staff_ids, f"Missing suffixed staff {sid}-1"

        # Part ids from file2 should also be present with "-1"
        f2_part_ids = {p.get("id") for p in score2.findall("./Part")}
        merged_part_ids = {p.get("id") for p in merged.findall("./Part")}
        for pid in f2_part_ids:
            assert f"{pid}-1" in merged_part_ids, f"Missing suffixed part {pid}-1"

def test_export_file_for_visual_inspection():
    fixtures_dir = Path(__file__).parent / "fixtures"
    file1_path = fixtures_dir / "Test-Score/Test-Score.mscx"
    file2_path = fixtures_dir / "Test-Score-2/Test-Score-2.mscx"
    output_path = Path(__file__).parent / "sample-output/Test-Score/Test-Score.mscx"

    merge_musescore_files(file1_path, file2_path, output_path)