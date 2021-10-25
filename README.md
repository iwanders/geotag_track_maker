# Geotag track maker

Combines coordinates from multiple gpx tracks and xmp metadata files into a single track.

```
./geotag_track.py --xmp-shift=-7200 --gpx-interval 60 -o combined_track.gpx tracks/*.gpx photo_metadata/*.xmp
```

Export metadata from photos
---------------------------
```bash
mkdir metadata_export_dir
exiv2 ex -l metadata_export_dir -e X *.jpg
# or exiv2 ex -e X *.jpeg for just in current directory.
```
