#if !defined(LSST_DETECTION_DGPSF_H)
#define LSST_DETECTION_DGPSF_H
//!
// Describe an image's PSF
//
#include "lsst/meas/algorithms/PSF.h"
#include "lsst/meas/algorithms/detail/PSFImpl.h"

#include "boost/serialization/nvp.hpp"
#include "boost/serialization/void_cast.hpp"

// Forward declarations

namespace lsst { namespace meas { namespace algorithms {
    class dgPSF;
}}}

namespace boost {
namespace serialization {
    template <class Archive>
    void save_construct_data(
        Archive& ar, lsst::meas::algorithms::dgPSF const* p,
        unsigned int const file_version);
}}

namespace lsst { namespace meas { namespace algorithms {
            
/*!
 * \brief Represent a PSF as a circularly symmetrical double Gaussian
 */
class dgPSF : public PSF {
public:
    typedef boost::shared_ptr<dgPSF> Ptr;

    /**
     * @brief constructors for a dgPSF
     *
     * Parameters:
     */
    explicit dgPSF(int size, double sigma1, double sigma2=1, double b=0);
private:
    double doGetValue(double const dx, double const dy) const;

    double _sigma1;                     ///< Width of inner Gaussian
    double _sigma2;                     ///< Width of outer Gaussian
    double _b;                          ///< Central amplitude of outer Gaussian (inner amplitude == 1)

private:
    friend class boost::serialization::access;
    template <class Archive>
    void serialize(Archive& ar, unsigned int const version) {
        boost::serialization::void_cast_register<dgPSF, PSF>(
            static_cast<dgPSF*>(0), static_cast<PSF*>(0));
    };
    template <class Archive>
    friend void boost::serialization::save_construct_data(
            Archive& ar, dgPSF const* p, unsigned int const file_version);
};

}}} // namespace lsst::meas::algorithms

namespace boost {
namespace serialization {

template <class Archive>
inline void save_construct_data(
    Archive& ar, lsst::meas::algorithms::dgPSF const* p,
    unsigned int const file_version) {
    int size = p->getKernel()->getWidth();
    ar << make_nvp("size", size);
    ar << make_nvp("sigma1", p->_sigma1);
    ar << make_nvp("sigma2", p->_sigma2);
    ar << make_nvp("b", p->_b);
};

template <class Archive>
inline void load_construct_data(
    Archive& ar, lsst::meas::algorithms::dgPSF* p,
    unsigned int const file_version) {
    int size;
    double sigma1;
    double sigma2;
    double b;
    ar >> make_nvp("size", size);
    ar >> make_nvp("sigma1", sigma1);
    ar >> make_nvp("sigma2", sigma2);
    ar >> make_nvp("b", b);
    ::new(p) lsst::meas::algorithms::dgPSF(size, sigma1, sigma2, b);
};

}}


#endif
