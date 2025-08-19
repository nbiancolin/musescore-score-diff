import sys
import xml.etree.ElementTree as ET
import zipfile
import os
import shutil
from enum import Enum
from pathlib import Path

from copy import deepcopy


def new_merge_musescore_files(f1_path, f2_path, output_path=None):
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
    tree1 = ET.parse(f1_path)
    tree2 = ET.parse(f2_path)

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
        staff_name = part.find("trackName").text
        assert staff_name is not None
        try:
            index = part_names.index(staff_name)
            union_part_list.insert(index +1, deepcopy(part))
            part_names.insert(index +1, staff_name)
            union_staff_list.insert(index, deepcopy(staff))
        except ValueError:
            # append to end of list
            print(f"ValueError: {staff_name}")
            union_part_list.append(part)
            part_names.append(staff_name)
            union_staff_list.append(staff)
            continue
        #TODO: Piano staves get added wrong, should be added after the second staff, not the first staff
        

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
    # TODO: Something here is messing up -- drum staff not being copied correctly, eveyrhting works tho
    # assert num_staves == num_parts, f"Num staves: {num_staves}, num parts: {num_parts}\n {[staff.attrib['id'] for staff in union_staff_list]}\n{[staff.attrib['id'] for staff in union_part_list]}"
    #Why are there 11 staves? thats an odd umber ??

    # all staves removed, add back new staves 
    for staff in reversed(union_staff_list):
        staff.attrib["id"] = f"{num_staves}"
        num_staves -= 1
        diff_score.insert(staff_first_index, staff)

    #remove parts:
    for part in parts_to_delete:
        diff_score.remove(part)

    
    for part in reversed(union_part_list):
        part.attrib["id"] = f"{num_parts}"
        num_parts -= 1
        diff_score.insert(part_first_index, part)

    if output_path:
        diff_score_tree.write(output_path, encoding="UTF-8", xml_declaration=True)
    return (diff_score_tree, part_names)


def _measures_are_unchanged(m1: ET.Element, m2: ET.Element) -> bool:
    # Compare tags
    if m1.tag != m2.tag:
        return False
    
    # Compare attributes (ignoring "eid")
    attrs1 = {k: v for k, v in m1.attrib.items() if k != "eid"}
    attrs2 = {k: v for k, v in m2.attrib.items() if k != "eid"}
    if attrs1 != attrs2:
        return False
    
    # Compare text (strip whitespace differences)
    if (m1.text or '').strip() != (m2.text or '').strip():
        return False
    
    # Compare tail text (optional, depends if you care about formatting)
    if (m1.tail or '').strip() != (m2.tail or '').strip():
        return False
    
    # Compare number of children
    children1 = [c for c in m1 if c.tag != "eid"]
    children2 = [c for c in m2 if c.tag != "eid"]
    if len(children1) != len(children2):
        return False
    
    # Compare children recursively
    return all(_measures_are_unchanged(c1, c2) for c1, c2 in zip(children1, children2))

def _make_color_elem(egb: tuple[int, int, int]) -> ET.Element:
    return ET.fromstring('<color r="242" g="102" b="34" a="100"/>')

def mark_differences_in_measure(measure1: ET.Element, measure2: ET.Element) -> None:
    """
    Assume measure 1 is old (red) and measure2 is new (green)
    """

    for voice1, voice2 in zip(measure1.findall("voice"), measure2.findall("voice")):
        children1 = [c for c in voice1 if c.tag != "eid"]
        children2 = [c for c in voice2 if c.tag != "eid"]
        
        for i in range(max(len(children1), len(children2))):
            c1 = children1[i] if i < len(children1) else None
            c2 = children2[i] if i < len(children2) else None
            str1 = ET.tostring(c1) if c1 else ""
            str2 = ET.tostring(c2) if c2 else ""
            if str1 != str2:
                #color elements red and green respetively:
                if c1:
                    c1.insert(2, _make_color_elem((1, 0, 0)))
                if c2:
                    c2.insert(2, _make_color_elem((1, 1, 1)))




