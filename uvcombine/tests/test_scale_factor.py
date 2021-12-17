import pytest

import astropy.units as u
from astropy.io import fits
import numpy.testing as npt
import numpy as np

from .utils import testing_data
from ..scale_factor import find_effSDbeam, find_scale_factor

try:
    import statsmodels
    STATMODELS_INSTALLED = True
except ImportError:
    STATMODELS_INSTALLED = False


def fake_overlap_samples(size=1000):

    np.random.seed(67848923)

    lowres_pts = np.random.lognormal(size=size)
    highres_pts = np.abs(lowres_pts + np.random.normal(scale=0.05, size=size))

    return lowres_pts, highres_pts


@pytest.mark.skipif('not STATMODELS_INSTALLED')
def test_scale_factor_distrib():

    lowres_pts, highres_pts = fake_overlap_samples()

    sf, sf_stderr = find_scale_factor(lowres_pts, highres_pts,
                                      method='distrib')

    npt.assert_almost_equal(sf, 1.001, decimal=3)
    npt.assert_almost_equal(sf_stderr, 0.001, decimal=3)


def test_scale_factor_linfit():

    lowres_pts, highres_pts = fake_overlap_samples()

    sf, sf_CI = find_scale_factor(lowres_pts, highres_pts,
                                  method='linfit')

    npt.assert_almost_equal(sf, 0.998, decimal=3)
    npt.assert_almost_equal(sf_CI[0], 0.996, decimal=3)
    npt.assert_almost_equal(sf_CI[1], 1.000, decimal=3)


def test_scale_factor_sigclip():

    lowres_pts, highres_pts = fake_overlap_samples()

    sf_dict = find_scale_factor(lowres_pts, highres_pts,
                                method='clippedstats')

    npt.assert_almost_equal(sf_dict["scale_factor_mean"], 1.000, decimal=3)
    npt.assert_almost_equal(sf_dict["scale_factor_median"], 1.001, decimal=3)
    npt.assert_almost_equal(sf_dict["scale_factor_std"], 0.058, decimal=3)


def test_SDeff_beam():

    largest_scale = 56 * u.arcsec
    lowresfwhm = 30.*u.arcsec

    orig_hdu, lowres_hdu, highres_hdu = testing_data(return_images=True,
                                                powerlawindex=1.5,
                                                largest_scale=largest_scale,
                                                smallest_scale=3.*u.arcsec,
                                                lowresfwhm=lowresfwhm,
                                                pixel_scale=1*u.arcsec)

    lowresfwhms = np.arange(20, 40, 2) * u.arcsec

    slopes, slopes_CI = \
        find_effSDbeam(highres_hdu, lowres_hdu, largest_scale,
                       lowresfwhms,
                       beam_divide_lores=True,
                       lowpassfilterSD=False,
                       min_beam_fraction=0.1,
                       alpha=0.85,
                       verbose=True)

    # Smallest slope should be the actual FWHM of 30''
    # However, there's some uncertainty to deal with and there's a quadratic
    # behaviour if the SD beam size is overestimated by ~>40%.
    # Because of this, we check for the smallest negative value within 1-sigma uncertainty
    # of slope=0.
    estimated_lowresfwhm = lowresfwhms[np.where(slopes_CI[1] >= 0.)][0]
    assert estimated_lowresfwhm == lowresfwhm

    # See note above. This check can fail due to the quadratic behaviour for too
    # large lowresfwhms
    # assert lowresfwhms[np.argmin(np.abs(slopes))].value == lowresfwhm.value

