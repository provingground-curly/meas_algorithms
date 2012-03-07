#!/usr/bin/env python

# 
# LSST Data Management System
# Copyright 2008, 2009, 2010 LSST Corporation.
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
# see <http://www.lsstcorp.org/LegalNotices/>.
#

# todo:
# - growth curves
# - 

import sys
import math
import pdb                          # we may want to say pdb.set_trace()
import unittest
import time

import numpy
import eups

import lsst.daf.base            as dafBase
import lsst.afw.math            as afwMath
import lsst.pex.exceptions      as pexEx
import lsst.pex.config          as pexConf
import lsst.pex.logging         as pexLog
import lsst.afw.image           as afwImage
import lsst.afw.detection       as afwDet
import lsst.afw.geom            as afwGeom
import lsst.afw.table           as afwTable
import lsst.afw.geom.ellipses   as geomEllip
import lsst.meas.algorithms     as measAlg

import lsst.afw.cameraGeom      as cameraGeom
import lsst.afw.cameraGeom.utils as cameraUtils

import lsst.utils.tests         as utilsTests

import lsst.afw.display.ds9     as ds9

numpy.random.seed(500) # make test repeatable

try:
    type(verbose)
except NameError:
    verbose = 0

try:
    display
except NameError:
    display = False
    
def plantSources(x0, y0, nx, ny, sky, nObj, wid, detector, useRandom=False):

    distorter = detector.getDistortion()
    
    img0 = afwImage.ImageF(afwGeom.ExtentI(nx, ny))
    img = afwImage.ImageF(afwGeom.ExtentI(nx, ny))
    
    ixx0, iyy0, ixy0 = wid*wid, wid*wid, 0.0
    m0 = geomEllip.Quadrupole(ixx0, iyy0, ixy0)

    edgeBuffer = 40.0*wid
    
    flux = 1.0e4
    nkx, nky = int(10*wid) + 1, int(10*wid) + 1
    xhwid,yhwid = nkx/2, nky/2

    nRow = int(math.sqrt(nObj))
    xstep = (nx - 1 - 0.0*edgeBuffer)/(nRow+1)
    ystep = (ny - 1 - 0.0*edgeBuffer)/(nRow+1)

    if useRandom:
	nObj = nRow*nRow

    goodAdded0 = []
    goodAdded = []
    
    for i in range(nObj):

	# get our position
	if useRandom:
	    xcen0, ycen0 = numpy.random.uniform(nx), numpy.random.uniform(ny)
	else:
	    xcen0, ycen0 = xstep*((i%nRow) + 1), ystep*(int(i/nRow) + 1)
	ixcen0, iycen0 = int(xcen0), int(ycen0)

	# distort position and shape
	p = distorter.distort(afwGeom.Point2D(xcen0, ycen0), detector)
	m = distorter.distort(afwGeom.Point2D(x0+xcen0, y0+ycen0), m0, detector)
	xcen, ycen = xcen0, ycen0 #p.getX(), p.getY()
	if (xcen < 1.0*edgeBuffer or (nx - xcen) < 1.0*edgeBuffer or
	    ycen < 1.0*edgeBuffer or (ny - ycen) < 1.0*edgeBuffer):
	    continue
	ixcen, iycen = int(xcen), int(ycen)
	ixx, iyy, ixy = m.getIxx(), m.getIyy(), m.getIxy()

	# plant the object
	tmp = 0.25*(ixx-iyy)**2 + ixy**2
	a2 = 0.5*(ixx+iyy) + numpy.sqrt(tmp)
	b2 = 0.5*(ixx+iyy) - numpy.sqrt(tmp)
	#ellip = 1.0 - numpy.sqrt(b2/a2)
	theta = 0.5*numpy.arctan2(2.0*ixy, ixx-iyy)
	a = numpy.sqrt(a2)
	b = numpy.sqrt(b2)

	c, s = math.cos(theta), math.sin(theta)
	good0, good = True, True
	for y in range(nky):
	    iy = iycen + y - yhwid
	    iy0 = iycen0 + y - yhwid
	    
	    for x in range(nkx):
		ix = ixcen + x - xhwid
		ix0 = ixcen0 + x - xhwid
		
		if ix >= 0 and ix < nx and iy >= 0 and iy < ny:
		    dx, dy = ix - xcen, iy - ycen
		    u =  c*dx + s*dy
		    v = -s*dx + c*dy
		    I0 = flux/(2*math.pi*a*b)		
		    val = I0*math.exp(-0.5*((u/a)**2 + (v/b)**2))
		    if val < 0:
			val = 0
		    prevVal = img.get(ix, iy)
		    img.set(ix, iy, val+prevVal)
		else:
		    good = False

		if ix0 >=0 and ix0 < nx and iy0 >= 0 and iy0 < ny:
		    dx, dy = ix - xcen, iy - ycen
		    I0 = flux/(2*math.pi*wid*wid)		
		    val = I0*math.exp(-0.5*((dx/wid)**2 + (dy/wid)**2))
		    if val < 0:
			val = 0
		    prevVal = img0.get(ix0, iy0)
		    img0.set(ix0, iy0, val+prevVal)
		else:
		    good0 = False

        if good0:
            goodAdded0.append([xcen,ycen])
        if good:
            goodAdded.append([xcen,ycen])

    # add sky and noise
    img += sky
    img0 += sky
    noise = afwImage.ImageF(afwGeom.ExtentI(nx, ny))
    noise0 = afwImage.ImageF(afwGeom.ExtentI(nx, ny))
    for i in range(nx):
	for j in range(ny):
	    noise.set(i, j, numpy.random.poisson(img.get(i,j) ))
	    noise0.set(i, j, numpy.random.poisson(img0.get(i,j) ))


    edgeWidth = int(0.5*edgeBuffer)
    mask = afwImage.MaskU(afwGeom.ExtentI(nx, ny))
    left   = afwGeom.Box2I(afwGeom.Point2I(0,0), afwGeom.ExtentI(edgeWidth, ny))
    right  = afwGeom.Box2I(afwGeom.Point2I(nx - edgeWidth,0), afwGeom.ExtentI(edgeWidth, ny))
    top    = afwGeom.Box2I(afwGeom.Point2I(0,ny - edgeWidth), afwGeom.ExtentI(nx, edgeWidth))
    bottom = afwGeom.Box2I(afwGeom.Point2I(0,0), afwGeom.ExtentI(nx, edgeWidth))
    
    for pos in [left, right, top, bottom]:
	msk = afwImage.MaskU(mask, pos, False)
	msk.set(msk.getPlaneBitMask('EDGE'))
	
    expos = afwImage.makeExposure(afwImage.makeMaskedImage(noise, mask, afwImage.ImageF(noise, True)))
    expos0 = afwImage.makeExposure(afwImage.makeMaskedImage(noise0, mask, afwImage.ImageF(noise0, True)))

    im = expos.getMaskedImage().getImage()
    im0 = expos0.getMaskedImage().getImage()
    im -= sky
    im0 -= sky

    
    return expos, goodAdded, expos0, goodAdded0

