import sys
import xml.etree.ElementTree as ET
import zipfile
import os
import shutil
from enum import Enum

from copy import deepcopy



def merge_musescore_files(file1_path, file2_path, output_path):
    """
    Merge two MuseScore (MSCX) files by appending a suffixed copy of file2's
    parts/staves into file1.

    - All <Part id="..."> from file2 become "<old>-1".
    - All <Staff id="..."> (both in <Part> and top-level <Staff>) from file2 become "<old>-1".
    - Top-level <Staff> blocks from file2 are appended after file1's top-level <Staff>s.

    Note: This keeps eids as-is. If you need to avoid potential duplicate <eid> collisions,
    strip them in the deepcopy before appending.
    """
    tree1 = ET.parse(file1_path)
    tree2 = ET.parse(file2_path)

    root1 = tree1.getroot()
    root2 = tree2.getroot()

    score1 = root1.find("Score")
    score2 = root2.find("Score")
    if score1 is None or score2 is None:
        raise ValueError("Both files must contain a <Score> element.")

    # Build a direct map for file2 staff ids -> suffixed ids
    staff_id_map = {}
    for staff in score2.findall(".//Staff"):
        sid = staff.get("id")
        if sid:
            staff_id_map[sid] = f"{sid}-1"

    # ---- Append Parts from file2 (always), remapping Part id and child Staff ids
    for part in score2.findall("./Part"):
        part_copy = deepcopy(part)

        # Remap the Part's own id (to avoid Part id collisions)
        old_part_id = part_copy.get("id")
        if old_part_id:
            part_copy.set("id", f"{old_part_id}-1")

        # Remap <Staff id="..."> within the part
        for st in part_copy.findall("./Staff"):
            old_sid = st.get("id")
            if old_sid in staff_id_map:
                st.set("id", staff_id_map[old_sid])

        score1.append(part_copy)

    # ---- Append top-level <Staff> blocks from file2, remapping ids
    for staff in score2.findall("./Staff"):
        old_sid = staff.get("id")
        staff_copy = deepcopy(staff)
        if old_sid:
            staff_copy.set("id", staff_id_map.get(old_sid, f"{old_sid}-1"))
        score1.append(staff_copy)

    # Write result
    tree1.write(output_path, encoding="UTF-8", xml_declaration=True)