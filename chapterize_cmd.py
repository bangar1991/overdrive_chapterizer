from pathlib import Path
from typing import List
from argparse import ArgumentParser
import xml.etree.ElementTree as ET
import sys

from recordclass import recordclass
import eyed3
from eyed3.mp3 import Mp3AudioFile
import tabulate

tabulate.PRESERVE_WHITESPACE = True

Chap = recordclass('Chap', 'title start end')


def _time_to_milliseconds(t: str) -> int:
    """
    Converts hh:mm:ss.zzz into integer milliseconds
    :param t: a string formatted as [[hh:]mm:]ss[.zzz]
    :return: number of milliseconds
    """
    time_comp = t.strip().split(':')
    secs = 0.0
    if len(time_comp) > 0:
        secs = float(time_comp[-1])
        mins = 0
        if len(time_comp) > 1:
            mins = int(time_comp[-2])
            hours = 0
            if len(time_comp) > 2:
               hours = int(time_comp[-3])
    seconds = (hours * 3600) + (mins * 60) + secs
    return int(seconds * 1000)


def _parse_markers(markers) -> List[Chap]:
    """
    Parses markers into Chap items
    :param markers: a user frame called 'Overdrive MediaMarkers' containing XML formatted markers
    :return: a list of Chap items
    """
    titles = []
    starts = []

    print("Parsing Overdrive chapters: ", end='')

    root = ET.fromstring(markers.text)
    for marker in root.iter('Marker'):
        name = marker.find('Name')
        time = marker.find('Time')
        if name is not None and time is not None:
            titles.append(name.text)
            starts.append(_time_to_milliseconds(time.text))

    if len(starts) > 0:
        ends = starts[1:] + [None]
    else:
        ends = [None]

    chapters = []

    for title, start, end in zip(titles, starts, ends):
        chapters.append(Chap(title=title, start=start, end=end))

    print("{} chapters parsed.".format(len(chapters)))

    return chapters


def _load_markers(mp3: Mp3AudioFile):
    """
    Returns 'Overdrive MediaMarkers' user frame (containing markers) from the loaded mp3 file
    :param mp3: the loaded mp3 file
    :return: 'Overdrive MediaMarkers' user frame if found, else None
    """
    print("Looking for Overdrive chapters: ", end='')
    user_frames = mp3.tag.user_text_frames
    if 'OverDrive MediaMarkers' in user_frames:
        markers = user_frames.get('OverDrive MediaMarkers')
        print("Succeeded.")
        return markers
    print("Failed.")
    return None


def _find_mp3_files(dir: str) -> List[Path]:
    """
    Provides a list of paths to mp3 files in a given directory
    :param dir: A directory
    :return: List of mp3 file paths
    """
    p = Path(dir)
    print("Finding mp3 files: ", end='')
    mp3_files = list(p.glob('*.mp3'))

    if len(mp3_files) == 0:
        print("Failed.")
    else:
        print("{} files found.".format(len(mp3_files)))

    return mp3_files


def _has_chapter_metadata(mp3: Mp3AudioFile) -> bool:
    """
    Returns True if mp3 file has chapter metadata otherwise False
    :param mp3: loaded mp3 file
    :return: True if mp3 file has chapter metadata otherwise False
    """
    for _ in mp3.tag.table_of_contents:
        return True

    for _ in mp3.tag.chapters:
        return True

    return False


def _remove_existing_chapter_metadata(mp3: Mp3AudioFile) -> None:
    """
    Removes existing chapter tags from the loaded mp3 file if present.
    Note that this does not save the modified tags.
    :param mp3: the loaded mp3 file
    """
    toc_eids = [toc.element_id for toc in mp3.tag.table_of_contents]
    chap_eids = [chap.element_id for chap in mp3.tag.chapters]

    for toc_eid in toc_eids:
        mp3.tag.table_of_contents.remove(toc_eid)

    for chap_eid in chap_eids:
        mp3.tag.chapters.remove(chap_eid)


def _load_mp3_file(mp3_file: str) -> Mp3AudioFile:
    """
    Load an mp3 file from a path
    :param mp3_file: path to mp3 file
    :return: loaded mp3 audio file if success, else None
    """
    print("Reading tags in {}: ".format(mp3_file), end='')

    mp3 = None
    try:
        mp3 = eyed3.load(mp3_file)
        if mp3 is None:
            print("Failed.")
        print("Succeeded.")
    except IOError:
        print("Failed.")
    return mp3


def _abort():
    print("Aborting.")
    sys.exit(0)