def _make_highlight_start(rgb: tuple[int, int, int], num_measures: int = 1) -> ET.Element:
    spanner = ET.Element("Spanner")
    spanner.attrib["type"] = "TextLine"
    text_line = ET.SubElement(spanner, "TextLine")
    linkedMain = ET.SubElement(text_line, "linkedMain")
    linkedMain.text = ""
    diagonal = ET.SubElement(text_line, "diagonal")
    diagonal.text = "0"
    color = ET.SubElement(text_line, "color")
    color.attrib["r"] = str(rgb[0])
    color.attrib["g"] = str(rgb[1])
    color.attrib["b"] = str(rgb[2])
    segment = ET.SubElement(text_line, "Segment")
    subtype = ET.SubElement(segment, "subtype")
    subtype.text = "0"
    offset = ET.SubElement(segment, "offset")
    offset.attrib["x"] = "0"
    offset.attrib["y"] = "2"
    off2 = ET.SubElement(segment, "off2")
    off2.attrib["x"] = "0"
    off2.attrib["y"] = "0"
    min_distance = ET.SubElement(segment, "minDistance")
    min_distance.text="-999"

    next_elem = ET.SubElement(spanner, "next")
    location = ET.SubElement(next_elem, "location")
    measures = ET.SubElement(location, "measures")
    measures.text = str(num_measures)

    return spanner

    # return ET.fromstring(
    #     '<Spanner type="TextLine">\n'
    #         '<TextLine>\n'
    #             # '<eid>icWAADvE7ZE_UNlVmVRZvkP</eid>'
    #             '<linkedMain/>\n'
    #             '<diagonal>0</diagonal>\n'
    #             '<lineWidth>5</lineWidth>\n'
    #             f'<color r="{rgb[0]}" g="{rgb[1]}" b="{rgb[2]}" a="100"/>\n'
    #             '<Segment>\n'
    #                 '<subtype>0</subtype>\n'
    #                 '<offset x="0" y="2"/>\n'
    #                 '<off2 x="0" y="0"/>\n'
    #                 '<minDistance>-999</minDistance>\n'
    #                 # '<eid>nblchKlbnaD_7SJXnVEKpAF</eid>'
    #                 '</Segment>\n'
    #             '</TextLine>\n'
    #         '<next>\n'
    #             '<location>\n'
    #             f'<measures>{num_measures}</measures>\n'
    #             '</location>\n'
    #             '</next>\n'
    #         '</Spanner>\n'
    # )

#TODO: revisit highlighting eventually, pivot towards

def _make_highlight_end(num_measures: int = 1) -> ET.Element:

    spanner = ET.Element("Spanner")
    spanner.attrib["type"] = "TextLine"
    prev_elem = ET.SubElement(spanner, "prev")
    location = ET.SubElement(prev_elem, "location")
    measures = ET.SubElement(location, "measures")
    measures.text = f"-{num_measures}"

    return spanner


    # return ET.fromstring(
    #     '<Spanner type="TextLine">\n'
    #         '<prev>\n'
    #             '<location>\n'
    #             f'<measures>-{num_measures}</measures>\n'
    #             '</location>\n'
    #             '</prev>\n'
    #         '</Spanner>\n'
    # )

def _highlight_measure(staff: ET.Element, index: int, rgb: tuple[int, int, int], num_measures: int = 1) -> None:
    """
    Highlight measure
    """
    start = staff[index]
    end = staff[index + num_measures]
    start.insert(1, _make_highlight_start(rgb, num_measures))
    end.insert(1, _make_highlight_end(num_measures))


def compute_diff_single_staff(staff1: ET.Element, staff2: ET.Element) -> None:
    """
    Given two staves to compare, (assuming staff 1 is the old staff, and staff 2 is the "new" staff)
    go through them measure by measure
    if measures are the same: set staff2 to be a measure of rest (ie. no difference)
    if different:
        colour notes red in old staff, green in new staff
    """
    assert len(staff1) == len(staff2), "ERROR: Both staves don't have the same number of measures!"
    for i in range(len(staff1) -1):
        m1 = staff1[i]
        m2 = staff2[i]
        if m1.tag != "Measure" or m2.tag != "Measure":
            print("Non measure tag encountered -- continuing")

        if _measures_are_unchanged(m1, m2):
            #set m2 to be a full bar of rest
            continue

        #if different, highlight measures
        #TODO: Show diff more creatively
        #   IDEA: set a flag that shows how much detail (can show just a measure highlight, or individual notes colored)
        mark_differences_in_measure(m1, m2)
        #eventually, do the hihglight in a big line  


def compute_diff(diff_score: ET.Element, part_names: list[str]):
    """
    GO through score 2 staves at a time (for now, assuming all )
    """
    staves = diff_score.findall("Staff")
    cont = False
    for i in range(0, len(staves) -1):
        if cont:
            cont = False
            continue
        staff1 = staves[i]
        staff2 = staves[i +1]
        if part_names[i] != part_names[i +1]:
            print("New score found, continuing and not adding anything")
            continue
        compute_diff_single_staff(staff1, staff2)
        cont = True


def export(diff_score_tree, output_path):
    diff_score_tree.write(output_path, encoding="UTF-8", xml_declaration=True)

if __name__ == "__main__":
    file1_path = "tests\\fixtures\\Test-Score\\Test-Score.mscx"
    file2_path = "tests\\fixtures\\Test-Score-2\\Test-Score-2.mscx"
    output_path = "tests\\sample-output\\Test-Score\\Test-Score.mscx"

    #TODO: Eventually do the parts independantly,

    # file1_path = fixtures_dir / "Test-Score/Excerpts/1_Trombone/1-Trombone.mscx"
    # file2_path = fixtures_dir / "Test-Score-2/Excerpts/1_Trombone/1-Trombone.mscx"
    # output_path = Path(__file__).parent / "sample-output/Test-Score/Excerpts/1_Trombone/1-Trombone.mscx"

    diff_score_tree, part_names = new_merge_musescore_files(file1_path, file2_path)
    diff_root = diff_score_tree.getroot()
    diff_score = diff_root.find("Score")
    compute_diff(diff_score, part_names)
    export(diff_score_tree, output_path)

    print("Musescore files merged!")
