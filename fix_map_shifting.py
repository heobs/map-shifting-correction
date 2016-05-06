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
import os
import zipfile

# Define the KML geometries currently supported by this script.
SUPPORTED_KML_GEOMETRIES = [ 'Point', 'Polygon', 'LineString' ]


class Place(object):
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

        if self.type == 'Point':
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
    """
    Return the geographical shift of one geometry element of the modified
    document compared to the location of this element in the original
    document.


    @param original_document: a KML document.

    @param modified_document: a copy of the KML document where the
        location of one geometry has been manually fixed.


    @return: a tuple ``(longitude, latitude)`` corresponding to the
        geographical shift of the particular element found.
    """
    shift = None
    for original_element in original_elements:
        for modified_element in modified_elements:
            _shift_ = original_element.calculate_shift(modified_element)
            if _shift_ and _shift_ != (0.0, 0.0):
                assert not shift, 'More than one geometry has been modified!'
                shift = _shift_

    assert shift, 'No change has been noticed!'

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

        # Retrieve the geometry of this place.
        geometry_type = [_ for _ in SUPPORTED_KML_GEOMETRIES if children.get(_)]
        if geometry_type:
            geometry_type = geometry_type[0]
            geometry_coordinates_element =  children[geometry_type].getElementsByTagName('coordinates')[0].childNodes[0]

            geometry = [ GeoPoint(round(float(longitude), 8), round(float(latitude), 8), round(float(altitude), 8))
                    for (longitude, latitude, altitude) in[ coordinates.split(',') for coordinates in
                        geometry_coordinates_element.nodeValue.split(' ')]]

            place = Place(place_name, geometry_type, geometry)
            places.append(place)

    return places


def shift_kml_document(document, shift):
    """
    Apply the shift to every geometry element of the specified KML document.


    @param document: a KML document

    @param shift: a tuple ``(longitude, latitude)`` representing the
        geographical shift to apply to every geometry element of the KML
        document.


    @return: the specified KML document.
    """
    (shift_x, shift_y) = shift

    for element in document.getElementsByTagName('Placemark'):
        children = dict([ (child.nodeName, child) for child in element.childNodes ])

        geometry_type = [ _ for _ in SUPPORTED_KML_GEOMETRIES if children.get(_) ]
        if geometry_type:
            geometry_type = geometry_type[0]
            geometry_coordinates_element = children[geometry_type].getElementsByTagName('coordinates')[0].childNodes[0]

            geometry = [ (float(longitude), float(latitude), float(altitude))
                    for (longitude, latitude, altitude) in [ coordinates.split(',')
                            for coordinates in geometry_coordinates_element.nodeValue.split(' ') ]]

            geometry_coordinates_element.replaceWholeText(
                    ' '.join([ '%s,%s,%s' % (round(longitude - shift_x, 8), round(latitude - shift_y, 8), altitude)
                            for (longitude, latitude, altitude) in geometry ]))

    return document


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

    fixed_xml_document = shift_kml_document(original_xml_document, shift)

    if arguments.output_file_path_name is None:
        print fixed_xml_document.toxml()

    else:
        (_, file_extension) = os.path.splitext(arguments.output_file_path_name)
        assert file_extension.lower() != 'kml', 'Wrong output file extension; need to be KML or KMZ'

        with contextlib.closing(codecs.open(arguments.output_file_path_name, 'wt', encoding='utf-8')) as file_handle:
            original_xml_document.writexml(file_handle)