#################################################################
# quick and dirty detection (note: we already subtracted background)
def detectAndMeasure(exposure, detConfig, measConfig):
    schema = afwTable.SourceTable.makeMinimalSchema()
    detConfig.validate()
    measConfig.validate()
    detTask = measAlg.SourceDetectionTask(config=detConfig, schema=schema)
    measTask = measAlg.SourceMeasurementTask(config=measConfig, schema=schema)
    # detect
    table = afwTable.SourceTable.make(schema)
    sources = detTask.makeSourceCatalog(table, exposure)
    # ... and measure
    measTask.run(exposure, sources)
    return sources

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

class PsfSelectionTestCase(unittest.TestCase):
    """Test the aperture correction."""

    def setUp(self):
	self.x0, self.y0 = 0, 0
        self.nx, self.ny = 512, 512 #2048, 4096
	self.sky = 100.0
	self.nObj = 100

        # make a distorter
        # This is a lot of distortion ... from circle r=1, to ellipse with a=1.3 (ie. 30%)
        # For suprimecam, we expect only about 5%
	self.distCoeffs = [0.0, 1.0, 2.0e-04, 3.0e-8]
        lanczosOrder = 3
        coefficientsDistort = True
	self.distorter = cameraGeom.RadialPolyDistortion(self.distCoeffs, coefficientsDistort, lanczosOrder)

        # make a detector
        self.detector = cameraUtils.makeDefaultCcd(afwGeom.Box2I(afwGeom.Point2I(0,0),
                                                                 afwGeom.Extent2I(self.nx, self.ny)))
        self.detector.setDistortion(self.distorter)
        self.detector.setCenter(cameraGeom.FpPoint(255.5, 255.5)) # move boresight from center to 0,0

        if False:
            for x,y in [(0,0), (0, 511), (511,0), (511, 511)]:
                p = afwGeom.Point2D(x, y)
                iqq = self.distorter.distort(p, geomEllip.Quadrupole(), self.detector)
                print x, y, geomEllip.Axes(iqq)
                print self.detector.getPositionFromPixel(p).getMm()
        
        print "Max distortion on this detector: ", self.distorter.computeMaxShear(self.detector)
        

        # detection policies
        self.detConfig = measAlg.SourceDetectionConfig()

        # measurement policies
        self.measSrcConfig = measAlg.SourceMeasurementConfig()
        
        # psf star selector
        starSelectorFactory = measAlg.starSelectorRegistry["secondMoment"]
        starSelectorConfig = starSelectorFactory.ConfigClass()
        starSelectorConfig.fluxLim = 5000.0
        self.starSelector = starSelectorFactory(starSelectorConfig)
        
        # psf determiner
        psfDeterminerFactory = measAlg.psfDeterminerRegistry["pca"]
        psfDeterminerConfig = psfDeterminerFactory.ConfigClass()
        width, height = self.nx, self.ny
        nEigenComponents = 3
        psfDeterminerConfig.sizeCellX = width//3
        psfDeterminerConfig.sizeCellY = height//3
        psfDeterminerConfig.nEigenComponents = nEigenComponents
        psfDeterminerConfig.spatialOrder = 1
        psfDeterminerConfig.kernelSizeMin = 31
        psfDeterminerConfig.nStarPerCell = 0
        psfDeterminerConfig.nStarPerCellSpatialFit = 0 # unlimited
        self.psfDeterminer = psfDeterminerFactory(psfDeterminerConfig)
        

        
    def tearDown(self):
	del self.detConfig
	del self.measSrcConfig
	del self.distorter
        del self.detector
	del self.starSelector
	del self.psfDeterminer

        
    def testPsfCandidate(self):

        detector = self.detector
        distorter = self.distorter
        
	# make an exposure
        print "Planting"
	psfSigma = 1.5
	exposDist, nGoodDist, expos0, nGood0 = plantSources(self.x0, self.y0,
							    self.nx, self.ny,
							    self.sky, self.nObj, psfSigma, detector)
        
        
	# set the psf
	kwid = 21
	psf = afwDet.createPsf("SingleGaussian", kwid, kwid, psfSigma)
	exposDist.setPsf(psf)
	exposDist.setDetector(detector)

        
        # detect
        print "detection"
	sourceList       = detectAndMeasure(exposDist, self.detConfig, self.measSrcConfig)

        # select psf stars
        print "PSF selection"
        psfCandidateList = self.starSelector.selectStars(exposDist, sourceList)

        # determine the PSF
        print "PSF determination"
        metadata = dafBase.PropertyList()
        t0 = time.time()
        psf, cellSet = self.psfDeterminer.determinePsf(exposDist, psfCandidateList, metadata)
        print "... determination time: ", time.time() - t0
        print "PSF kernel width: ", psf.getKernel().getWidth()
        
        #######################################################################
        # try to subtract off the stars and check the residuals

        imgOrig = exposDist.getMaskedImage().getImage().getArray()
        maxFlux = imgOrig.max()

        
        ############
        # first try it with no distortion in the psf
        detector.setDistortion(None)

        print "uncorrected subtraction"
        subImg = afwImage.MaskedImageF(exposDist.getMaskedImage(), True)
	for s in sourceList:
	    x, y = s.getX(), s.getY()
            measAlg.subtractPsf(psf, subImg, x, y)

        if display:
            settings = {'scale': 'minmax', 'zoom':"to fit", 'mask':'transparency 80'}
            ds9.mtv(exposDist, frame=1, title="full", settings=settings)
            ds9.mtv(subImg, frame=2, title="subtracted", settings=settings)
            
        img = subImg.getImage().getArray()
        norm = img/math.sqrt(maxFlux)

        smin0, smax0, srms0 = norm.min(), norm.max(), norm.std()

        print "min:", smin0, "max: ", smax0, "rms: ", srms0


        ##############
        # try it with the correct distortion in the psf
        detector.setDistortion(distorter)

        print "corrected subtraction"
        subImg = afwImage.MaskedImageF(exposDist.getMaskedImage(), True)
	for s in sourceList:
	    x, y = s.getX(), s.getY()
            measAlg.subtractPsf(psf, subImg, x, y)

        if display:
            settings = {'scale': 'minmax', 'zoom':"to fit", 'mask':'transparency 80'}
            ds9.mtv(exposDist, frame=1, title="full", settings=settings)
            ds9.mtv(subImg, frame=2, title="subtracted", settings=settings)
            
        img = subImg.getImage().getArray()
        norm = img/math.sqrt(maxFlux)

        smin, smax, srms = norm.min(), norm.max(), norm.std()
        
        # with proper distortion, residuals should be < 4sigma (even for 512x512 pixels)
        print "min:", smin, "max: ", smax, "rms: ", srms

        # the distrib of residuals should be tighter
        self.assertTrue(smin0 < smin)
        self.assertTrue(smax0 > smax)
        self.assertTrue(srms0 > srms)
        

        

    def testDistortedImage(self):

	distorter = self.distorter
        detector = self.detector
        
	psfSigma = 1.5
        stars = plantSources(self.x0, self.y0, self.nx, self.ny, self.sky, self.nObj, psfSigma, detector)
        expos, starXy = stars[0], stars[1]
        
        # add some faint round galaxies ... only slightly bigger than the psf
	gxy = plantSources(self.x0, self.y0, self.nx, self.ny, self.sky, 10, 1.07*psfSigma, detector)
        mi = expos.getMaskedImage()
        mi += gxy[0].getMaskedImage()
        gxyXy = gxy[1]
        
	kwid = 15 #int(10*psfSigma) + 1
	psf = afwDet.createPsf("SingleGaussian", kwid, kwid, psfSigma)
	expos.setPsf(psf)


	expos.setDetector(detector)
        
	########################
	# try without distorter
	detector.setDistortion(None)
        print "Testing PSF selection *without* distortion"
	sourceList       = detectAndMeasure(expos, self.detConfig, self.measSrcConfig)
	psfCandidateList = self.starSelector.selectStars(expos, sourceList)
        
	########################
	# try with distorter
	detector.setDistortion(distorter)
        print "Testing PSF selection *with* distortion"
	sourceList       = detectAndMeasure(expos, self.detConfig, self.measSrcConfig)
	psfCandidateListCorrected = self.starSelector.selectStars(expos, sourceList)

        def countObjects(candList):
            nStar, nGxy = 0, 0
            for c in candList:
                s = c.getSource()
                x, y = s.getX(), s.getY()
                for xs,ys in starXy:
                    if abs(x-xs) < 2.0 and abs(y-ys) < 2.0:
                        nStar += 1
                for xg,yg in gxyXy:
                    if abs(x-xg) < 2.0 and abs(y-yg) < 2.0:
                        nGxy += 1
            return nStar, nGxy
        
        nstar, ngxy = countObjects(psfCandidateList)
        nstarC, ngxyC = countObjects(psfCandidateListCorrected)

	print "uncorrected nStar, nGxy: ", nstar, "/", len(starXy),"   ", ngxy, '/', len(gxyXy)
	print "dist-corrected nStar, nGxy: ", nstarC, '/', len(starXy),"   ", ngxyC, '/', len(gxyXy)
	
	########################
	# display
	if display:
	    iDisp = 1
	    ds9.mtv(expos, frame=iDisp)
            size = 40
	    for c in psfCandidateList:
		s = c.getSource()
                ixx, iyy, ixy = size*s.getIxx(), size*s.getIyy(), size*s.getIxy()
		ds9.dot("@:%g,%g,%g" % (ixx, ixy, iyy), s.getX(), s.getY(),
                        frame=iDisp, ctype=ds9.RED)
            size *= 2.0
	    for c in psfCandidateListCorrected:
		s = c.getSource()
                ixx, iyy, ixy = size*s.getIxx(), size*s.getIyy(), size*s.getIxy()
		ds9.dot("@:%g,%g,%g" % (ixx, ixy, iyy), s.getX(), s.getY(),
                        frame=iDisp, ctype=ds9.GREEN)
                
	# we shouldn't expect to get all available stars without distortion correcting
	self.assertTrue(nstar < len(starXy))
        
	# here we should get all of them, occassionally 1 or 2 might get missed
	self.assertTrue(nstarC >= 0.95*len(starXy))

        # no contamination by small gxys
        self.assertEqual(ngxyC, 0) 

		
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

def suite():
    """Returns a suite containing all the test cases in this module."""
    utilsTests.init()

    suites = []
    suites += unittest.makeSuite(PsfSelectionTestCase)
    suites += unittest.makeSuite(utilsTests.MemoryTestCase)

    return unittest.TestSuite(suites)

def run(exit=False):
    """Run the tests"""
    utilsTests.run(suite(), exit)
 
if __name__ == "__main__":
    run(True)

