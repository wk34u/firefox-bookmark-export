# firefox-bookmark-export

**fbx.py** is a command-line utility that reads the Firefox *places.sqlite* database and writes a HTML file listing the saved bookmarks.

This program borrows from the earlier [firefox-places](https://github.com/wmelvin/firefox-places) utility.

If no command-line arguments are given, the common location for Firefox profiles is searched and the most recently modified `places.sqlite` file is used. The default output file is named `Firefox-bookmarks-*date_time*.html` and is written to the user's `Desktop` folder.


```
usage: fbx.py [-h] [--profile PROFILE] [--places-file PLACES_FILE]
              [--output-name OUTPUT_FILE] [--output-folder OUTPUT_FOLDER]

Exports Firefox bookmarks to a single HTML file.

optional arguments:
  -h, --help            show this help message and exit
  --profile PROFILE     Path to the Firefox profile folder.
  --places-file PLACES_FILE
                        Path to a specific version of the 'places.sqlite'
                        file. Overrides the '--profile' options.
  --output-name OUTPUT_FILE
                        Name of the output HTML file.
  --output-folder OUTPUT_FOLDER
                        Name of the folder in which to create the output HTML
                        file.
```