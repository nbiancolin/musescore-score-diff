import sys
import xml.etree.ElementTree as ET
import zipfile
import os
import shutil
from copy import deepcopy
from typing import List, Tuple

# Assuming these are imported from your utils
from .utils import extract_measures, State

TEMP_DIR = "blob/temp"

def lcs(seq1: list[str], seq2: list[str]) -> list[list[int]]:
    """Compute LCS DP table."""
    n, m = len(seq1), len(seq2)
    L = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n):
        for j in range(m):
            if seq1[i] == seq2[j]:
                L[i+1][j+1] = L[i][j] + 1
            else:
                L[i+1][j+1] = max(L[i][j+1], L[i+1][j])
    return L

def backtrack(L: list[list[int]], measures1, measures2) -> dict[int, State]:
    """Backtrack through LCS to reconstruct diff."""
    diffs = {}
    i, j = len(measures1), len(measures2)
    while i > 0 or j > 0:
        if i > 0 and j > 0 and measures1[i-1][1] == measures2[j-1][1]:
            diffs[measures1[i-1][0]] = State.UNCHANGED
            i -= 1
            j -= 1
        elif i > 0 and j > 0 and measures1[i-1][0] == measures2[j-1][0]:
            diffs[measures1[i-1][0]] = State.MODIFIED
            i -= 1
            j -= 1
        elif j > 0 and (i == 0 or L[i][j-1] >= L[i-1][j]):
            diffs[measures2[j-1][0]] = State.INSERTED
            j -= 1
        elif i > 0 and (j == 0 or L[i][j-1] < L[i-1][j]):
            diffs[measures1[i-1][0]] = State.REMOVED
            i -= 1
    return diffs

def compute_diff_measures(file1: str, file2: str) -> dict[int, State]:
    """Compute diff using the provided helper functions."""
    measures1, measures2 = extract_measures(file1), extract_measures(file2)
    seq1 = [h for (_, h, _) in measures1]
    seq2 = [h for (_, h, _) in measures2]
    L = lcs(seq1, seq2)
    return backtrack(L, measures1, measures2)

def _measures_are_unchanged(m1: ET.Element, m2: ET.Element) -> bool:
    """Check if two measures are identical (from your existing code)."""
    if m1.tag != m2.tag:
        return False
    
    attrs1 = {k: v for k, v in m1.attrib.items() if k != "eid"}
    attrs2 = {k: v for k, v in m2.attrib.items() if k != "eid"}
    if attrs1 != attrs2:
        return False
    
    if (m1.text or '').strip() != (m2.text or '').strip():
        return False
    
    if (m1.tail or '').strip() != (m2.tail or '').strip():
        return False
    
    children1 = [c for c in m1 if c.tag != "eid"]
    children2 = [c for c in m2 if c.tag != "eid"]
    if len(children1) != len(children2):
        return False
    
    return all(_measures_are_unchanged(c1, c2) for c1, c2 in zip(children1, children2))

def _make_color_elem(rgb: tuple[int, int, int]) -> ET.Element:
    """Create color element for highlighting (from your existing code)."""
    return ET.fromstring(f'<color r="{rgb[0]}" g="{rgb[1]}" b="{rgb[2]}" a="255"/>')

def _make_cutaway() -> ET.Element:
    """Create cutaway element (from your existing code)."""
    return ET.fromstring("<cutaway>1</cutaway>")

def mark_differences_in_measure(measure1: ET.Element, measure2: ET.Element) -> None:
    """Mark differences within a measure (adapted from your existing code)."""
    for voice1, voice2 in zip(measure1.findall("voice"), measure2.findall("voice")):
        children1 = [c for c in voice1 if c.tag != "eid"]
        children2 = [c for c in voice2 if c.tag != "eid"]
        
        for i in range(max(len(children1), len(children2))):
            c1 = deepcopy(children1[i]) if i < len(children1) else None
            c2 = deepcopy(children2[i]) if i < len(children2) else None

            if c1 is not None:
                for child in c1:
                    if child.tag == "eid":
                        c1.remove(child)
                    if child.tag == "Chord":
                        for c in child:
                            if c.tag == "eid":
                                child.remove(c)

            if c2 is not None:
                for child in c2:
                    if child.tag == "eid":
                        c2.remove(child)
                    if child.tag == "Chord":
                        for c in child:
                            if c.tag == "eid":
                                child.remove(c)

            str1 = ET.tostring(c1) if c1 is not None else ""
            str2 = ET.tostring(c2) if c2 is not None else ""
            if str1 != str2:
                # Color elements red and green respectively
                if c1 is not None and i < len(children1):
                    if children1[i].tag == "Chord":
                        for c in children1[i].findall("Note"):
                            c.insert(2, _make_color_elem((200, 0, 0)))
                    children1[i].insert(2, _make_color_elem((200, 0, 0)))
                if c2 is not None and i < len(children2):
                    if children2[i].tag == "Chord":
                        for c in children2[i].findall("Note"):
                            c.insert(2, _make_color_elem((32, 186, 32)))
                    children2[i].insert(2, _make_color_elem((32, 186, 32)))

