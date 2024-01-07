import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from fbx import from_moz_date, get_opts, main


def moz_date(days: int) -> int:
    base_date: datetime = datetime(2023, 1, 2, 3, 4, 5)
    d = base_date + timedelta(days=days)
    #  Convert to milliseconds.
    return d.timestamp() * 1000000.0


def test_moz_date():
    md = moz_date(0)
    assert from_moz_date(md) == "2023-01-02 03:04:05"
    md = moz_date(-1)
    assert from_moz_date(md) == "2023-01-01 03:04:05"
    md = moz_date(1)
    assert from_moz_date(md) == "2023-01-03 03:04:05"


def make_fake_places_file(file_path: Path):
    assert not file_path.exists(), "Should be a new file."

    con = sqlite3.connect(str(file_path))
    cur = con.cursor()

    cur.execute("CREATE TABLE moz_places (id INTEGER, url TEXT);")

    cur.execute(
        "CREATE TABLE moz_bookmarks (id INTEGER, fk INTEGER, title TEXT, "
        "parent INTEGER, dateAdded INTEGER);"
    )

    #  Insert places (URLs).
    cur.execute(
        "INSERT INTO moz_places VALUES (?, ?);", (1, "http://www.example.com/")
    )

    cur.execute(
        "INSERT INTO moz_places VALUES (?, ?);",
        (2, "http://www.example.com/page1"),
    )

    cur.execute(
        "INSERT INTO moz_places VALUES (?, ?);",
        (3, "http://www.example.com/page2"),
    )
    #  moz_places: id, url

    #  Insert entries for menu and folders.
    cur.execute(
        "INSERT INTO moz_bookmarks VALUES (?, ?, ?, ?, ?);",
        (1, None, "menu", 0, moz_date(0)),
    )
    cur.execute(
        "INSERT INTO moz_bookmarks VALUES (?, ?, ?, ?, ?);",
        (2, None, "folder-1", 1, moz_date(0)),
    )
    cur.execute(
        "INSERT INTO moz_bookmarks VALUES (?, ?, ?, ?, ?);",
        (3, None, "folder-2", 1, moz_date(0)),
    )
    cur.execute(
        "INSERT INTO moz_bookmarks VALUES (?, ?, ?, ?, ?);",
        (4, None, "folder-2a", 3, moz_date(0)),
    )

    #  Insert entries for bookmarked places.
    cur.execute(
        "INSERT INTO moz_bookmarks VALUES (?, ?, ?, ?, ?);",
        (5, 1, "Example Home Page", 2, moz_date(0)),
    )
    cur.execute(
        "INSERT INTO moz_bookmarks VALUES (?, ?, ?, ?, ?);",
        (6, 2, "Example Page 1", 3, moz_date(4)),
    )
    cur.execute(
        "INSERT INTO moz_bookmarks VALUES (?, ?, ?, ?, ?);",
        (7, 3, "Example Page 2", 4, moz_date(2)),
    )

    #  moz_bookmarks: id, fk, title, parent, dateAdded

    con.commit()
    con.close()


@pytest.fixture()
def setup_tmp_source_and_output(tmp_path):
    """
    Creates a fake (well, it's a real sqlite db) places.sqlite to
    simulate one created by Firefox, but with only the fields
    queried by fbx.py.

    Returns a tuple of (src_file, out_dir) where src_file is the
    places.sqlite file and out_dir is the location where output
    files should be written. Both are pathlib.Path objects.
    """
    src_dir = tmp_path / "profile"
    src_dir.mkdir()
    src_file = src_dir / "places.sqlite"
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    make_fake_places_file(src_file)
    return (src_file, out_dir)


def test_opt_default_profile():
    args = ["fbx.py"]
    opts = get_opts(args)
    print(f"\n{opts}")
    assert opts.places_file, (
        "This will fail if there is no Firefox profile found on the host in "
        "the expected location. Either the expected location is wrong, or "
        "Firefox is not installed (or Mozilla changed their data file name)."
    )
    assert isinstance(opts.output_file, Path)


def test_opt_profile(tmp_path: Path):
    p1 = tmp_path.joinpath("profileZ")
    p1.mkdir()
    p1 = p1.joinpath("places.sqlite")
    print(f"\n{p1}")
    make_fake_places_file(p1)

    #  profile2 will have the newer file.
    p2 = tmp_path.joinpath("profileA")
    p2.mkdir()
    p2 = p2.joinpath("places.sqlite")
    print(f"\n{p2}")
    make_fake_places_file(p2)

    args = ["fbx.py", "--profile", str(tmp_path)]
    opts = get_opts(args)
    assert str(p2) == str(opts.places_file), (
        "Should pick the profile with the most recent places.sqlite file when "
        "given a parent of the profile location."
    )


