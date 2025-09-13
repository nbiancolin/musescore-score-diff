from musescore_score_diff.display_diff import compare_musescore_files, compare_mscz_files

import warnings
import pytest

def test_mscz_compare_visually():
    compare_mscz_files("tests/fixtures/Test-Score.mscz", "tests/fixtures/Test-Score-2.mscz", "tests/fixtures/_sample_output/Test-Score.mscz")
    warnings.warn("Check the outputted file that output looks correct!")