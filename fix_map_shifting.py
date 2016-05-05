#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Majormode.  All rights reserved.
#
# This software is the confidential and proprietary information of
# Majormode or one of its subsidiaries.  You shall not disclose this
# confidential information and shall use it only in accordance with
# the terms of the license agreement or other applicable agreement you
# entered into with Majormode.
#
# MAJORMODE MAKES NO REPRESENTATIONS OR WARRANTIES ABOUT THE
# SUITABILITY OF THE SOFTWARE, EITHER EXPRESS OR IMPLIED, INCLUDING
# BUT NOT LIMITED TO THE IMPLIED WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, OR NON-INFRINGEMENT.  MAJORMODE
# SHALL NOT BE LIABLE FOR ANY LOSSES OR DAMAGES SUFFERED BY LICENSEE
# AS A RESULT OF USING, MODIFYING OR DISTRIBUTING THIS SOFTWARE OR ITS
# DERIVATIVES.
#
# @version $Revision$

from majormode.perseus.model.geolocation import GeoPoint
from xml.dom import minidom

import StringIO
import argparse
import codecs
import contextlib
import enum
import locale
import os
import sys
import zipfile

# Python determines the encoding of stdout and stderr based on the
# value of the ``LC_CTYPE`` variable, but only if the stdout is a tty.
# So if you just output to the terminal, ``LC_CTYPE`` (or ``LC_ALL``)
# define the encoding.  However, when the output is piped to a file or
# to a different process, the encoding is not defined, and defaults to
# 7-bit ASCII, which raise the following exception when outputting
# unicode characters:
#
#   ``UnicodeEncodeError: 'ascii' codec can't encode character u'\x..' in position 18: ordinal not in range(128).``
#
# @note: using the environment variable ``PYTHONIOENCODING`` is
#     another solution, however it requires the user to prefix the
#     command line with ``PYTHONIOENCODING=utf-8``, which is more
#     cumbersome.
# sys.stdout = codecs.getwriter(sys.stdout.encoding if sys.stdout.isatty() \
#         else locale.getpreferredencoding())(sys.stdout)


class Place(object):
    GeometryType = enum.Enum(
        'line',
        'point',
        'polygon',
    )

    def __init__(self, name, type, geometry):
        self.name = name
        self.type = type
        self.geometry = geometry

    @property
    def geometry_type(self):
        return self.type

    def calculate_shift(self, other):
        if self.name != other.name or self.type != other.type:
            return False

        if self.type == Place.GeometryType.point:
            return (round(self.geometry.longitude - other.geometry.longitude, 8),
                    round(self.geometry.latitude - other.geometry.latitude, 8))

        else:
            shift = set([ (round(geopoint.longitude - other.geometry[i].longitude, 5),
                           round(geopoint.latitude - other.geometry[i].latitude, 5))
                    for (i, geopoint) in enumerate(self.geometry)
                        if (abs(geopoint.longitude - other.geometry[i].longitude > 0.00001)) or
                            abs((geopoint.latitude - other.geometry[i].latitude > 0.00001)) ])

            return len(shift) == 1 and list(shift)[0]


def find_map_shifting(original_document, modified_document):
    found = False

    for original_element in original_elements:
        for modified_element in modified_elements:
            _shift_ = original_element.calculate_shift(modified_element)
            if _shift_ and _shift_ != (0.0, 0.0):
                if found:
                    print '[ERROR] More than one geometry has been modified!'
                    return None
                else:
                    shift = _shift_
                    print '[INFO] Place %s has been moved %s from its initial position' % (original_element.name, shift)
                    found = True

    if not found:
        print '[ERROR] No change has been noticed!'

    else:
        return shift


def open_kml_file(file_path_name):
    """
    Open the specified KML or KMZ file and return an XML document.

    @param file_path_name: absolute path and name of a KML or KMZ file.

    @return: an XML document.
    """
    # If the KML file is distributed in a KMZ file, which is a zipped KML
    # files with a .kmz extension, create an in-memory file-like object
    # and uncompress the inner KML file in it.
    is_file_zipped = file_path_name.lower().endswith('kmz')
    if is_file_zipped:
        zip_file = zipfile.ZipFile(file_path_name)

        zip_list_names = zip_file.namelist()
        if len(zip_list_names) == 0:
            raise ValueError('The specified file %s does not contain any entry' % file_path_name)
        if len(zip_list_names) > 1:
            raise ValueError('The specified file %s contains more than 1 entry' % file_path_name)

        file_name = zip_list_names[0]
        if not file_name.lower().endswith('.kml'):
            raise ValueError('The entry %s in the file %s does not have the extension .kml' % (file_name, file_path_name))

        in_memory_file = StringIO.StringIO()
        in_memory_file.writelines(zip_file.read(file_name))
        in_memory_file.seek(0)

    return minidom.parse(in_memory_file if is_file_zipped else file_path_name)


def parse_kml_document(document):
    folders = document.getElementsByTagName('Folder')
    if len(folders) == 0:
        elements = parse_kml_elements(document)
    else:
        elements = []

        for element in folders:
            children = dict([(child.nodeName, child) for child in element.childNodes])
            folder_name = children.get('name').childNodes[0].nodeValue.strip()
            print '[INFO] Analyzing folder %s' % folder_name

            elements += parse_kml_elements(element)

    return elements


