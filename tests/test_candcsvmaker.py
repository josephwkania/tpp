import os
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from candcsvmaker import gencandcsv  # noqa: E402


CAND_COLUMNS = [
    "snr",
    "ssample",
    "stime",
    "width",
    "dmidx",
    "dm",
    "cluster_size",
    "startsamp",
    "endsamp",
]


def write_cand_file(path, rows):
    """rows: list of dicts with keys from CAND_COLUMNS (missing keys default to 0)."""
    lines = []
    for row in rows:
        values = [str(row.get(col, 0)) for col in CAND_COLUMNS]
        lines.append("\t".join(values))
    path.write_text("\n".join(lines) + "\n")
    return path


def make_source_file(tmp_path, name="data_test.fil"):
    f = tmp_path / name
    f.write_bytes(b"\x00")
    return f


PASSING_ROW = dict(
    snr=10,
    ssample=100,
    stime=1.5,
    width=3,
    dmidx=5,
    dm=50,
    cluster_size=4,
    startsamp=99,
    endsamp=101,
)


@pytest.fixture
def source_file(tmp_path):
    return make_source_file(tmp_path)


def test_filters_rows_by_snr_dm_and_clustersize(tmp_path, source_file):
    cand = write_cand_file(
        tmp_path / "a.cand",
        [
            PASSING_ROW,
            dict(PASSING_ROW, snr=3),  # fails snr threshold
            dict(PASSING_ROW, dm=5),  # fails dm_min
            dict(PASSING_ROW, dm=6000),  # fails dm_max
            dict(PASSING_ROW, cluster_size=1),  # fails clustersize
        ],
    )
    out = tmp_path / "out.csv"

    gencandcsv([str(cand)], [str(source_file)], outname=str(out))

    df = pd.read_csv(out)
    assert len(df) == 1
    assert df.iloc[0]["snr"] == PASSING_ROW["snr"]
    assert df.iloc[0]["dm"] == PASSING_ROW["dm"]


def test_output_columns_and_values(tmp_path, source_file):
    cand = write_cand_file(tmp_path / "a.cand", [PASSING_ROW])
    out = tmp_path / "out.csv"

    gencandcsv(
        [str(cand)],
        [str(source_file)],
        label=1,
        chan_mask="/some/mask/path.bad",
        outname=str(out),
    )

    df = pd.read_csv(out)
    assert list(df.columns) == [
        "file",
        "snr",
        "stime",
        "width",
        "dm",
        "label",
        "chan_mask_path",
        "num_files",
    ]
    row = df.iloc[0]
    assert row["file"] == os.path.abspath(str(source_file))
    assert row["snr"] == PASSING_ROW["snr"]
    assert row["stime"] == PASSING_ROW["stime"]
    assert row["width"] == PASSING_ROW["width"]
    assert row["dm"] == PASSING_ROW["dm"]
    assert row["label"] == 1
    assert row["chan_mask_path"] == "/some/mask/path.bad"
    assert row["num_files"] == 1


def test_num_files_reflects_filelist_length(tmp_path, source_file):
    second = make_source_file(tmp_path, "data_test2.fil")
    cand = write_cand_file(tmp_path / "a.cand", [PASSING_ROW])
    out = tmp_path / "out.csv"

    gencandcsv([str(cand)], [str(source_file), str(second)], outname=str(out))

    df = pd.read_csv(out)
    assert (df["num_files"] == 2).all()


def test_multiple_cand_files_are_appended(tmp_path, source_file):
    cand1 = write_cand_file(tmp_path / "a.cand", [PASSING_ROW])
    cand2 = write_cand_file(tmp_path / "b.cand", [PASSING_ROW, PASSING_ROW])
    out = tmp_path / "out.csv"

    gencandcsv([str(cand1), str(cand2)], [str(source_file)], outname=str(out))

    df = pd.read_csv(out)
    assert len(df) == 3


def test_no_candidates_pass_threshold_writes_header_only(tmp_path, source_file):
    cand = write_cand_file(tmp_path / "a.cand", [dict(PASSING_ROW, snr=0)])
    out = tmp_path / "out.csv"

    gencandcsv([str(cand)], [str(source_file)], outname=str(out))

    df = pd.read_csv(out)
    assert len(df) == 0
    assert list(df.columns) == [
        "file",
        "snr",
        "stime",
        "width",
        "dm",
        "label",
        "chan_mask_path",
        "num_files",
    ]


def test_custom_thresholds_are_applied(tmp_path, source_file):
    cand = write_cand_file(
        tmp_path / "a.cand",
        [
            dict(PASSING_ROW, snr=7, dm=20, cluster_size=3),
            dict(PASSING_ROW, snr=9, dm=20, cluster_size=3),
        ],
    )
    out = tmp_path / "out.csv"

    gencandcsv(
        [str(cand)],
        [str(source_file)],
        snr_th=8,
        dm_min=10,
        dm_max=100,
        clustersize_th=2,
        outname=str(out),
    )

    df = pd.read_csv(out)
    assert len(df) == 1
    assert df.iloc[0]["snr"] == 9


def test_outname_appends_csv_extension_when_missing(tmp_path, source_file):
    cand = write_cand_file(tmp_path / "a.cand", [PASSING_ROW])
    out = tmp_path / "out_without_ext"

    gencandcsv([str(cand)], [str(source_file)], outname=str(out))

    assert (tmp_path / "out_without_ext.csv").exists()


@pytest.mark.parametrize("ext", ["fits", "sf", "fil"])
def test_outname_defaults_to_first_file_basename(tmp_path, monkeypatch, ext):
    monkeypatch.chdir(tmp_path)
    source = make_source_file(tmp_path, f"observation.{ext}")
    cand = write_cand_file(tmp_path / "a.cand", [PASSING_ROW])

    gencandcsv([str(cand)], [str(source)])

    assert (tmp_path / "observation.csv").exists()


def test_unsupported_extension_without_outname_raises_typeerror(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source = make_source_file(tmp_path, "observation.txt")
    cand = write_cand_file(tmp_path / "a.cand", [PASSING_ROW])

    with pytest.raises(TypeError):
        gencandcsv([str(cand)], [str(source)])


def test_empty_candsfiles_raises_valueerror(tmp_path, source_file):
    with pytest.raises(ValueError):
        gencandcsv([], [str(source_file)], outname=str(tmp_path / "out.csv"))


def test_empty_filelist_raises_valueerror(tmp_path, source_file):
    cand = write_cand_file(tmp_path / "a.cand", [PASSING_ROW])
    with pytest.raises(ValueError):
        gencandcsv([str(cand)], [], outname=str(tmp_path / "out.csv"))


def test_missing_source_file_raises_filenotfounderror(tmp_path, source_file):
    cand = write_cand_file(tmp_path / "a.cand", [PASSING_ROW])
    missing = tmp_path / "does_not_exist.fil"

    with pytest.raises(FileNotFoundError):
        gencandcsv(
            [str(cand)],
            [str(source_file), str(missing)],
            outname=str(tmp_path / "out.csv"),
        )