def test_opt_places_file(tmp_path: Path):
    p1 = tmp_path.joinpath("profile1")
    p1.mkdir()
    p1 = p1.joinpath("places.sqlite")
    print(f"\n{p1}")
    make_fake_places_file(p1)

    #  profile2 will have the newer file.
    p2 = tmp_path.joinpath("profile2")
    p2.mkdir()
    p2 = p2.joinpath("places.sqlite")
    print(f"\n{p2}")
    make_fake_places_file(p2)

    args = ["fbx.py", "--profile", str(p2.parent), "--places-file", str(p1)]
    opts = get_opts(args)
    assert str(p1) == str(
        opts.places_file
    ), "--places-file should override --profile"


def test_opt_default_output():
    args = ["fbx.py"]
    opts = get_opts(args)
    print(f"\n{opts}")
    assert isinstance(opts.output_file, Path)
    assert "Desktop" in str(opts.output_file)


def test_opt_output_name():
    args = ["fbx.py", "--output-name", "myname.txt"]
    opts = get_opts(args)
    print(f"\n{opts}")
    assert (
        opts.output_file.name == "myname.html"
    ), "File name suffix should always be '.html'."


def test_opt_md_output_names():
    args = ["fbx.py", "--output-name", "myname.txt", "--by-date", "--md"]
    opts = get_opts(args)
    print(f"\n{opts}")
    assert opts.md_file.name == "myname.md"
    assert opts.md_bydate.name == "myname-bydate.md"


def test_opt_output_folder(tmp_path):
    args = ["fbx.py", "--output-folder", str(tmp_path)]
    opts = get_opts(args)
    print(f"\n{opts}")
    assert str(opts.output_file.parent) == str(
        tmp_path
    ), "Output file should be in specified folder."


def test_html_output(setup_tmp_source_and_output, capsys):
    src_file, out_dir = setup_tmp_source_and_output
    args = [
        "fbx.py",
        "--places-file",
        str(src_file),
        "--output-folder",
        str(out_dir),
        "--output-name",
        "test-fbx2-output.html",
        "--by-date",
    ]
    result = main(args)
    captured = capsys.readouterr()
    assert result == 0
    assert "Done." in captured.out


def test_markdown_output(setup_tmp_source_and_output, capsys):
    src_file, out_dir = setup_tmp_source_and_output
    out_name = "test-fbx-output.md"
    out_md = out_dir / out_name
    args = [
        "fbx.py",
        "--places-file",
        str(src_file),
        "--output-folder",
        str(out_dir),
        "--output-name",
        out_name,
        "--md",
    ]
    result = main(args)
    captured = capsys.readouterr()
    assert result == 0
    assert "Done." in captured.out
    assert out_md.exists()


def test_db_output(setup_tmp_source_and_output, capsys):
    #  Maybe this test does too much, but it seems to make sense to chain
    #  these operations instead of fiddling with a bunch of extra setup just
    #  to make a test only test one thing. So says the impurist. :}~

    src_file, out_dir = setup_tmp_source_and_output

    #  Read a places.sqlite file and write to a sqlite database.
    args = [
        "fbx2.py",
        "--places-file",
        str(src_file),
        "--output-folder",
        str(out_dir),
        "--output-sqlite=test-fbx2-db-output.sqlite",
    ]
    result = main(args)
    captured = capsys.readouterr()
    assert result == 0
    assert "Done." in captured.out

    #  Read the same places.sqlite file and write to the same sqlite database.
    args = [
        "fbx2.py",
        "--places-file",
        str(src_file),
        "--output-folder",
        str(out_dir),
        "--output-sqlite=test-fbx2-db-output.sqlite",
    ]
    result = main(args)
    captured = capsys.readouterr()
    assert result == 1
    assert " already in " in captured.out, "Should not load duplicate data."

    #  Read the same places.sqlite file and write to the same sqlite database,
    #  but say it's from a different host (--host-name parameter).
    args = [
        "fbx2.py",
        "--places-file",
        str(src_file),
        "--output-folder",
        str(out_dir),
        "--output-sqlite=test-fbx2-db-output.sqlite",
        "--host-name=other_host",
    ]
    result = main(args)
    captured = capsys.readouterr()
    assert result == 0
    assert "Done." in captured.out

    #  Read the sqlite database and write HTML files.
    args = [
        "fbx2.py",
        "--output-folder",
        str(out_dir),
        f"--from-sqlite={out_dir}/test-fbx2-db-output.sqlite",
        "--output-name",
        "test-fbx2-output-from-db.html",
        "--by-date",
    ]
    result = main(args)
    captured = capsys.readouterr()
    assert result == 0
    assert "Done." in captured.out

    html_path = out_dir / "test-fbx2-output-from-db.html"
    assert html_path.exists()
    assert "other_host" in html_path.read_text()