def parse_kml_elements(root_element):
    places = list()

    for element in root_element.getElementsByTagName('Placemark'):
        children = dict([(child.nodeName, child) for child in element.childNodes])

        # Retrive the name of the place.
        name_element = children.get('name')
        place_name = name_element.childNodes[0].nodeValue.strip() if len(name_element.childNodes) > 0 else None

        # Retrieve the geometry of this place, either a simple point, either a
        # polygon.
        if children.get('Point'):
            (longitude, latitude, altitude) = children['Point'].getElementsByTagName('coordinates')[0].childNodes[0].nodeValue.split(',')
            place = Place(place_name, Place.GeometryType.point,
                    GeoPoint(round(longitude, 8), round(latitude, 8), altitude=round(altitude, 8)))

        elif children.get('Polygon'):
            place_geometry = [ GeoPoint(round(float(lon), 8), round(float(lat), 8), round(float(alt), 8)) for (lon, lat, alt) in
                    [ coordinates.split(',') for coordinates in
                            children['Polygon'].getElementsByTagName('coordinates')[0].childNodes[0].nodeValue.split(' ') ]]
            place = Place(place_name, Place.GeometryType.polygon, place_geometry)

        elif children.get('LineString'):
            place_geometry = [ GeoPoint(round(float(lon), 8), round(float(lat), 8), round(float(alt), 8)) for (lon, lat, alt) in
                    [ coordinates.split(',') for coordinates in
                            children['LineString'].getElementsByTagName('coordinates')[0].childNodes[0].nodeValue.split(' ') ]]
            place = Place(place_name, Place.GeometryType.line, place_geometry)

        elif children.get('styleUrl'):
            pass # Ignore Style URL?

        else:
            print '[WARNING] Ignore place "%s" with unsupported geometry.' % place_name
            print children.items()
            continue

        places.append(place)

    return places


def shift_kml_document(document, (shift_x, shift_y)):
    for element in document.getElementsByTagName('Placemark'):
        children = dict([ (child.nodeName, child) for child in element.childNodes ])

        if children.get('Point'):
            (longitude, latitude, altitude) = \
                children['Point'].getElementsByTagName('coordinates')[0].childNodes[0].nodeValue.split(',')

            children['Point'].getElementsByTagName('coordinates')[0].childNodes[0].nodeValue = '%s,%s,%s' % \
                    (round(float(longitude) - shift_x, 8), round(float(latitude) - shift_y, 8), altitude)

        elif children.get('Polygon'):
            geometry = [ (float(longitude), float(latitude), float(altitude))
                    for (longitude, latitude, altitude) in [ coordinates.split(',')
                            for coordinates in children['Polygon'].getElementsByTagName('coordinates')[0].childNodes[0].nodeValue.split(' ') ]]

            children['Polygon'].getElementsByTagName('coordinates')[0].firstChild.replaceWholeText(
                    ' '.join([ '%s,%s,%s' % (round(longitude - shift_x, 8), round(latitude - shift_y, 8), altitude)
                            for (longitude, latitude, altitude) in geometry ]))

        elif children.get('LineString'):
            geometry = [ (float(longitude), float(latitude), float(altitude))
                    for (longitude, latitude, altitude) in [ coordinates.split(',')
                            for coordinates in children['LineString'].getElementsByTagName('coordinates')[0].childNodes[0].nodeValue.split(' ') ]]

            children['LineString'].getElementsByTagName('coordinates')[0].firstChild.nodeValue = \
                    ' '.join([ '%s,%s,%s' % (round(longitude - shift_x, 8), round(latitude - shift_y, 8), altitude)
                            for (longitude, latitude, altitude) in geometry ])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Heritage Observatory KML Shift Correction')
    parser.add_argument('-i1', '--original-file', dest='original_file_path_name', metavar='filename', required=True,
            help='specify the absolute path and name of the KML document where geometries have been shifted around')
    parser.add_argument('-i2', '--copy-file', dest='modified_file_path_name', metavar='filename', required=True,
            help = 'specify the absolute path and name of the modified KML document in which one POINT has been fixed')
    parser.add_argument('-o', '--output-file', dest='output_file_path_name', metavar='filename', required=False,
            help='specify the absolute path and name of the fixed KML document to generate')
    parser.add_argument('--verbose', required=False, action='store_true', default=False, help='print verbose messages, including warnings.')
    arguments = parser.parse_args()

    original_xml_document = open_kml_file(arguments.original_file_path_name)
    modified_xml_document = open_kml_file(arguments.modified_file_path_name)

    original_elements = parse_kml_document(original_xml_document)
    modified_elements = parse_kml_document(modified_xml_document)

    shift = find_map_shifting(original_elements, modified_elements)
    (shift_x, shift_y) = shift

    shift_kml_document(original_xml_document, shift)

    output_file_path_name = arguments.output_file_path_name if arguments.output_file_path_name else \
            os.path.join(os.path.dirname(arguments.original_file_path_name),
                         'fixed_%s' % os.path.basename(arguments.original_file_path_name))

    with contextlib.closing(codecs.open(output_file_path_name, 'wt', encoding='utf-8')) as file_handle:
        original_xml_document.writexml(file_handle)
