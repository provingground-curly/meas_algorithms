// -*- LSST-C++ -*-
#include <cmath>
#include <cstdio>
#include <string>
#include <algorithm>

#include "lsst/base.h"
#include "lsst/utils/Utils.h"
#include "lsst/pex/logging/Trace.h"
#include "lsst/pex/exceptions.h"
#include "lsst/pex/policy/Policy.h"
#include "lsst/afw/detection.h"
#include "lsst/afw/detection/Psf.h"
#include "lsst/afw/image.h"
#include "lsst/afw/math/Statistics.h"
#include "lsst/meas/algorithms/CR.h"

using namespace std;
namespace eups = lsst::utils::eups;
namespace pexLogging = lsst::pex::logging; 
namespace pexPolicy = lsst::pex::policy;
namespace afwDetection = lsst::afw::detection;
namespace afwImage = lsst::afw::image;
namespace afwMath = lsst::afw::math;
namespace algorithms = lsst::meas::algorithms;
namespace ex = lsst::pex::exceptions;

typedef afwImage::MaskedImage<float> MImageF;
typedef pexPolicy::Policy PPolicy;
typedef afwDetection::Footprint Footprint;

/****************************************************************************************************/

int main() {
    pexLogging::Trace::setVerbosity("algorithms.CR", 2);

    afwImage::MaskedImage<float>::Ptr im;  // declare im outside scope of try block
    try {
        string afwdata = eups::productDir("afwdata");
        im = MImageF::Ptr(new MImageF(afwdata + "/CFHT/D4/cal-53535-i-797722_1"));
        im->getMask()->addMaskPlane("DETECTED");
    } catch(lsst::pex::exceptions::NotFoundException const& e) {
        cerr << e << endl;
        return 1;
    }

    double const fwhm = 5;              // pixels
    PTR(afwDetection::Psf) psf = afwDetection::createPsf("DoubleGaussian", 0, 0, fwhm/(2*sqrt(2*log(2))));

    PPolicy::Ptr policy;
    try {
        policy = PPolicy::Ptr(PPolicy::createPolicy(eups::productDir("meas_algorithms") +
                                                    "/pipeline/CosmicRays.paf") );
    } catch(ex::NotFoundException const& e) {
        cerr << e << endl;
        return 1;
    }

    cout << boost::format("%dx%d\n") % im->getWidth() % im->getHeight();
    //
    // to work
    //
    double const background = afwMath::makeStatistics(*im->getImage(), afwMath::MEAN).getValue();
    std::vector<Footprint::Ptr> crs = algorithms::findCosmicRays(*im, *psf, background,
                                                                 *policy->getPolicy("CR"));
    
    cout << boost::format("Found %d CRs\n") % crs.size();

    return 0;
}
