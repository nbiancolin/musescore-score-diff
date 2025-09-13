from musescore_score_diff import compare_musescore_files, compare_mscz_files

from musescore_score_diff.display_diff import merge_musescore_files_for_diff

import warnings
import pytest

FILE1_MSCZ_PATH = "tests/fixtures/Test-Score.mscz"
FILE2_MSCZ_PATH = "tests/fixtures/Test-Score-2.mscz"

FILE1_UNCOMPRESSED_PATH = "tests/fixtures/Test-Score/Test-Score.mscx"
FILE2_UNCOMPRESSED_PATH = "tests/fixtures/Test-Score-2/Test-Score-2.mscx"

def test_mscz_compare_visually():
    # compare_mscz_files("tests/fixtures/Test-Score.mscz", "tests/fixtures/Test-Score-2.mscz", "tests/fixtures/_sample_output/Test-Score.mscz")
    warnings.warn("Check the outputted file that output looks correct!")


def initial_diff_score_generated_properly():
    diff_score_tree, _ = merge_musescore_files_for_diff(FILE1_UNCOMPRESSED_PATH, FILE2_UNCOMPRESSED_PATH)
    diff_score_tree.write("tests/fixtures/_sample_output/Test-Score/Test-Score.mscx", encoding="UTF-8", xml_declaration=True)
    warnings.warn("Check the outputted file that output looks correct!")