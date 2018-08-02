import unittest
import numpy as np

import lsst.utils.tests

from lsst.afw.geom import Box2I, Point2I, Point2D, Extent2I, SpherePoint, degrees, makeCdMatrix, makeSkyWcs
from lsst.afw.image import PARENT
from lsst.afw.table import SourceTable
from lsst.meas.algorithms import DynamicDetectionTask
from lsst.meas.algorithms.testUtils import plantSources


class DynamicDetectionTest(lsst.utils.tests.TestCase):
    def setUp(self):
        xy0 = Point2I(12345, 67890)  # xy0 for image
        dims = Extent2I(2345, 2345)  # Dimensions of image
        box = Box2I(xy0, dims, invert=False)  # Bounding box of image
        sigma = 3.21  # PSF sigma
        buffer = 4.0  # Buffer for star centers around edge
        nSigmaForKernel = 5.0  # Number of PSF sigmas for kernel
        sky = 12345.6  # Sky level
        numStars = 100  # Number of stars
        noise = np.sqrt(sky)*np.pi*sigma**2  # Poisson noise per PSF
        faint = 1.0*noise  # Faintest level for star fluxes
        bright = 100.0*noise  # Brightest level for star fluxes
        starBox = Box2I(box)  # Area on image in which we can put star centers
        starBox.grow(-int(buffer*sigma))
        scale = 1.0e-5*degrees  # Pixel scale

        np.random.seed(12345)
        stars = [(xx, yy, ff, sigma) for xx, yy, ff in
                 zip(np.random.uniform(starBox.getMinX(), starBox.getMaxX(), numStars),
                     np.random.uniform(starBox.getMinY(), starBox.getMaxY(), numStars),
                     np.linspace(faint, bright, numStars))]
        self.exposure = plantSources(box, 2*int(nSigmaForKernel*sigma) + 1, sky, stars, True)
        self.exposure.setWcs(makeSkyWcs(crpix=Point2D(0, 0),
                                        crval=SpherePoint(0, 0, degrees),
                                        cdMatrix=makeCdMatrix(scale=scale)))

        # Make a large area of extra background; we should be robust against it
        # Unfortunately, some tuning is required here to get something challenging but not impossible:
        # * A very large box will cause failures because the "extra" and the "normal" are reversed.
        # * A small box will not be challenging because it's simple to clip out.
        # * A large value will cause failures because it produces large edges in background-subtrction that
        #     broaden flux distributions.
        # * A small value will not be challenging because it has little effect.
        extraBox = Box2I(xy0 + Extent2I(345, 456), Extent2I(1234, 1234),
                         invert=False)  # Box for extra background
        extraValue = 0.5*noise  # Extra background value to add in
        self.exposure.image[extraBox, PARENT] += extraValue

        self.config = DynamicDetectionTask.ConfigClass()
        self.config.skyObjects.nSources = 300
        self.config.reEstimateBackground = False
        self.config.doTempWideBackground = True
        self.config.thresholdType = "pixel_stdev"

        # Relative tolerance for tweak factor
        # Not sure why this isn't smaller; maybe due to use of Poisson instead of Gaussian noise?
        self.rtol = 0.1

    def tearDown(self):
        del self.exposure

    def check(self, expectFactor):
        schema = SourceTable.makeMinimalSchema()
        task = DynamicDetectionTask(config=self.config, schema=schema)
        table = SourceTable.make(schema)

        results = task.run(table, self.exposure, expId=12345)
        self.assertFloatsAlmostEqual(results.factor, expectFactor, rtol=self.rtol)

    def testVanilla(self):
        """Dynamic detection used as normal detection"""
        self.check(1.0)

    def testDynamic(self):
        """Modify the variance plane, and see if the task is able to determine what we did"""
        factor = 2.0
        self.exposure.maskedImage.variance /= factor
        self.check(1.0/np.sqrt(factor))

    def testNoSources(self):
        self.config.skyObjects.nSources = self.config.minNumSources - 1
        self.check(1.0)


class TestMemory(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    import sys
    setup_module(sys.modules['__main__'])
    unittest.main()
