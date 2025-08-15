import sys
import xml.etree.ElementTree as ET
import zipfile
import os
import shutil
from enum import Enum

from copy import deepcopy



def merge_musescore_files(file1_path, file2_path, output_path):
    # Parse both files
    tree1 = ET.parse(file1_path)
    tree2 = ET.parse(file2_path)

    root1 = tree1.getroot()
    root2 = tree2.getroot()

    # Locate the <Score> element in each
    score1 = root1.find("Score")
    score2 = root2.find("Score")

    if score1 is None or score2 is None:
        raise ValueError("Both files must contain a <Score> element.")

    # Collect all Staff IDs from score1
    existing_staff_ids = set()
    for staff in score1.findall(".//Staff"):
        existing_staff_ids.add(staff.attrib.get("id"))

    # Map old staff IDs from file2 to new IDs if needed
    staff_id_map = {}
    for staff in score2.findall(".//Staff"):
        sid = staff.attrib.get("id")
        if sid in existing_staff_ids:
            # Keep same ID for matching staff
            staff_id_map[sid] = sid
        else:
            # Make a new ID with "-1" suffix
            new_id = f"{sid}-1"
            staff_id_map[sid] = new_id

    # Merge <Part> elements from file2
    for part in score2.findall("./Part"):
        # Clone the part so we don't mess with tree2
        part_copy = deepcopy(part)
        has_new_staff = False

        # Update staff IDs in this part
        for staff in part_copy.findall("Staff"):
            old_id = staff.attrib.get("id")
            if old_id in staff_id_map:
                staff.attrib["id"] = staff_id_map[old_id]
                if staff_id_map[old_id] != old_id:
                    has_new_staff = True

        if has_new_staff:
            # Append to score1
            score1.append(part_copy)

    # Merge top-level <Staff> blocks outside of <Part>
    for staff in score2.findall("./Staff"):
        old_id = staff.attrib.get("id")
        if old_id in staff_id_map and staff_id_map[old_id] != old_id:
            staff_copy = deepcopy(staff)
            staff_copy.attrib["id"] = staff_id_map[old_id]
            score1.append(staff_copy)

    # Save merged file
    tree1.write(output_path, encoding="UTF-8", xml_declaration=True)