def merge_musescore_files_for_diff(f1_path: str, f2_path: str) -> Tuple[ET.ElementTree, List[str]]:
    """
    Merge two MuseScore files for diff display (adapted from your new_merge_musescore_files).
    """
    tree1 = ET.parse(f1_path)
    tree2 = ET.parse(f2_path)

    root1 = tree1.getroot()
    root2 = tree2.getroot()

    score1 = root1.find("Score")
    score2 = root2.find("Score")
    if score1 is None or score2 is None:
        raise ValueError("Both files must contain a <Score> element.")

    # Get parts and create union lists
    union_part_list = [part for part in score1.findall("Part")]
    part_names = [part.find("trackName").text for part in score1.findall("Part")]
    union_staff_list = [staff for staff in score1.findall("Staff")]

    # Process parts from score2
    for part, staff in zip(score2.findall("Part"), score2.findall("Staff")):
        assert part.attrib["id"] == staff.attrib["id"], (
            "ERROR: Part and staff IDs got out of sync"
        )
        staff_name = part.find("trackName").text
        assert staff_name is not None
        
        try:
            index = part_names.index(staff_name)
            # Add "-1" suffix for diff version
            p = deepcopy(part)
            track_name_elem = p.find("trackName")
            if track_name_elem is not None:
                track_name_elem.text = f"{staff_name}-1"
            
            # Add cutaway for visual distinction
            s = deepcopy(staff)
            s.append(_make_cutaway())
            
            union_part_list.insert(index + 1, p)
            part_names.insert(index + 1, f"{staff_name}-1")
            union_staff_list.insert(index + 1, s)
        except ValueError:
            # Part doesn't exist in score1, append to end
            print(f"New part found: {staff_name}")
            p = deepcopy(part)
            track_name_elem = p.find("trackName")
            if track_name_elem is not None:
                track_name_elem.text = f"{staff_name}-1"
            
            union_part_list.append(p)
            part_names.append(f"{staff_name}-1")
            union_staff_list.append(deepcopy(staff))

    # Create diff score tree
    diff_score_tree = deepcopy(tree1)
    diff_root = diff_score_tree.getroot()
    diff_score = diff_root.find("Score")

    # Remove existing parts and staves
    list_score = list(diff_score)
    part_first_index = -1
    staff_first_index = -1
    parts_to_delete = []
    
    for i in range(len(list_score)):
        elem = list_score[i]
        if elem.tag == "Part":
            if part_first_index == -1:
                part_first_index = i
            parts_to_delete.append(elem)
        if elem.tag == "Staff":
            if staff_first_index == -1:
                staff_first_index = i
            diff_score.remove(elem)

    assert part_first_index != -1, "Could not find any parts in diff-score"
    assert staff_first_index != -1, "Could not find any staves in diff-score"

    # Add new staves with updated IDs
    num_staves = len(union_staff_list)
    for staff in reversed(union_staff_list):
        staff.attrib["id"] = f"{num_staves}"
        num_staves -= 1
        diff_score.insert(staff_first_index, staff)

    # Remove old parts
    for part in parts_to_delete:
        diff_score.remove(part)

    # Add new parts with updated IDs
    num_parts = len(union_part_list)
    for part in reversed(union_part_list):
        part.attrib["id"] = f"{num_parts}"
        num_parts -= 1
        diff_score.insert(part_first_index, part)

    return (diff_score_tree, part_names)

def compute_diff_single_staff(staff1: ET.Element, staff2: ET.Element) -> None:
    """
    Compare two staves measure by measure and highlight differences.
    """
    for i in range(min(len(staff1), len(staff2))):
        m1 = staff1[i]
        m2 = staff2[i]
        if m1.tag != "Measure" or m2.tag != "Measure":
            continue

        if not _measures_are_unchanged(m1, m2):
            # Mark differences in both measures
            mark_differences_in_measure(m1, m2)
            print(f"Differences found in measure {i + 1}")

