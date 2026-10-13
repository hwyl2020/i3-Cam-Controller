/*
 * Copyright (c) 2020 i3system Inc. All rights reserved.
 *
 * This library is licensed under the Creative Commons Attribution 4.0
 * International license. (CC-BY-4.0)
 * Redistribution must reproduce a identification of the creator, a copyright
 * notice, this list of conditions, and the following disclaimer.
 *
 * UNLESS OTHERWISE SEPARATELY UNDERTAKEN BY THE LICENSOR, TO THE
 * EXTENT POSSIBLE, THE LICENSOR OFFERS THE LICENSED MATERIAL AS-IS
 * AND AS-AVAILABLE, AND MAKES NO REPRESENTATIONS OR WARRANTIES OF
 * ANY KIND CONCERNING THE LICENSED MATERIAL, WHETHER EXPRESS,
 * IMPLIED, STATUTORY, OR OTHER. THIS INCLUDES, WITHOUT LIMITATION,
 * WARRANTIES OF TITLE, MERCHANTABILITY, FITNESS FOR A PARTICULAR
 * PURPOSE, NON-INFRINGEMENT, ABSENCE OF LATENT OR OTHER DEFECTS,
 * ACCURACY, OR THE PRESENCE OR ABSENCE OF ERRORS, WHETHER OR NOT
 * KNOWN OR DISCOVERABLE. WHERE DISCLAIMERS OF WARRANTIES ARE NOT
 * ALLOWED IN FULL OR IN PART, THIS DISCLAIMER MAY NOT APPLY TO YOU.

 * TO THE EXTENT POSSIBLE, IN NO EVENT WILL THE LICENSOR BE LIABLE
 * TO YOU ON ANY LEGAL THEORY (INCLUDING, WITHOUT LIMITATION,
 * NEGLIGENCE) OR OTHERWISE FOR ANY DIRECT, SPECIAL, INDIRECT,
 * INCIDENTAL, CONSEQUENTIAL, PUNITIVE, EXEMPLARY, OR OTHER LOSSES,
 * COSTS, EXPENSES, OR DAMAGES ARISING OUT OF THIS PUBLIC LICENSE OR
 * USE OF THE LICENSED MATERIAL, EVEN IF THE LICENSOR HAS BEEN
 * ADVISED OF THE POSSIBILITY OF SUCH LOSSES, COSTS, EXPENSES, OR
 * DAMAGES. WHERE A LIMITATION OF LIABILITY IS NOT ALLOWED IN FULL OR
 * IN PART, THIS LIMITATION MAY NOT APPLY TO YOU.
 */

/** @file
@brief  This file defines functions for thermal image processing.
*/
#pragma once
#ifndef ASTROHN
#ifndef I3SYSTEM_IMGPROC_H
#define I3SYSTEM_IMGPROC_H

#ifdef _WINDOWS
#ifdef I3_DLL_EXPORT
#ifndef I3_LIB_API
#define I3_LIB_API __declspec(dllexport)
#endif
#else
#ifndef I3_LIB_API
#define I3_LIB_API __declspec(dllimport)
#endif
#endif

#pragma warning(disable:4297)

#endif // _WINDOWS

#ifdef _LINUX
#ifdef I3_LIB_EXPORT
#ifndef I3_LIB_API
#define I3_LIB_API __attribute__((visibility("default")))
#endif
#else
#ifndef I3_LIB_API
#define I3_LIB_API
#endif
#endif
#endif


#ifdef FOR_INTERNAL
namespace i3 {

	/**
	@brief Apply AIE algorithm
	@param _srcImg : Source image to apply AIE algorithm (cv::Mat with CV_8UC1)
	@param _dstImg : AIE applied Output image (cv::Mat with CV_8UC1)
	@param _factor : Edge enhancement factor. As the _factor value is set  higher, edge will be more enhanced but image will be more noisier.
	@remark This function applies AIE algorithm to enhance edge in _srcImg and returns output image in _dstImg. This function get 8bit gray image, so 16bit image data which is received from TE should be converted to 8bit before apply AIE.
	*/
	//extern "C" I3_LIB_API void AIE(cv::Mat &_srcImg, cv::Mat &_dstImg, double _factor);

	extern "C" I3_LIB_API bool TProcessing(unsigned short *result, unsigned short *input, int height, int width, int filterSize, double lambda, bool denoise, bool ams_remove, bool he, bool denoise2, int agc);

	extern "C" I3_LIB_API void InitBilateralFilter();
	extern "C" I3_LIB_API void ChangeBilateralFilter(int sigma);

