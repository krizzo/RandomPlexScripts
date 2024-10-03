#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Upload/Updates plex poster images using fuzzy matching from a posters dir.

Required setup:
1) There should be a 'libraries' directory at the same level as this script.
2) Within the dir there should be a dir for each library in plex or
   as defined by the 'library_names' var in main()
   all lowercase and underscores '_' for spaces.
3) Posters should be in the format of 'MOVIE_TITLE (MOVIE_YEAR)' The closer
   it is to what plex names it the more accurate the matching will be.

Example dir/file structure
.
├── libraries
│   └── movies
│       ├── collections
│       │   └── Alien Complete Collection.png
│       └── posters
│           ├── Alien (1979).png
│           ├── Alien³ (1992).png
│           ├── Alien- Covenant (2017).png
│           ├── Alien Resurrection (1997).png
│           ├── Aliens (1986).png
│           └── Aliens vs Predator- Requiem (2007).png
└── plex_api_poster_update.py

Author: krizzo
Requires: plexapi, fuzzywuzzy
Example:
    python plex_api_poster_update.py

TODO:
1) Actually implement better logging than the archaic print statements
2) Allow for args/options to be passed such as dir or ratio matching
3) Possibly validate if poster needs updated rather than just uploading blindly
4) Extend to update collections or even create them
5) Allow for match testing of strings

Fuzzy fails
Plex Name,Poster Name,Notes
Star Wars: Episode VI - Return of the Jedi (1983),Return of the Jedi (1983), Lower than 78 ratio match strength
Star Wars: Episode V - The Empire Strikes Back (1980),The Empire Strikes Back (1980), Lower than 78 ratio match strength
'''

from plexapi.server import PlexServer, CONFIG
from os import listdir
from os.path import isfile, join
import re
from fuzzywuzzy import fuzz
from fuzzywuzzy import process


def write_library_list_file_from_plex(library_names=None, MyPlexServer=None):
    for library in library_names:
        lib_name = library.lower().replace(' ', '_')
        pmf = open(f"plex_{lib_name}_list.txt", 'w')
        for media in MyPlexServer.library.section(library).all():
            # Clean names of special characters
            # name = re.sub('\W+', ' ', media.title)
            # Add (year) to name
            name = '{} ({})'.format(media.title, media.year)
            pmf.write(name + '\n')
        pmf.close()


def get_posters_files_of_library(library=None):
    """
    Take a library directy name and return a list of all files in the library
    Expecting a dir structure as './libraries/<library_name_lowercase>/posters/'
    """
    posters_path = f"./libraries/{library.lower().replace(' ', '_')}/posters"
    try:
        return {f: join(posters_path, f) for f in listdir(posters_path) if isfile(join(posters_path, f))}
    except FileNotFoundError as e:
        print(f"!!! WARN  - Expected dir '{posters_path}' is missing for library '{library}'.")
        return None


def process_library_posters(library=None, posters_files=None, MyPlexServer=None, min_ratio_match=78):
    """
        78% appears to be a good value for updating a poster correctly matching it's name to the media name from plex.
        https://python-plexapi.readthedocs.io/en/latest/modules/mixins.html#plexapi.mixins.PosterMixin
    """
    ratio_val_min = 78 # Inclusive
    ratio_val_max = 100 # Exclusive
    precential_int = 25
    range_count = 0
    ratio_percentile = ratio_val_max - ((precential_int / 100) * (ratio_val_max - ratio_val_min))
    lowest_ratio = 100
    try:
        for media in MyPlexServer.library.section(library).all():
            name = '{} ({})'.format(media.title, media.year)
            if posters_files == None:
                continue
            poster_name = process.extractOne(name, posters_files.keys(), scorer=fuzz.token_sort_ratio)
            if poster_name != None:
                if poster_name[1] >= min_ratio_match:
                    print(f"--- DEBUG - Ratio {poster_name[1]} matched for poster key '{poster_name[0]}' with file path value of '{posters_files[poster_name[0]]}'")
                    print(f"--- INFO  - Poster found above min ratio of {min_ratio_match} updating now...")
                    media.uploadPoster(filepath=posters_files[poster_name[0]])
                    if poster_name[1] in range(ratio_val_min, (ratio_val_max + 1)):
                        range_count += 1
                        if poster_name[1] < lowest_ratio: lowest_ratio = poster_name[1]
                        if poster_name[1] < ratio_percentile: print(f"--- DEBUG - {precential_int}th percentile in range poster: '{poster_name}' - media formatted name:   '{name}'")
        print(f"--- DEBUG - {range_count} identified posters for {library} between {ratio_val_min} - {ratio_val_max} with lowest ratio of {lowest_ratio}")
    except NoneType as e:
        print(f"!!! WARN  - No match found.\n{e}")
    except Exception as e:
        print(f"!!! ERROR - Exception found.\n{e}")


def main():
    plex_url = CONFIG.data['auth'].get('server_baseurl')
    plex_token = CONFIG.data['auth'].get('server_token')
    MyPlexServer = PlexServer(plex_url, plex_token)

    # TODO: Allow a poster dir to be passed with LIBRARY_NAME/POSERS.FILES and generate lib list from the dirs.
    library_names = ['Movies', 'TV Shows'] # These are the default libraries

    for library in library_names:
        poster_files = get_posters_files_of_library(library=library)
        process_library_posters(library, poster_files, MyPlexServer)


if __name__ == "__main__":
    main()