def compute_diff_for_score(diff_score: ET.Element, part_names: List[str]) -> None:
    """
    Go through the diff score and compare adjacent staff pairs.
    """
    staves = diff_score.findall("Staff")
    skip_next = False
    
    for i in range(len(staves) - 1):
        if skip_next:
            skip_next = False
            continue
            
        staff1 = staves[i]
        staff2 = staves[i + 1]
        
        # Check if this is a staff pair (original and "-1" version)
        if i < len(part_names) - 1:
            name1 = part_names[i]
            name2 = part_names[i + 1]
            
            if name2 == f"{name1}-1":
                print(f"Comparing staff pair: {name1} vs {name2}")
                compute_diff_single_staff(staff1, staff2)
                skip_next = True
            else:
                print(f"Skipping non-paired staff: {name1}")

def compare_musescore_files(file1_path: str, file2_path: str, output_path: str|None = None) -> str:
    """
    Main function to compare two MuseScore files and create a diff score.
    
    Args:
        file1_path: Path to the old version (score1)
        file2_path: Path to the new version (score2)
        output_path: Optional output path for the diff file
    
    Returns:
        Path to the generated diff file
    """
    # Generate output filename if not provided
    if output_path is None:
        base_name = os.path.splitext(os.path.basename(file1_path))[0]
        output_path = f"diff-{base_name}.mscx"

    print(f"Comparing {file1_path} and {file2_path}")
    
    # Create merged score with both versions
    diff_score_tree, part_names = merge_musescore_files_for_diff(file1_path, file2_path)
    
    # Get the score element
    diff_root = diff_score_tree.getroot()
    diff_score = diff_root.find("Score")
    
    # Create temporary directory for staff comparisons
    temp_dir = os.path.join(TEMP_DIR, "staff_comparisons")
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # Compute and apply differences
        compute_diff_for_score(diff_score, part_names, temp_dir)
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    # Save the diff score
    diff_score_tree.write(output_path, encoding="UTF-8", xml_declaration=True)
    
    print(f"Diff score saved as: {output_path}")
    return output_path

def compare_mscz_files(file1_path: str, file2_path: str, output_path: str|None = None) -> str:
    """
    Compare two .mscz files by extracting and processing their .mscx contents.
    """
    both_mscx_files = []

    # Extract .mscx files from both .mscz files
    for input_path in [file1_path, file2_path]:
        work_dir = os.path.join(TEMP_DIR, os.path.basename(input_path))
        os.makedirs(work_dir, exist_ok=True)
        
        with zipfile.ZipFile(input_path, "r") as zip_ref:
            zip_ref.extractall(work_dir)
            mscx_files = [
                os.path.join(work_dir, f) for f in zip_ref.namelist() 
                if f.endswith(".mscx")
            ]
        both_mscx_files.append(mscx_files)

    # Generate output path if not provided
    if output_path is None:
        base_name = os.path.splitext(os.path.basename(file1_path))[0]
        output_path = f"diff-{base_name}.mscz"

    # Process each .mscx file pair
    output_files = []
    for file1, file2 in zip(both_mscx_files[0], both_mscx_files[1]):
        mscx_output = file1.replace(os.path.basename(file1), f"diff-{os.path.basename(file1)}")
        compare_musescore_files(file1, file2, mscx_output)
        output_files.append(mscx_output)
        print(f"Processed: {os.path.basename(file1)}")

    # Create output .mscz file
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for output_file in output_files:
            arcname = os.path.relpath(output_file, os.path.dirname(output_file))
            zipf.write(output_file, arcname)

    # Clean up temporary files
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    
    print(f"Diff .mscz file created: {output_path}")
    return output_path

def main():
    """Main function to run the diff comparison."""
    if len(sys.argv) not in [3, 4]:
        print("Usage: python musescore_diff.py <old_score> <new_score> [output_path]")
        print("Supports both .mscx and .mscz files")
        sys.exit(1)

    file1_path = sys.argv[1]
    file2_path = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) == 4 else file1_path

    if not os.path.exists(file1_path):
        print(f"Error: File {file1_path} not found")
        sys.exit(1)

    if not os.path.exists(file2_path):
        print(f"Error: File {file2_path} not found")
        sys.exit(1)

    try:
        # Determine file type and process accordingly
        if file1_path.endswith('.mscz') and file2_path.endswith('.mscz'):
            diff_file = compare_mscz_files(file1_path, file2_path, output_path)
        elif file1_path.endswith('.mscx') and file2_path.endswith('.mscx'):
            diff_file = compare_musescore_files(file1_path, file2_path, output_path)
        else:
            print("Error: Both files must be of the same type (.mscx or .mscz)")
            sys.exit(1)
            
        print(f"Successfully created diff file: {diff_file}")
    except Exception as e:
        print(f"Error creating diff: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()