import sys
import xml.etree.ElementTree as ET
import zipfile
import os
import shutil
from enum import Enum
from pathlib import Path

from copy import deepcopy

def merge_musescore_files(file1_path, file2_path, output_path):
    """
    Merge two MuseScore (MSCX) files into one Score with:
      - Interleaving of matching staves/parts (file1, then file2 match)
      - Unmatched staves/parts appended to the end
      - Sequential IDs after merge
      - processing_id preserved for mapping
    """
    tree1 = ET.parse(file1_path)
    tree2 = ET.parse(file2_path)

    root1 = tree1.getroot()
    root2 = tree2.getroot()

    score1 = root1.find("Score")
    score2 = root2.find("Score")
    if score1 is None or score2 is None:
        raise ValueError("Both files must contain a <Score> element.")

    # Find highest existing ID in score1
    file1_ids = [int(s.get("id")) for s in score1.findall("./Staff") if s.get("id") and s.get("id").isdigit()]
    max_id_file1 = max(file1_ids) if file1_ids else 0

    # Build staff ID remapping for score2
    staff_id_map = {}
    next_id = max_id_file1 + 1
    for staff in score2.findall("./Staff"):
        old_id = staff.get("id")
        if old_id not in staff_id_map and old_id and old_id.isdigit():
            staff_id_map[old_id] = str(next_id)
            next_id += 1

    # Ensure file1 has processing_id
    for part in score1.findall("./Part"):
        part.set("processing_id", part.get("id"))
    for staff in score1.findall("./Staff"):
        staff.set("processing_id", staff.get("id"))

    # Helper: find parts/staves in score2 by processing_id
    def get_matching_from_file2(pid):
        matching_parts = []
        matching_staves = []
        for part in score2.findall("./Part"):
            if part.get("id") == pid:
                pcopy = deepcopy(part)
                pcopy.set("id", staff_id_map.get(pid, pid))
                pcopy.set("processing_id", pid)
                for st in pcopy.findall("./Staff"):
                    sid = st.get("id")
                    if sid in staff_id_map:
                        st.set("id", staff_id_map[sid])
                        st.set("processing_id", sid)
                matching_parts.append(pcopy)
        for staff in score2.findall("./Staff"):
            if staff.get("id") == pid:
                scopy = deepcopy(staff)
                scopy.set("id", staff_id_map.get(pid, pid))
                scopy.set("processing_id", pid)
                matching_staves.append(scopy)
        return matching_parts, matching_staves

    used_file2_ids = set()

    # Interleave matching
    i = 0
    while i < len(score1):
        elem = score1[i]
        if elem.tag in ("Part", "Staff"):
            pid = elem.get("processing_id")
            if pid:
                parts2, staves2 = get_matching_from_file2(pid)
                for p in parts2:
                    i += 1
                    score1.insert(i, p)
                    used_file2_ids.add(p.get("processing_id"))
                for s in staves2:
                    i += 1
                    score1.insert(i, s)
                    used_file2_ids.add(s.get("processing_id"))
        i += 1

    # Append unmatched from score2
    for part in score2.findall("./Part"):
        if part.get("id") not in used_file2_ids:
            pcopy = deepcopy(part)
            pcopy.set("id", staff_id_map.get(part.get("id"), part.get("id")))
            pcopy.set("processing_id", part.get("id"))
            for st in pcopy.findall("./Staff"):
                sid = st.get("id")
                if sid in staff_id_map:
                    st.set("id", staff_id_map[sid])
                    st.set("processing_id", sid)
            score1.append(pcopy)
    for staff in score2.findall("./Staff"):
        if staff.get("id") not in used_file2_ids:
            scopy = deepcopy(staff)
            scopy.set("id", staff_id_map.get(staff.get("id"), staff.get("id")))
            scopy.set("processing_id", staff.get("id"))
            score1.append(scopy)

    # Renumber IDs in XML order
    current_id = 1
    for elem in score1.findall("./Part") + score1.findall("./Staff"):
        elem.set("id", str(current_id))
        current_id += 1

    # Save merged file
    tree1.write(output_path, encoding="UTF-8", xml_declaration=True)


if __name__ == "__main__":
    fixtures_dir = Path(__file__) / "tests/fixtures"
    file1_path = fixtures_dir / "Test-Score/Test-Score.mscx"
    file2_path = fixtures_dir / "Test-Score-2/Test-Score-2.mscx"
    output_path = Path(__file__) / "tests/sample-output/Test-Score/Test-Score.mscx"

    merge_musescore_files(file1_path, file2_path, output_path)