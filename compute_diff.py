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
    file1_ids = [
        int(s.get("id"))
        for s in score1.findall("./Staff")
        if s.get("id") and s.get("id").isdigit()
    ]
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


def new_merge_musescore_files(f1_path, f2_path, output_path):
    """
    read in f1 and f2, create diff_score that is union of both scores

    make list of all parts in f1
    and all staves in f1
        Note that their IDs line up!

    make diff_score a deep_copy of score 1

    then, copy over all parts and scores from staff 2 into diff_score
    create list union_part_list and union_staff_list
    when adding a part to the part list:
        - simultaneously add the staff to the staff list
        - Need to insert it in the correct position
            - so, if the staff name exists in the list, name staff "<name>-1"
            - set all IDs by their position in the list afterwards,

    then, once lists are creatd
    overwrite all parts in diff_score with the parts (in order) from part_list
    and overwrite all staves in diff_score with the scores (in order) from score_list
    """
    tree1 = ET.parse(file1_path)
    tree2 = ET.parse(file2_path)

    root1 = tree1.getroot()
    root2 = tree2.getroot()

    score1 = root1.find("Score")
    score2 = root2.find("Score")
    if score1 is None or score2 is None:
        raise ValueError("Both files must contain a <Score> element.")

    union_part_list = [part for part in score1.findall("Part")]
    part_names = [part.find("trackName").text for part in score1.findall("Part")]
    union_staff_list = [staff for staff in score1.findall("Staff")]

    for part, staff in zip(score2.findall("Part"), score2.findall("Staff")):
        assert part.attrib["id"] == staff.attrib["id"], (
            "ERROR: Somehow part and score IDs got out of sync"
        )
        staff_name = part.find("trackName")
        assert staff_name
        try:
            index = part_names.index(staff_name)
        except ValueError:
            # append to end of list
            union_part_list.append(part)
            part_names.append(staff_name)
            union_staff_list.append(staff)
            continue

        union_part_list.insert(index +1, deepcopy(part))
        part_names.insert(index +1, deepcopy(part.find("trackName")))
        union_staff_list.insert(index, deepcopy(staff))

    diff_score_tree = deepcopy(tree1)

    # remove all parts, and add back all parts from union_part_list (update IDs as they are inserted)

    diff_root = diff_score_tree.getroot()
    diff_score = diff_root.find("Score")

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
        
    assert part_first_index != -1, "Could not find any parts in diff-score..."
    assert staff_first_index != -1, "Could not find any staves in diff-score..."

    num_staves = len(union_staff_list)
    num_parts = len(union_part_list)
    assert num_staves == num_parts

    # all staves removed, add back new staves 
    for staff in reversed(union_staff_list):
        diff_score.insert(staff_first_index, staff)

    #remove parts:
    for part in parts_to_delete:
        diff_score.remove(part)

    
    for part in reversed(union_part_list):
        diff_score.insert(part_first_index, part)

    diff_score_tree.write(output_path, encoding="UTF-8", xml_declaration=True)




if __name__ == "__main__":
    file1_path = "tests\\fixtures\\Test-Score\\Test-Score.mscx"
    file2_path = "tests\\fixtures\\Test-Score-2\\Test-Score-2.mscx"
    output_path = "tests\\sample-output\\Test-Score\\Test-Score.mscx"

    new_merge_musescore_files(file1_path, file2_path, output_path)

    print("Musescore files merged!")
