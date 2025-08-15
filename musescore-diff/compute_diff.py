import sys
import xml.etree.ElementTree as ET
import zipfile
import os
import shutil
from enum import Enum

import copy

TEMP_DIR 



def create_diff_score(input_score: str, output_score: str):
    """
    Create `diff-score`, the score where the diff calculation will take place

    Copy score from score1 into diffscore, then create new staves in diffscore
    """

    def get_part_name_from_staff_id(score: ET.Element, staff_id: int): # Returns tuple of dict of (int, ET.Element)
        for part in score.findall("Part"):
            if part.find("Staff").attrib["id"] == staff_id:
                assert part.find("trackName")
                return part.find("trackName").text
        return "N/A"


    parser = ET.XMLParser()
    score1_tree = ET.parse(input_score, parser)
    score1_root = score1_tree.getroot()
    score1 = score1_root.find("Score")

    parser2 = ET.XMLParser()
    score2_tree = ET.parse(input_score, parser2)
    score2_root = score2_tree.getroot()
    score2 = score2_root.find("Score")

    diff_score_tree = copy.deepcopy(score1_tree)
    diff_score_root = diff_score_tree.getroot()
    diff_score = diff_score_root.find("Score")

    score1_staves = {}
    for staff in score1.findall("Staff"):
        score1_staves[staff.attrib["id"]] = staff

    score2_staves = {}
    for staff in score2.findall("Staff"):
        score2_staves[staff.attrib["id"]] = staff

    assert score2
    assert score1
    #TODO: use part names instead of IDs, bc if instruments are added or removed, the IDs change
    for staff in score2.findall("Staff"):
        staff.attrib["id"] = f"{staff.attrib["id"]}-1"
        diff_score.append(staff)
    
    return {"diff_score_tree": diff_score_tree, "score1_staves": score1_staves, "score2_staves": score2_staves}
        



def process_diff(diff_score_tree):
    """
    Grab staves
    """