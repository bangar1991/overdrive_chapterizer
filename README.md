Audiobooks downloaded from Overdrive in MP3 format have ID3 tags that describe chapter information. 
However, those tags are usable only in Overdrive and Libby media players, and aren't supported in
general media players. It is more useful to have chapter information as 
[ID3v2 chapter tags](http://id3.org/id3v2-chapters-1.0) instead. This utility helps you to transfer
Overdrive chapters to ID3v2 chapter tags instead.

This utility allows you to:
- Display existing Overdrive chapters
- Display existing ID3v2 
- Modify existing ID3v2 chapters by title, start time or end time
- Insert new chapters
- Remove existing chapters

## Requirements
- `eyed3`
- `pyqt5`

## Usage
```
python3 chapterize.py
```
