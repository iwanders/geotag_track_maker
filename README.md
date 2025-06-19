# Geotag track maker

Combines coordinates from multiple gpx tracks and xmp metadata files into a single track. This track
can then be used to geotag photos made with a camera or any device that doesn't have gps capabilities.

```
./geotag_track.py --xmp-shift=-7200 --gpx-interval 60 -o combined_track.gpx tracks/*.gpx photo_metadata/*.xmp
```

## Export metadata from photos

Use this to extract metadata from iOS files, since they always have a location:

```bash
mkdir metadata_export_dir
exiv2 ex -l metadata_export_dir -e X *.jpg
# or exiv2 ex -e X *.jpeg for just in current directory.
```

## License
[MIT][./license.txt].