def _write_chapters(mp3: Mp3AudioFile, chapters: List[Chap]) -> None:
    if len(chapters) == 0:
        return

    toc = mp3.tag.table_of_contents.set(b'toc', toplevel=True, description=u'Table of Contents')

    for index, chapter in zip(range(1, len(chapters) + 1), chapters):
        ch = mp3.tag.chapters.set('ch{}'.format(index).encode('ascii'), (chapter.start, chapter.end))
        ch.title = chapter.title

        toc.child_ids.append(ch.element_id)
        print("Added chapter: {}".format(chapter.title))


def _parse_selection(selection: str):
    selected = []

    if selection.strip() == '':
        return selected

    for s in selection.split(','):
        try:
            numbers = [int(n.strip()) for n in s.strip().split('-')]
            if len(numbers) == 1:
                selected.append(numbers[0])
            elif len(numbers) == 2:
                selected.extend(list(range(min(numbers), max(numbers) + 1)))
            else:
                return None
        except ValueError:
            return None
    return list(sorted(set(selected)))


def _print_chapters(chapters: List[Chap], index=False, title=True, start=False, end=False) -> None:
    data = [[]]
    if index:
        data[-1].append("Idx")
    if title:
        data[-1].append("Title")
    if start:
        data[-1].append("Start")
    if end:
        data[-1].append("End")

    for idx, chap in zip(range(1, len(chapters) + 1), chapters):
         data.append([])
         if index:
             data[-1].append(idx)
         if title:
             data[-1].append(chap.title)
         if start:
             data[-1].append(chap.start)
         if end:
             data[-1].append(chap.end)

    print(tabulate.tabulate(data, headers="firstrow"))


def _select_chapters(chapters: List[Chap]):
    all_selected = []
    if len(chapters) == 0:
        return all_selected

    while True:
        _print_chapters(chapters, index=True, title=True)
        print()

        response = input('Select chapters to include: ')
        selection = _parse_selection(response)

        if selection is not None:
            selected_chapters = [chapters[i - 1] for i in selection if 1 <= i <= len(chapters)]

            if len(selected_chapters) > 0:
                if len(selected_chapters) < len(chapters):
                    # Create modified timestamps to account for the missing chapters
                    for sc1, sc2 in zip(selected_chapters,
                                        selected_chapters[1:] + [None] if len(selected_chapters) >= 2 else [None]):
                        all_selected.append(Chap(title=sc1.title, start=sc1.start,
                                                 end=sc2.start if sc2 is not None else chapters[-1].end))
                else:
                    # No chapter omitted, so no timestamp modification needed
                    all_selected = selected_chapters

            break
        else:
            print("Please enter a valid selection.")
            print("A valid selection consists of comma delimited integers or integer ranges. Example: 1-3, 5, 4")

    if len(selection) > 0:
        print("Selected chapters: ", end='\n\n')
        _print_chapters(all_selected, index=True, title=True, start=True, end=True)
        print()

    return all_selected


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.description = "Adds ID3v2 chapter tags to mp3 audiobook files downloaded from Overdrive"
    parser.add_argument('path', help='Path to audiobook directory')
    parser.add_argument('-o', '--overwrite', action='store_const', const=True, default=False,
                        help='Overwrite existing chapter information. Without this flag, mp3 files with '
                             'existing chapter information will be ignored')
    parser.add_argument('-s', '--select', action='store_const', const=True, default=False,
                        help='In select mode, user will be asked to select chapters for each mp3 file')

    args = parser.parse_args()

    mp3_files = _find_mp3_files(args.path)

    if len(mp3_files) == 0:
        _abort()

    for mp3_file in mp3_files:
        mp3 = _load_mp3_file(mp3_file)

        if mp3 is None:
            _abort()

        markers = _load_markers(mp3)

        if markers is None:
            _abort()

        chapters = _parse_markers(markers)

        if len(chapters) == 0:
            print("Skipping.")
            continue

        mp3_duration = int(mp3.info.time_secs * 1000)  # Duration of audio file in milliseconds
        chapters[-1].end = mp3_duration

        if _has_chapter_metadata(mp3):
            print("Existing chapter information found.", end='')

            if args.overwrite:
                print(" Overwriting.", end='\n\n')
                _remove_existing_chapter_metadata(mp3)
                try:
                    selected = _select_chapters(chapters) if args.select else chapters
                    _write_chapters(mp3, selected)
                except KeyboardInterrupt:
                    sys.exit(0)
                except EOFError:
                    sys.exit(0)

                print()
            else:
                print(" Ignoring.", end='\n\n')
                continue
        else:
            try:
                selected = _select_chapters(chapters) if args.select else chapters
                _write_chapters(mp3, selected)
            except KeyboardInterrupt:
                sys.exit(0)
            except EOFError:
                sys.exit(0)

        print("Saving tags: ", end='')
        mp3.tag.save()
        print("Succeeded.", end='\n\n')
