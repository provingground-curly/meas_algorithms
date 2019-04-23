#
# LSST Data Management System
#
# Copyright 2008-2016  AURA/LSST.
#
# This product includes software developed by the
# LSST Project (http://www.lsst.org/).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the LSST License Statement and
# the GNU General Public License along with this program.  If not,
# see <https://www.lsstcorp.org/LegalNotices/>.
#
import os
import numpy as np
import unittest

import lsst.geom
import lsst.afw.geom as afwGeom
import lsst.afw.math as afwMath
import lsst.afw.table as afwTable
import lsst.afw.image as afwImage
import lsst.meas.algorithms as measAlg
import lsst.utils.tests

try:
    type(verbose)
except NameError:
    verbose = 0
    display = False


class CoaddApCorrMapTest(lsst.utils.tests.TestCase):

    def testCoaddApCorrMap(self):
        """Check that we can create and use a coadd ApCorrMap."""
        coaddBox = lsst.geom.Box2I(lsst.geom.Point2I(0, 0), lsst.geom.Extent2I(100, 100))
        scale = 5.0e-5*lsst.geom.degrees
        cdMatrix = afwGeom.makeCdMatrix(scale=scale)
        crval = lsst.geom.SpherePoint(0.0, 0.0, lsst.geom.degrees)
        center = lsst.geom.Point2D(lsst.geom.Extent2D(coaddBox.getDimensions())*0.5)
        coaddWcs = afwGeom.makeSkyWcs(crpix=lsst.geom.Point2D(0, 0), crval=crval, cdMatrix=cdMatrix)
        schema = afwTable.ExposureTable.makeMinimalSchema()
        weightKey = schema.addField("customweightname", type="D", doc="Coadd weight")
        catalog = afwTable.ExposureCatalog(schema)

        # Non-overlapping
        num = 5
        inputBox = lsst.geom.Box2I(lsst.geom.Point2I(0, 0), lsst.geom.Extent2I(10, 10))
        validBox = lsst.geom.Box2I(lsst.geom.Point2I(0, 0), lsst.geom.Extent2I(7, 7))
        pointList = []
        pointListValid = []

        for i in range(num):
            value = np.array([[1]], dtype=float)  # Constant with value = i+1
            apCorrMap = afwImage.ApCorrMap()
            bf = afwMath.ChebyshevBoundedField(inputBox, value*(i + 1))
            apCorrMap.set("only", bf)

            point = lsst.geom.Point2D(0, 0) - lsst.geom.Extent2D(coaddBox.getDimensions())*(i+0.5)/num
            wcs = afwGeom.makeSkyWcs(crpix=point, crval=crval, cdMatrix=cdMatrix)
            center = inputBox.getCenter()
            pointList.append(coaddWcs.skyToPixel(wcs.pixelToSky(center)))

            # This point will only be valid for the second overlapping record
            pointValid = center + lsst.geom.Extent2D(4, 4)
            pointListValid.append(coaddWcs.skyToPixel(wcs.pixelToSky(pointValid)))

            # A record with the valid polygon defining a limited region
            record = catalog.getTable().makeRecord()
            record.setWcs(wcs)
            record.setBBox(inputBox)
            record.setApCorrMap(apCorrMap)
            record.set(weightKey, i + 1)
            record['id'] = i
            record.setValidPolygon(afwGeom.Polygon(lsst.geom.Box2D(validBox)))
            catalog.append(record)

            # An overlapping record with the whole region as valid
            record = catalog.getTable().makeRecord()
            record.setWcs(wcs)
            record.setBBox(inputBox)
            apCorrMap = afwImage.ApCorrMap()
            bf = afwMath.ChebyshevBoundedField(inputBox, value*(i + 2))
            apCorrMap.set("only", bf)
            record.setApCorrMap(apCorrMap)
            record.set(weightKey, i + 2)
            record['id'] = i + num
            record.setValidPolygon(afwGeom.Polygon(lsst.geom.Box2D(inputBox)))
            catalog.append(record)

        apCorrMap = measAlg.makeCoaddApCorrMap(catalog, coaddBox, coaddWcs, "customweightname")
        # This will test a point where both records contribute
        self.assertApCorrMap(apCorrMap, pointList)
        # Only the second record will be valid for this point
        self.assertApCorrMapValid(apCorrMap, pointListValid)

        filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), "coaddApCorrMap.fits")
        exposure = afwImage.ExposureF(1, 1)
        exposure.getInfo().setApCorrMap(apCorrMap)
        exposure.writeFits(filename)
        exposure = afwImage.ExposureF(filename)
        self.assertApCorrMap(exposure.getInfo().getApCorrMap(), pointList)
        self.assertApCorrMapValid(exposure.getInfo().getApCorrMap(), pointListValid)
        os.unlink(filename)

    def assertApCorrMap(self, apCorrMap, pointList):
        for i, point in enumerate(pointList):
            weights = [i + 1, i + 2]
            values = [i + 1, i + 2]
            expected = sum((w*v for w, v in zip(weights, values)), 0.0)/sum(weights)
            actual = apCorrMap["only"].evaluate(point)
            self.assertEqual(actual, expected)

    def assertApCorrMapValid(self, apCorrMap, pointList):
        for i, point in enumerate(pointList):
            weights = [i + 2]
            values = [i + 2]
            expected = sum((w*v for w, v in zip(weights, values)), 0.0)/sum(weights)
            actual = apCorrMap["only"].evaluate(point)
            self.assertEqual(actual, expected)


class TestMemory(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()
