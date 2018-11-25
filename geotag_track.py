#!/usr/bin/env python3

# The MIT License (MIT)
# Copyright (c) 2018 Ivor Wanders
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import argparse
import datetime
import sys
import os
from collections import namedtuple
import dateutil.parser

# Timestamp shall be in datetime.datetime UTC.
# latitude and longitude shall be a floating point number representing degrees.
# altitude is float in meters, negative is below sea level.
Position = namedtuple("Position", ["timestamp", "latitude", "longitude", "altitude"]);

# Assume all timezones are UTC / gps time.


import gpxpy
import gpxpy.gpx
def gpx_to_coordinates(fname, args):
    positions = []
    with open(fname, "r") as f:
        gpx = gpxpy.parse(f.read())

    flat = []
    last_point_time = 0.0
    # Flatten the track, reading all points from tracks, waypoints and routes.
    for track in gpx.tracks:
        for segment in track.segments:
            for i, point in enumerate(segment.points):
                if (i == len(segment.points) - 1):
                    flat.append(point)
                    break # ensure last point is added
                if (point.time.timestamp() - last_point_time >= args.gpx_interval):
                    last_point_time = point.time.timestamp()
                    flat.append(point)
                    
        
    for waypoint in gpx.waypoints:
        flat.append(waypoint)

    for route in gpx.routes:
        for point in route.points:
            flat.append(point)

    for point in flat:
        positions.append(Position(timestamp=point.time, latitude=point.latitude, longitude=point.longitude, altitude=point.elevation))
    return positions

import libxmp
def xmp_to_coordinates(fname):
    with open(fname, "r") as f:
        xmp = libxmp.XMPMeta()
        xmp.parse_from_str(f.read())

    def coordinate_fixer(coord_str):
        # https://gis.stackexchange.com/questions/136925/#comment265294_136928
        # dd=x0+x1/60.+x2/3600
        # https://sno.phy.queensu.ca/~phil/exiftool/TagNames/GPS.html
        # positive for north latitudes or negative for south, or a string ending in N or S)
        # positive for east longitudes or negative for west, or a string ending in E or W)
        scalar = 1.0
        if (coord_str.lower().endswith("w") or coord_str.lower().endswith("s")):
            scalar = -1
            coord_str = coord_str[:-1]
        if (coord_str.lower()[-1] in {"n", "e"}):
            coord_str = coord_str[:-1]
        components = [float(x) for x in coord_str.split(",")]
        return scalar * sum([components[i]/(60**i) for i in range(0, len(components))])

    def altitude_fixer(alt_rat, alt_ref):
        scalar = 1.0
        if (int(alt_ref) == 1):
            scalar = -1
        a, b = alt_rat.split("/")
        return scalar * (float(a) / float(b))

    try:
        lat = coordinate_fixer(xmp.get_property(libxmp.consts.XMP_NS_EXIF, 'GPSLatitude'))
        long = coordinate_fixer(xmp.get_property(libxmp.consts.XMP_NS_EXIF, 'GPSLongitude'))

        alt_rat = xmp.get_property(libxmp.consts.XMP_NS_EXIF, 'GPSAltitude')
        alt_ref = xmp.get_property(libxmp.consts.XMP_NS_EXIF, 'GPSAltitudeRef')
        alt = altitude_fixer(alt_rat, alt_ref)
        gpstime = dateutil.parser.parse(xmp.get_property(libxmp.consts.XMP_NS_EXIF, 'GPSTimeStamp'))    
        return [Position(timestamp=gpstime, latitude=lat, longitude=long, altitude=alt)]
    except libxmp.XMPError as e:
        sys.stderr.write("Could not find necessary data in {}\n".format(fname))
        return []

def traverse(inputs):
    found_files = set()
    for input in inputs:
        if (os.path.isfile(input)):
            found_files.add(input)
            continue
        for root, dirs, files in os.walk(input):
            for f in files:
                entry = os.path.join(root, f)
                if (entry.endswith(".xmp") or entry.endswith(".gpx")):
                    found_files.add(entry)
    return found_files

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Combine geotagged data into a single useful track.')
    parser.add_argument('input_folders_files', metavar='N', type=str, nargs='+',help='Path(s) to file(s) or directories.')
    parser.add_argument('--gpx-interval', nargs='?', type=float, help="Minimum interval between points in tracks [s].", default=1.0)
    parser.add_argument('-o', '--output', default=None, help="Output file name.")

    args = parser.parse_args()

    files = traverse(args.input_folders_files)
    sys.stderr.write("Found {} files.\n".format(len(files)))

    positions = []
    for f in files:
        if f.endswith(".gpx"):
            positions.extend(gpx_to_coordinates(f, args))
        if f.endswith(".xmp"):
            positions.extend(xmp_to_coordinates(f))

    sys.stderr.write("Found {} coordinates.\n".format(len(positions)))
    positions.sort(key=lambda x: x.timestamp)


    gpx = gpxpy.gpx.GPX()

    # create track in the gpx file.
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(gpx_track)

    # create segment in the track.
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)

    # Create points in the gpx segment.
    for p in positions:
        gpxpoint = gpxpy.gpx.GPXTrackPoint(latitude=p.latitude, longitude=p.longitude, elevation=p.altitude, time=p.timestamp);
        gpx_segment.points.append(gpxpoint)

    if (args.output):
        with open(args.output, "w") as f:
            f.write(gpx.to_xml())
    else:
        sys.stdout.write(gpx.to_xml())