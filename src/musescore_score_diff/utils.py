import xml.etree.ElementTree as ET
import hashlib
from enum import Enum

class State(Enum):
    UNCHANGED = 1
    MODIFIED = 2
    INSERTED = 3
    REMOVED = 4


def _hash_measure(measure: ET.Element) -> str:
    """
    Return a stable hash of the measure's XML content.
    Allows for quick comparison
    """
    raw = ET.tostring(measure, encoding="utf-8")
    # normalize whitespace
    normalized = b"".join(raw.split())
    return hashlib.md5(normalized).hexdigest()

def _sanitize_measure(measure: ET.Element) -> ET.Element:
    """ Remove all the useless (to us) junk from musescore measures"""

    #remove any tag that says "EID"
    #remove any "LinkedMain"
    to_remove = []
    for elem in measure.iter():
        for child in list(elem):
            if child.tag in ("eid", "linkedMain"):
                to_remove.append((elem, child))
    
    for parent, child in to_remove:
        parent.remove(child)
    return measure

def extract_measures(filename: str) -> list[tuple[int, str, ET.Element]]:
    """Parse uncompressed mcsx and return list of (number, hash, element)."""
    parser = ET.XMLParser()
    tree = ET.parse(filename, parser)
    root = tree.getroot()
    score = root.find("Score")
    if score is None:
        raise ValueError("No <Score> tag found in the XML.")

    staff = score.find("Staff")
    assert staff is not None

    measures = []
    score_measures = staff.findall("Measure")
    for i in range(len(score_measures)):
        m = _sanitize_measure(score_measures[i])
        num = i+1
        
        h = _hash_measure(m)
        measures.append((num, h, m))
    return measures
