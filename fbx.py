#!/usr/bin/env python3

import argparse
import sqlite3
import sys

from collections import namedtuple
from datetime import datetime
from pathlib import Path
from textwrap import dedent, indent

# from rich import print


app_name = "fbx.py"

run_dt = datetime.now()

AppOptions = namedtuple("AppOptions", "places_file, output_file")

Bookmark = namedtuple("Bookmark", "title, url, parent_path")


def get_args(argv):
    ap = argparse.ArgumentParser(
        description="Exports Firefox bookmarks to a single HTML file."
    )

    ap.add_argument(
        "--profile",
        dest="profile",
        action="store",
        help="Path to the Firefox profile folder.",
    )

    ap.add_argument(
        "--places-file",
        dest="places_file",
        action="store",
        help="Path to a specific version of the 'places.sqlite' file. "
        "Overrides the '--profile' options.",
    )

    ap.add_argument(
        "--output-name",
        dest="output_file",
        action="store",
        help="Name of the output HTML file.",
    )

    ap.add_argument(
        "--output-folder",
        dest="output_folder",
        action="store",
        help="Name of the folder in which to create the output HTML file.",
    )

    return ap.parse_args(argv[1:])


def get_opts(argv):
    args = get_args(argv)

    places_file = None

    if args.places_file:
        places_file = Path(args.places_file)
    else:
        if args.profile:
            p = Path(args.profile)
        else:
            p = Path("~/.mozilla/firefox").expanduser().resolve()

        if not p.exists():
            sys.stderr.write(f"\nERROR: Cannot find folder '{p}'\n")
            sys.exit(1)

        files = list(p.glob("**/places.sqlite"))
        files.sort(key=lambda x: x.stat().st_mtime)
        places_file = files[-1]

    if places_file:
        if not places_file.exists():
            sys.stderr.write(f"\nERROR: Cannot find folder '{p}'\n")
            sys.exit(1)
    else:
        sys.stderr.write("\nERROR: No profile or file name specified.'\n")
        sys.exit(1)

    out_dir = None
    output_file = None

    if args.output_folder:
        out_dir = Path(args.output_folder).expanduser().resolve()
    else:
        out_dir = Path.home().joinpath("Desktop")

    if args.output_file:
        out_file = Path(args.output_file)
        out_file = Path(out_file.stem).with_suffix(".html")
    else:
        out_file = Path(
            f"Firefox-bookmarks-{run_dt.strftime('%y%m%d_%H%M%S')}.html"
        )

    output_file = out_dir.joinpath(out_file.name)

    return AppOptions(places_file, output_file)


def html_style():
    s = """
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            padding: 1rem 4rem;
        }
        a:link, a:visited {
            color: #00248F;
            text-decoration: none;
        }
        :link:hover,:visited:hover {
            color: #B32400;
            text-decoration: underline;
        }
        .bookmark-path { color: gray; }
        .bookmark-title { color: black; }
        #asof {
            color: darkgray;
            font-size: 12px;
        }
        #footer {
            border-top: 1px solid black;
            font-size: x-small;
            margin-top: 2rem;
        }
    """
    return s.lstrip("\n").rstrip()


def html_head(title):
    return (
        dedent(
            """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta name="generator" content="{0}">
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
            <title>{1}</title>
            <style>
        {2}
            </style>
        </head>
        <body>
        <h1>{1}</h1>
        <ul>
        """
        )
        .format(app_name, title, html_style())
        .strip("\n")
    )


def html_tail():
    return dedent(
        """
        </ul>
        <div id="footer">
          Created by {0} at {1}.
        </div>
        </body>
        </html>
        """
    ).format(app_name, run_dt.strftime("%Y-%m-%d %H:%M"))


def get_parent_path(con, id):
    cur = con.cursor()

    depth = 0
    parent_id = id
    parent_path = "/"
    while 0 < parent_id:
        #  It appears that the root always has id=0. If that is not the case
        #  this max-depth check (99 seems like a good arbitrary value) will
        #  prevent an infinate loop.
        depth += 1
        assert depth < 99

        sql = (
            "SELECT parent, title FROM moz_bookmarks WHERE id = {0}"
        ).format(parent_id)

        cur.execute(sql)
        rows = cur.fetchall()
        assert len(rows) == 1

        parent_id = int(rows[0][0])
        if 0 < parent_id:
            title = str(rows[0][1])
            parent_path = f"/{title}{parent_path}"

    return parent_path


def get_bookmarks(con):
    bookmarks = []

    sql = dedent(
        """
        SELECT
            a.title,
            b.url,
            a.parent
        FROM
            moz_bookmarks a
        JOIN moz_places b
        ON b.id = a.fk
        """
    )
    cur = con.cursor()

    try:
        cur.execute(sql)
    except Exception as ex:
        if str(ex) == "database is locked":
            cur.close()
            con.close()
            sys.stderr.write(
                "\nERROR: Database is locked. "
                "Please close Firefox and try again.\n"
            )
            sys.exit(1)
        else:
            raise ex

    rows = cur.fetchall()

    for row in rows:
        url = str(row[1])

        if not url.startswith("http"):
            print(f"SKIP NON-HTTP URL: '{url}'")
            continue

        title = str(row[0])
        parent_id = int(row[2])

        if title is None:
            title = f"({url})"

        bookmarks.append(Bookmark(title, url, get_parent_path(con, parent_id)))

    bookmarks.sort(key=lambda item: item.parent_path + item.title)

    return bookmarks


def limited(value):
    s = str(value)
    if len(s) <= 180:
        return s
    else:
        return s[:177] + "..."


def htm_txt(text: str) -> str:
    s = text.replace("&", "&amp;")
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    return s


def htm_url(url: str) -> str:
    return url.replace("&", "%26")


def write_bookmarks_html(opts: AppOptions, con: sqlite3.Connection):
    file_name = str(opts.output_file)

    bmks = get_bookmarks(con)

    print(f"Writing '{file_name}'")
    with open(file_name, "w") as f:

        f.write(html_head("Bookmarks"))

        dt = run_dt.strftime("%Y-%m-%d %H:%M")
        f.write(f'<p><span id="asof">(as of {dt})</span></p>\n')

        for bmk in bmks:
            title = limited(ascii(bmk.title))
            s = dedent(
                """
                    <li>
                        <p><span class="bookmark-path">{0}</span><br />
                        <span class="bookmark-title">{1}</span><br />
                        <a target="_blank" href=
                        "{2}">
                        {2}</a></p>
                    </li>
                    """
            ).format(
                htm_txt(bmk.parent_path), htm_txt(title), htm_url(bmk.url)
            )
            f.write(indent(s, " " * 8))
        f.write(html_tail())


def main(argv):
    opts = get_opts(argv)
    print(f"Reading {opts.places_file}")
    con = sqlite3.connect(opts.places_file, timeout=1.0)
    write_bookmarks_html(opts, con)
    con.close()
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
