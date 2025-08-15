import xml.etree.ElementTree as ET
from pathlib import Path
import tempfile
from compute_diff import merge_musescore_files

def test_merge_adds_new_staves_with_suffix():
    fixtures_dir = Path(__file__).parent / "fixtures"
    file1_path = fixtures_dir / "Test-Score/Test-Score.mscx"
    file2_path = fixtures_dir / "Test-Score-2/Test-Score-2.mscx"

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "merged.mscx"

        # Merge files
        merge_musescore_files(file1_path, file2_path, output_path)

        # Parse merged XML
        tree = ET.parse(output_path)
        score = tree.getroot().find("Score")

        # Collect staff IDs
        staff_ids = [staff.attrib["id"] for staff in score.findall(".//Staff")]

        # ✅ 1. All original staves from file1 are still present
        file1_staff_ids = {staff.attrib["id"] for staff in ET.parse(file1_path).getroot().find("Score").findall(".//Staff")}
        for sid in file1_staff_ids:
            assert sid in staff_ids, f"Missing original staff {sid}"

        # ✅ 2. New staves from file2 have "-1" suffix
        file2_staff_ids = {staff.attrib["id"] for staff in ET.parse(file2_path).getroot().find("Score").findall(".//Staff")}
        new_staves = file2_staff_ids - file1_staff_ids
        for sid in new_staves:
            suffixed = f"{sid}-1"
            assert suffixed in staff_ids, f"Expected new staff ID {suffixed} in merged file"

        # ✅ 3. Staff IDs inside <Part> match top-level <Staff> IDs
        top_level_ids = {staff.attrib["id"] for staff in score.findall("./Staff")}
        part_staff_ids = {staff.attrib["id"] for staff in score.findall("./Part/Staff")}
        assert part_staff_ids.issubset(top_level_ids), "Part staff IDs don't match top-level staff IDs"

def test_export_file_for_visual_inspection():
    fixtures_dir = Path(__file__).parent / "fixtures"
    file1_path = fixtures_dir / "Test-Score/Test-Score.mscx"
    file2_path = fixtures_dir / "Test-Score-2/Test-Score-2.mscx"
    output_path = Path(__file__).parent / "sample-output/Test-Score/Test-Score.mscx"

    merge_musescore_files(file1_path, file2_path, output_path)