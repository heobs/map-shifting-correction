#!/usr/bin/less
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

KML Shift Correction is a Command-Line Interface (CLI) script, written
in Python, that provides shift correction of geometries, like POINT
and POLYGON, in a Keyhole Markup Language (KML) document.

When Google updates its satellite imagery of a region, it sometimes
results that geometries, such as markers or shapes, are shifted about
around one meter on the map.  This phenomena is also known as "map
shifting".

This script is used to line up the geometries in a KML document.  It
accepts two arguments:

1. the original KML document with the geometries that don't appear
   correctly lined up with the new satellite photos of the region;

2. a copy of this KML document where one and only one POINT geometry
   has been manually fixed to properly match the new satellite photos
   of the region.

This script generates a new KML document where all the geometries have
been appropriately fixed.
