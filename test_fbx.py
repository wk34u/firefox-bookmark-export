import sqlite3

from pathlib import Path

from fbx import get_opts


def make_fake_places_file(file_path: Path):
    assert not file_path.exists(), "Should be a new file."

    con = sqlite3.connect(str(file_path))
    cur = con.cursor()
    cur.execute("CREATE TABLE moz_places (url TEXT);")
    cur.execute("CREATE TABLE moz_bookmarks (title TEXT, parent TEXT);")
    con.commit()
    con.close()


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
    assert str(p1) == str(opts.places_file), (
        "--places-file should override --profile"
    )


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
    assert opts.output_file.name == "myname.html", (
        "File name suffix should always be '.html'."
    )


def test_opt_output_folder(tmp_path):
    args = ["fbx.py", "--output-folder", str(tmp_path)]
    opts = get_opts(args)
    print(f"\n{opts}")
    assert str(opts.output_file.parent) == str(tmp_path), (
        "Output file should be in specified folder."
    )