	extern "C" I3_LIB_API void SProcessing25_1(unsigned short *input, unsigned short *result, unsigned short *_delay1, int height, int width, bool _denoise, double lambda, int sigma, bool _isLocalHEOn, bool _isATROn, double _dLocalLimitGain, bool _isCLAHEEvenOnly, float _localHistoRatio, bool _3dnr, unsigned short *_3dnrPrev1, unsigned short *_3dnrPrev2, double _agcClipMultiple, double _agcLimitGain);
	extern "C" I3_LIB_API void SProcessing25_test(unsigned short *input, unsigned short *result, unsigned short *_delay1, int height, int width, bool _denoise, double lambda, int sigma, bool _isLocalHEOn, bool _isATROn, double _dLocalLimitGain, bool _isCLAHEEvenOnly, float _localHistoRatio, bool _3dnr, unsigned short *_3dnrPrev1, unsigned short *_3dnrPrev2, double _agcClipMultiple, double _agcLimitGain, double _maxAgcGainChange, bool _gaussian);

	extern "C" I3_LIB_API void SProcessing25_2(unsigned short *input, unsigned short *result, unsigned short *_delay1, int **_localHisto, int **_localHistoDelay, int height, int width, int filterSize, double lambda, bool gamma, int sigma, double _threshold, double _limitGain, bool _autoThreshold, double _nMin, bool _isATRGaussian, double _atrGaussianSigma, double _thresholdPer, bool _isLocalHEOn, bool _isATROn, bool _isOnlyLocal, double _dLocalLimitGain, bool _isCLAHEEvenOnly, bool _isClahe_ClipOn, double _dGamma, bool &_bIsCLHAEHysteresys, double &_dATRGammaFactor, unsigned char *_bySceneM);

	extern "C" I3_LIB_API void GetSProc25Delay(unsigned short *dst, unsigned short *src, int width, int height);

	/**
	@brief Image enhancement.
	@param input : 16bit input image to apply image enhancement
	@param result : 16bit output image
	@param height : height of image
	@param width : width of image
	@param filter_size : size of denoise filter. actual denoise filter size will be (2*filter_size) x (2*filter_size)
	@param denoise_factor : factor to determine how much noise will be removed. Greater denoise_factor will suppress more noise, but image will be more blurred. typical range is 0~1000.
	@param lamda : This parameter will determine how much image will be enhanced. large value of lamda can make image more noisy. typical range of this parameter is 0~10.
	@remark This function sharpen edge of image and enhance image contrast. Since image enhancement algorithm also enhance noise, denoise algorithm is applied. In order to get clear image, proper setting of denoise and enhancement factor needs to be applied. Otherwise, image can be too blur or too noisy.
	*/
	/* extern "C" I3_LIB_API void FProcessing(unsigned short *input, unsigned short *result, int height, int width, int filterSize, int denoise_factor, double lambda, bool gamma, int &counter, double *gain_cul, bool histo); */

	extern "C" I3_LIB_API void Init3DNR(float _sigmaSpace[], float _sigmaColor);
#ifdef _TEST
	extern "C" I3_LIB_API void SProcessing(unsigned short *input, unsigned short *result, int height, int width, int filterSize, double lambda, int &counter, double *gain_cul, bool histo, bool denoise, bool agc_lim, bool gamma);
#else
	extern "C" I3_LIB_API void SProcessing(unsigned short *input, unsigned short *result, int height, int width, int filterSize, double lambda, int &counter, double *gain_cul, bool histo, bool denoise, bool gamma);
#endif // _TEST

#ifdef _TEST
	extern "C" I3_LIB_API void InitGammaTable();
	extern "C" I3_LIB_API void GammaCorr(unsigned char *_src, unsigned char *_dst, int _gamma, int _size);

	extern "C" I3_LIB_API void IEGAGC(unsigned char *_src, unsigned char *_dst, int _width, int _height);
#endif // _TEST
}
#endif // FOR_INTERNAL

namespace i3 {
    /**
       @brief Initialize Image Enhancement Algorithm
       @param size : frame size
       @remark This function initializes parameters & buffers to be used in image enhancement algorithm. Call this function once before using ImageEnhancement Algorithm.
	*/
    extern "C" I3_LIB_API void InitImageEnhancement(int size);

    /**
       @brief Apply image enhancement algorithm
       @param dst: output image
       @param src: input image
       @param width: image width
       @param height: image height
       @remark This function applies image enhancement algorithm containing denoise, contrast enhancement, and edge enhancement. Use raw image data for src (AGC not applied).
	*/
    extern "C" I3_LIB_API void ImageEnhancement(unsigned short *dst, unsigned short *src, int width, int height);

    /**
       @brief Apply image enhancement algorithm
       @param dst: output image
       @param src: input image
       @param width: image width
       @param height: image height
       @remark This function applies image enhancement algorithm containing denoise, contrast enhancement, and edge enhancement. Use raw image data for src (AGC not applied).
	*/
    extern "C" I3_LIB_API void ImageEnhancement_B(unsigned short *dst, float *src, int width, int height);

    /**
       @brief Release buffers used in image enhancement algorithm
       @remark This function frees allocated memory. Call this function when image enhancement algorithm is no longer used.
	*/
    extern "C" I3_LIB_API void ReleaseImageEnhancement();
}

#endif // I3SYSTEM_IMGPROC_H

#endif // ASTROHN
