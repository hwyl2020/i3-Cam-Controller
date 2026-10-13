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
@brief  This file defines abstract class for communication with Thermal Expert
*/
#pragma once
#ifndef ASTROHN
#ifndef I3SYSTEM_TE_H
#define I3SYSTEM_TE_H

#include "i3_types.h"

#define MAX_USB_NUM	32

#ifdef _WINDOWS
#ifdef I3_DLL_EXPORT
#define I3_LIB_API __declspec(dllexport)
#else
#define I3_LIB_API __declspec(dllimport)
#endif
#elif defined(_LINUX)
#ifdef I3_LIB_EXPORT
#define I3_LIB_API __attribute__((visibility("default")))
#else
#define I3_LIB_API
#endif

#define TE_ARRIVAL 1
#define TE_REMOVAL 2
#endif // _WINDOWS

#define I3_TE_Q1	 0x01
#define I3_TE_V1	 0x02
#define I3_TE_EQ1	 0x03
#define I3_TE_EV1	 0x04
#define I3_TE_M1	 0x09
#define I3_TE_EQ2	 0x0C
#define I3_TE_EV2	 0x0D
#define I3_TE_Q2     0x0E
#define I3_TE_V2     0x0F
#define I3_TE_V2MINI 0x11

#ifdef FOR_INTERNAL
#define I3_TE_XGA 0x10
#endif // FOR_INTERNAL

#define I3_TEMP_SHUTTER		0x0000
#define I3_TIME_SHUTTER		0x0001
#define I3_MANUAL_SHUTTER	0x0002

#define I3_SHUTTER_TIME_MIN 0x0001
#define I3_SHUTTER_TIME_MAX 0x0078

#define I3_SHUTTER_TEMP_MIN 0x0001
#define I3_SHUTTER_TEMP_MAX 0x000A

#define I3_COLORMAP_WHITEHOT		0
#define I3_COLORMAP_BLACKHOT		1
#define I3_COLORMAP_IRON			2
#define I3_COLORMAP_BLUERED			3
#define I3_COLORMAP_MEDICAL			4
#define I3_COLORMAP_PURPLE			5
#define I3_COLORMAP_PURPLEYELLOW	6
#define I3_COLORMAP_DARKBLUE		7
#define I3_COLORMAP_CYAN			8
#define I3_COLORMAP_RAINBOW			9

#ifdef FOR_INTERNAL
#define I3_NO_AGC 0
#define I3_BI_AGC 1
#define I3_CLIP_AGC2 2
#define I3_CLIP_AGC6 3

#endif // FOR_INTERNAL

#ifdef _HDPRO
#define I3_FPS_30	0
#define I3_FPS_25	1

#define I3_NOT_EXPORTABLE 0
#define I3_EXPORTABLE     1

#define I3_NTSC	1
#define I3_PAL 2

#define I3_QVGA (1)
#define I3_VGA	(2)
#define I3_XGA	(3)
#define I3_SXGA (4)
#endif // _HDPRO

#ifdef _LG_
namespace i3 {
	typedef struct tagCallbackBuffer {
		void *memBuf;
		UINT memSize;
		__int64 clk;
	}CbBuf, *LPCbBuf;
}
#endif // _LG_

namespace i3 {

	typedef enum UsbDiagnosticOperation {
		I3_USB_OPERATION_NONE = 0,
		I3_USB_OPERATION_SCAN = 1,
		I3_USB_OPERATION_OPEN = 2,
		I3_USB_OPERATION_CONTROL = 3,
		I3_USB_OPERATION_SEND = 4,
		I3_USB_OPERATION_RECEIVE = 5,
		I3_USB_OPERATION_INITIALIZE = 6
	} USB_DIAGNOSTIC_OPERATION;

	typedef enum UsbDiagnosticResult {
		I3_USB_DIAGNOSTIC_SUCCESS = 1,
		I3_USB_DIAGNOSTIC_NULL_HANDLE = 100,
		I3_USB_DIAGNOSTIC_SHORT_CONTROL = 101,
		I3_USB_DIAGNOSTIC_INCOMPLETE_TRANSFER = 102,
		I3_USB_DIAGNOSTIC_INVALID_PARAMETER = 103,
		I3_USB_DIAGNOSTIC_INITIALIZATION_FAILED = 1000,
		I3_USB_DIAGNOSTIC_USB_NOT_OPENED = 1001,
		I3_USB_DIAGNOSTIC_DEAD_READ_FAILED = 1002,
		I3_USB_DIAGNOSTIC_GAIN_READ_FAILED = 1003,
		I3_USB_DIAGNOSTIC_OFFSET_READ_FAILED = 1004,
		I3_USB_DIAGNOSTIC_MULTIOFFSET_READ_FAILED = 1005,
		I3_USB_DIAGNOSTIC_CERTIFICATION_FAILED = 1006,
		I3_USB_DIAGNOSTIC_FRAME_KIND_MISMATCH = 1007,
		I3_USB_DIAGNOSTIC_INVALID_MODEL = 1008,
		I3_USB_DIAGNOSTIC_RECOGNITION_FAILED = 1009
	} USB_DIAGNOSTIC_RESULT;

	typedef struct UsbDiagnostic {
		int operation;   /**< USB_DIAGNOSTIC_OPERATION */
		int result;      /**< Raw platform USB code or USB_DIAGNOSTIC_RESULT */
		int deviceIndex; /**< Device index for open, -1 for scan */
	} USB_DIAGNOSTIC;

    typedef int (*img_cb_fn)(void* _inBuf, void* _outBuf, void *_args);

	class ITE_A_Impl;
	class ITE_B_Impl;

	/*! \brief Interface for communication with Thermal Expert Type A(EQ1, EV1, EQ2, EV2)
     */
	class TE_A {
	public:
		/**
           @brief Constructor of TE_A class
		*/
		TE_A(void *_initParams);

		/**
           @brief Destructor of TE_A class
		*/
		virtual ~TE_A();

		/**
           @brief Disconnect Thermal Expert
           @remark This function disconnect the Thermal Expert and delete data. Call this function after finishing the work.
		*/
		virtual void CloseTE();

		/**
           @brief Receive image data
           @param pRecvImage : variable to get image data (384x288 for QVGA and 640x480 for VGA, 16bits)
           @param _AGC_On : if set true, AGC algorithm is applied. Otherwise, AGC is not applied.
           @return 1: Read image successfully
           @return 2: Read image of size 0 (image not ready)
           @return 3: Recieved image size is not equal to requested size
           @return 4: Data read fail
           @remark This function receive data from Thermal Expert and calibrate to show image. It send image data to pRecvImage. If _AGC_On is set to true, gain and offset value is automatically calculated so that image data will be fitted to 16bit range.
		*/
		virtual int RecvImage(unsigned short *pRecvImage, bool _AGC_On);

		/**
           @brief Receive image data with temperature limit
           @param img_buf : variable to get image data (384x288 for QVGA and 640x480 for VGA, 16bits)
           @param temp_min : minimum temperature to express in image
           @param temp_max : maximum temperature to express in image
           @return 1: Read image successfully
           @return 2: Read image of size 0 (image not ready)
           @return 3: Recieved image size is not equal to requested size
           @return 4: Data read fail
           @remark This function receive image data from Thermal Expert and manipulate data to express scene within temperature range. if temperature is smaller than temp_min, 0 will be assigned, and if temperature is greater than temp_max, 65535 will be assigned.  temperature within those limit will set value between 0 and 65535 depending on temperature.
		*/
		virtual int RecvImage(unsigned short *img_buf, float temp_min, float temp_max);

		/**
           @brief Receive image data which image processing algorithm is applied to.
           @param dst : Buffer to get output image.
           @return 1: Read image successfully
           @return 2: Read image of size 0 (image not ready)
           @return 3: Recieved image size is not equal to requested size
           @return 4: Data read fail
           @remark This function receives data from Thermal Expert and applies image processing algorithm depending on parameters set. Parameters for image processing algorithms can be set in SetImgOutPrms function. AGC is enabled and other image processing algorithms are disabled in default setting.
		*/
        virtual int RecvImage(unsigned short *dst);

		/**
           @brief Set Image Output Parameters
           @param prms : Parameters to apply.
           @remark This function sets parameters to determine image processing algorithms which is appiled after receiving raw data from thermal detector. These parameters are applied when user gets image from RecvImage(unsigned short *dst) function. Other RecvImage function does not apply these parameters and returns data depending on its own arguments.
		*/
        virtual void SetImgOutPrms(IMGOUTPRMS prms);

		/**
           @brief Get image width
           @return Image width
           @remark Return width of image, i.e. it returns 384 for QVGA and 640 for VGA
		*/
		virtual int GetImageWidth();

		/**
           @brief Get image height
           @return Image height
           @remark Return height of image, i.e. it returns 288 for QVGA and 480 for VGA
		*/
		virtual int GetImageHeight();

		/**
           @brief Get temperature (1 pixel)
           @param _x : x coordinate
           @param _y : y coordinate
           @remark This function returns temperature for given pixel. RecvImage function should be called before calling this function. Returned values are modified to fit into 2byte. To get temperature, user should subtract 5000 and then divide by 100, i.e. (real temperature value) = (return value - 5000) / 100
		*/
		virtual unsigned short CalcTemp(unsigned short _x, unsigned short _y);

		/**
           @brief Get temperature of 1 frame
           @param _pTempBuf : buffer to get temperature data (384x288 for QVGA and 640x480 for VGA)
           @remark This function returns temperature data for entire image which is most recently received. Therefore RecvImage function should be called before calling this function. Returned values are modified to fit into 2byte. To get temperature, user should subtract 5000 and then divide by 100, i.e. (real temperature value) = (return value - 5000) / 100
		*/
		virtual void CalcTemp(unsigned short *_pTempBuf);

		/**
           @brief Reset TE engine
           @return true if reset signal is transferred successfully, otherwise return false
           @remark It sends signal to reset TE engine. After calling this function, TE will be rebooted.
		*/
		virtual bool ResetMainBoard();

		/**
           @brief Set emissivity value
           @param _emissivity : emissivity value to apply
           @remark It sets emissivity value and afterwards emissivity applied temperature value will be returned when calling CalcTemp function.
		*/
		virtual void SetEmissivity(float _emissivity);

		/**
           @brief Save current setting in TE
           @param _pSetting : Pointer of TE_SETTING struct which contains setting values to save
           @return true if save setting signal is transferred successfully, otherwise return false
           @remark It sends signal to save setting values in TE engine. Values in _pSetting struct will be saved. But, saved setting values are not applied until power is off. Keep cable connected more than 10 seconds. otherwise, it may remove data in flash memory. If settings are successfully saved, thsee values will be applied when TE is connected.
		*/
		virtual bool SaveSetting(TE_SETTING *_pSetting);

		/**
           @brief Get current setting in TE
           @param _pSetting : Pointer of TE_SETTING struct to get setting values
           @remark It returns current setting values in _pSetting variable.
		*/
		virtual void GetSetting(TE_SETTING *_pSetting);

		virtual bool UpdateTempData(float _target1, float _meas1, float _target2, float _meas2);

#ifdef _HDPRO
		/**
           @brief Update bad pixels
           @remark If some bad pixels are generated while operating, this function finds those pixels which have quite different value compared to nearby pixels, and correction algorithm will be applied afterwards. Also, it saves those pixels and save in dead.txt files.
		*/
		void UpdateDead();

		virtual unsigned short IsNTSCorPAL();
		virtual unsigned short IsQVGAorVGA();
		virtual int	 GetFWVer();
#endif // _HDPRO

		/**
           @brief Set shutter operation mode
           @param _mode : Shutter operation mode. (Time mode = I3_TIME_SHUTTER, Temperature mode = I3_TEMP_SHUTTER)
           @return true : Signal is transferred successfully
           @return false : Transfer of signal failed
           @remark Shutter in TE engine is automatically closed and do calibration to maintain high image quality. This function set a condition when shutter is closed. It supports time mode which closes shutter periodically with specified period and temperature mode which closes shutter when temperature of shutter is changed with specified amount.
           @remark See SetShutterTemperature and SetShutterTime.
		*/
		virtual bool SetShutterMode(unsigned short _mode);

		/**
           @brief Set period of shutter operation
           @param _time : Period of shutter operation. This value should be withnin I3_SHUTTER_TIME_MIN and I3_SHUTTER_TIME_MAX.
           @return true : set signal is transferred successfully
           @return false : Transfer of signal failed
           @remark This function is used to set period of shutter operation. Shutter is close for every _time * 30 sec if time shutter mode is set.
           @remark See SetShutterMode.
		*/
		virtual bool SetShutterTime(unsigned short _time);

		/**
           @brief Set temperature variation limit to close shutter
           @param _temp : temperature variation limit. This value should be withnin I3_SHUTTER_TEMP_MIN and I3_SHUTTER_TEMP_MAX.
           @return true : set signal is transferred successfully
           @return false : Transfer of signal failed
           @remark When temperature shutter mode is set, shutter will be closed if temperature change of shutter is over temperature variation limit. This function set the limit.
           @remark See SetShutterMode.
		*/
		virtual bool SetShutterTemperature(unsigned short _temp);

		/**
           @brief Do calibration
           @return true: success
           @return false: fail
           @remark This function will close shutter and recalculate offset values to obtain uniform image.
		*/
		virtual bool ShutterCalibrationOn();

		/**
           @brief Get serial number of TE
           @return serial number
           @remark This function returns serial number of TE which is unique for each product.
		*/
		virtual unsigned int GetID();

		/**
           @brief Get FPA temperature
           @return fpa temperature
           @remark This function returns fpa temperature. This value depends on environment temperature. Also it is different for every TE even though TEs are in same condition.
           @remark FPA temperature is updated when image is taken from TE and this function returns most recently received value.
		*/
		virtual float GetFpaTemp();

		/**
           @brief Get PT100 sensor output
           @return PT100 sensor output
           @remark PT100 sensor is attached to shutter in order to calibrate temperature and it returns this PT100 sensor output.
           @remark PT100 output value is updated when shutter is closed. Therefore if shutter is not closed for long time, it may return incorrect value. User should close shutter periodically to get correct value by calling ShutterCalibrationOn or SetShutterMode function.
           @remark Also, TE sends this value at the end of image data, so it returns PT100 output which is received at last RecvImage function call. To get current PT100 output, RecvImage needs to be called before calling this function.
		*/
		virtual unsigned short GetShutterPt100RawValue();

		/**
           @brief Get Shutter temperature
           @return Shutter temperature
           @remark PT100 sensor is attached to shutter in order to calibrate temperature and it returns this shutter temperature computed from this PT100 sensor output.
           @remark PT100 output value is updated when shutter is closed. Therefore if shutter is not closed for long time, it may return incorrect value. User should close shutter periodically to get correct value by calling ShutterCalibrationOn or SetShutterMode function.
           @remark Also, TE sends this value at the end of image data, so it returns PT100 output which is received at last RecvImage function call. To get current PT100 output, RecvImage needs to be called before calling this function.
		*/
		virtual float GetShutterPt100Temp();

		/**
           @brief Save calibration data in file
           @return true: success
           @return false: fail
           @remark This function will save offset values to obtain uniform image in file with given path. Before calling this function, call LensShadingCorrection function.
		*/
		virtual bool SaveCalibration(const char *_path);

        /**
           @brief Load calibration data
           @param _path : file name to load
           @return true : succeeded to load data
           @return false : failed to load data (file open fail, incorrect file size, or incorrect data load)
           @remark If user have calibration data (using SaveCalibration function), user can load that file and apply calibration data to improve image quality.
           @remark Incorrect file load can cause bad image quality or file load fail.
		*/

		virtual bool LoadCalibration(const char *_path);

        /**
           @brief Do Lens Shading Correction
           @return true if success. otherwise false
           @remark This function calibrate shading at outer position generated by lens effect in order to make uniform image. Thermal Expert engine should see uniform scene before executing this function.
        */
		virtual bool LensShadingCorrection();

		/**
           @brief Set agc limit gain
           @param _limitGain : limit gain value. should be greater than 0.
           @return false if argument is less than or equal to zero. true otherwise.
           @remark Automatic Gain Control(AGC) algorithm is applied in thermal image to create more clearer image. But, if contrast is enhanced too much, image can be seen too noisy.
           @remark Limit gain controls how much it will enhance contrast for flat scene. Larger limit gain will enhance contrast more. This function is for setting this limit gain.
		*/
		virtual bool SetAgcLimitGain(float _limitGain);

		/**
           @brief Get limit gain value
           @return Current limit gain value
           @remark This function returns limit gain currently used. (See SetAgcLimitGain function for more about limit gain.)
		*/
		virtual float GetAgcLimitGain();

#ifdef _LIG
		/**
           @brief Change TE operation setting
           @param table : setting table, 0 for lower temperature and 1 for higher temperature setting
           @return true: succeed to send command
           @return false: fail to send command
           @remark Since detector output is changed depending on the environment temperature, data saturation can be occured in igh environment temperature. To prevent this, TE stores 2 setting conditions, one for lower temperature and the other for higher temperature.
           @remark Therefore, when environment temperature crosses borderline temperature, operation setting needs to be changed. Pass 0 for low temperature and 1 for high temperature.
		*/
		virtual bool ChangeOperationTable(WORD table);
#endif // _LIG


#ifdef FOR_INTERNAL
        virtual bool SetFrameRate(unsigned short _rate);
		virtual bool SetExportable(unsigned short _ver);

        /**
           @brief Write Engine ID in flash memory
           @param _id: ID of engine to write
           @remark This function id value to flash memory. Keep cable connected more than 10 seconds to write successfully. If it is written successfully, user can get id value from ScanTE function.
        */
		virtual bool WriteEngineID(unsigned short _id);


		/// image processing
		/**
		 *		@brief Set AGC Parameters
		 */
		virtual void SetAgcParams(AGCPRMS &_prms);

		/**
		 *	@brief	Save ROI in flash (for HQ1)
         */
		virtual bool SetVisibleRoi(RECT _roi);

		/**
         *	@brief Load ROI (for HQ1)
         */
		virtual RECT GetVisibleRoi();

		/**
           @brief continuously receive image
		*/
		virtual bool Run();

		/**
           @brief stop image receiving
		*/
		virtual void Stop();

		/**
           @brief set callback setting
		*/
		virtual void SetRecvCallback(img_cb_fn _cb, int _mode, int _period, void *_args, int _argsLen);

		/**
           @brief Set high temp or normal temp mode for EQ2
		*/
		virtual bool SetHighTempMode(bool _on);

		/**
           @brief Get high temp or normal temp mode for EQ2
		*/
		virtual bool GetHighTempMode();

		/**
           @brief Set high temp or normal temp mode for EQ2
		*/
		virtual void LoadCalibOsData(int *_cal);

		/**
           @brief load offset data for normal temp mode & high temp mode (ver2)
		*/
		virtual bool LoadCalibOsData(const char *_path_normal, const char* _path_high);

		/**
           @brief Get package version
		*/
		virtual int GetPackVer();

		/**
           @brief Calibration without shutter close (calibrate image only)
		*/
		virtual bool ImageCalibrationWoShutter();

		/**
           @brief Calibration without shutter close (calibrate image & temperature)
		*/
		virtual bool ImageAndTempCalibrationWoShutter();

		/**
           @brief Get current data & save in m_pwDataLow (use to calc calibration data)
		*/
		virtual bool GetDataLow();

		/**
           @brief Get current data & save in m_pwDataHigh (use to calc calibration data)
		*/
		virtual bool GetDataHigh();

		/**
           @brief Calc 1st order calibration data (use m_pwDataLow & m_pwDataHigh)
		*/
		virtual void UpdateCalData();

		virtual void SetCalLowHighDiff(WORD _diff);

		/**
           @brief save calibration data for 1st order calibration. (EQ2 with shutter)
		*/
		virtual bool SaveFirstOrderCalData();

		/**
           @brief load calibration data for 1st order calibration. (EQ2 with shutter)
		*/
		virtual void LoadFirstOrderCalData(const char *_fname);

		void CalcTempRaw(float *buf);
		float CalcTempRaw(int x, int y);

		/**
           @brief 
		*/
		virtual float GetTempGain();
		virtual float GetTempOffset();
		virtual int GetCurTempTableSel();
		virtual void GetRawData(WORD *_pbuffer);
		virtual int	GetHndDev();
		virtual int GetResolution();


		/**
           @brief send command to add dead pixel
		*/
		virtual bool AddBadPixel(int _x, int _y);
		virtual bool WriteBadPixel();
		virtual bool UpdateGainOffset(float _gain, float _offset, int _tempTable);
		virtual bool UpdateGainOffset(float *_gain, float *_offset);
		virtual bool WriteUpdatedTempCalData(int _mode);
		virtual BOOL GetTempGainOffset(float *_pfGain, float *_pfOffset, int _mode);
		virtual BOOL GetTempGainOffset(float *_pfGain, float *_pfOffset, bool _highTempMode, int _mode);
		virtual void GetAmbCorrGainOffset(float &_gain, float &_offset);
		virtual BOOL ResetDefaultGainOffset();
		virtual int GetModel();
		virtual void SetImageHeaderSize(int len);
		//virtual BOOL SetTempMode(WORD _mode);

        /**
           @brief Check TE firmware version
           @return firmware version
           @remark This function checks firmware version. firmwware version is saved as firmware update date. return value corresponds to following. (MSB)(8bit:empty, 8bit:year, 8bit:month, 8bit:day)(LSB)
		*/
		virtual int GetFwVer();
		virtual void SetAgcMode(UINT agc_mode);
		virtual int SendCommand(WORD *buf);
		virtual int SendCommand(UCHAR *buf, DWORD &send_byte, DWORD len);


		virtual float GetPt100Temp();
		virtual float GetTempFromIndex(int idx);
		virtual WORD GetPT100Value();
		virtual WORD GetDigitalVal(int _x, int _y);
		virtual WORD GetReferenceVal();
		virtual WORD GetFPATemp();
		virtual WORD GetDeliveryVer();

		virtual bool SaveImageCalWoShutter(const char *_file);
		virtual bool LoadImageCalWoShutter(const char *_file);
		virtual bool SaveImageAndTempCalWoShutter(const char *_file);
		virtual bool LoadImageAndTempCalWoShutter(const char *_file);
		virtual void ResetCal();

		virtual UINT GetTempTableNum();

#endif
#ifdef _SW_ENGINE_DEAD
		/**
           @brief add dead pixel in dead table
		*/
		virtual void AddDead(int _x, int _y);

		/**
           @brief add column dead pixel in dead table
		*/
		virtual void AddColDead(int _x);
#endif // _SW_ENGINE_DEAD

#ifdef _TEST
		virtual void GetGainOffset(float &_fTempGain, float &_fTempOffset, float &_fAmbTempGain, float &_fAmbTempOffset);
		virtual void MultiThreadTest(void(*callback)(unsigned short *buf, void *_callbackInput), void *callbackInput);
		virtual void DestroyThread();
		virtual int UsbRead(byte *_buf, unsigned int _size);
#endif // _TEST

	private:
		/**
           @brief TE_A implementation class
		*/
		ITE_A_Impl *m_pTE_Impl;
	};

	/*! \brief Interface for communication with Thermal Expert Type B(Q1, V1, M1, Q2, V2, V2Mini)
     */
	class TE_B {
	public:

		/**
           @brief Constructor of TE_B class
		*/
		TE_B(unsigned int _coreID, unsigned int _rcgData, int hnd_dev, int _modelNum);

		/**
           @brief Destructor of TE_B class
		*/
		virtual ~TE_B();

		/**
           @brief Disconnect Thermal Expert
           @remark This function disconnect the Thermal Expert and delete data. Do this function after finishing the work.
		*/
		virtual void	CloseTE();

		/**
           @brief Receive image data
           @param pRecvImage : variable to get image data (384x288 for QVGA and 640x480 for VGA, 32 bits gray data (not normalized))
           @return 1: Read image successfully
           @return 2: Read image of size 0 (image not ready)
           @return 3: Recieved image size is not equal to requested size
           @return 4: Data read fail
           @return 7: Flash Data is not read
           @remark This function receive data from Thermal Expert and calibrate to show image. It send image data to pRecvImage in which AGC algorithm is not applied. Gain and offset value should be applied in user side.
		*/
		virtual int		RecvImage(float *pRecvImage);

		/**
           @brief Receive image data
           @param pRecvImage : variable to get image data (384x288 for QVGA and 640x480 for VGA, 16 bits gray data)
           @return 1: Read image successfully
           @return 2: Read image of size 0 (image not ready)
           @return 3: Recieved image size is not equal to requested size
           @return 4: Data read fail
           @return 7: Flash Data is not read
           @remark This function receive data from Thermal Expert and calibrate to show image. It applies AGC algorithm, and then send image data fitted to 16bits to input argument pRecvImage.
		*/
		virtual int		RecvImage(unsigned short *pRecvImage);

		/** Receive a V2Mini image followed by metadata; optionally apply AGC. */
		virtual int		RecvImage(unsigned short *pRecvImage, bool _agc);


        /**
           @brief Receive image data which image processing algorithm is applied to.
           @param dst : Buffer to get output image. If no post processing is applied, float data is returned, so buffer size should be (4 * pixel num). Otherwise, 16 bit data is returned and buffer size should be (2 * pixel num).
           @return 1: Read image successfully
           @return 2: Read image of size 0 (image not ready)
           @return 3: Recieved image size is not equal to requested size
           @return 4: Data read fail
           @remark This function receives data from Thermal Expert and applies image processing algorithm depending on parameters set. Parameters for image processing algorithms can be set in SetImgOutPrms function. AGC is enabled and other image processing algorithms are disabled in default setting.
		*/
        virtual int RecvImage(void *dst);

		/**
           @brief Set Image Output Parameters
           @param prms : Parameters to apply.
           @remark This function sets parameters to determine image processing algorithms which is appiled after receiving raw data from thermal detector. These parameters are applied when user gets image from RecvImage(void *dst) function. Other RecvImage function does not apply these parameters and returns data depending on its own arguments.
		*/
        virtual void SetImgOutPrms(IMGOUTPRMS prms);

		/**
           @brief Do calibration
           @return 1: success
           @return 2: fail
           @remark This function will recalculate offset data for calibration.
           @remark Before calibration, stop receiving image data from Thermal Expert, and set Thermal Expert to see uniform temperature scene. It will recalculate offset to obtain uniform image.
		*/
		virtual int ShutterCalibrationOn();

        virtual int LensOffsetCalibration();

		/**
           @brief Calculate temperature
           @param _x : Horizontal position of target pixel (0~383 for QVGA, 0~639 for VGA)
           @param _y : Vertical position of target pixel (0~287 for QVGA, 0~479 for VGA)
           @return Temperature (Celsius)
           @remark Return temperature of target pixel (_x, _y) from previously received image data.
		*/
		virtual float CalcTemp(int _x, int _y);

		/**
           @brief Calculate temperature of all image pixels
           @param pRecvTemp : variable to get temperature data (384x288 for QVGA and 640x480 for VGA, 32bits)
           @remark Return temperature array of all pixels to pRecvTemp from previously received image data.
		*/
		virtual void CalcEntireTemp(float *pRecvTemp);

		/**
           @brief Update bad pixels
           @return 0 : fail to update
           @return 1 : succeed to update
           @remark In some cases, bad pixels can be generated while using TE which does not exist before, so it is considered non-dead pixel in flash data. This function receive images and analyze if additional bad pixels exist. If bad pixels exist, it will update dead data and calibration process will be applied to those pixels afterwards.
           @remark Update data is not stored after disconnection. So, User should call this function for every reconnection if user want to update bad pixels.
		*/
		virtual int UpdateDead();

		/**
           @brief Update bad pixels & save in files
           @return 0 : fail to update
           @return 1 : succeed to update
           @remark In some cases, bad pixels can be generated while using TE which does not exist before, so it is considered non-dead pixel in flash data. This function receive images and analyze if additional bad pixels exist. If bad pixels exist, it will update and save dead data and calibration process will be applied to those pixels afterwards. This function appends bad pixels in file, so to refresh bad pixels, delete file and call this function.
           @remark Update data is not stored after disconnection. So, User should call this function for every reconnection if user want to update bad pixels.
		*/
		virtual int UpdateDead(const char *path);

		/**
           @brief Add or remove bad pixel
           @param x : x coordinate of bad pixel
           @param y : y coordinate of bad pixel
           @return TRUE : pixel set as bad pixel
           @return FALSE : pixel set as not bad pixel
           @remark When some pixels look like dead pixels, user may want to set those pixels as bad pixels manually and do calibration for those pixels afterwards. It provides those functionality.
           @remark Insert x & y coordinate in arguments and it will set this pixel as bad pixel and calibartion will be done. To remove from bad pixel, call this function once more.
		*/
		virtual int AddDead(unsigned int x, unsigned int y);

		/**
           @brief Add or remove bad pixel
           @param pos : (width of image) * (y coordinate of bad pixel) + (x coordinate of bad pixel)
           @return TRUE : pixel set as bad pixel
           @return FALSE : pixel set as not bad pixel
           @remark When some pixels look like dead pixels, user may want to set those pixels as bad pixels manually and do calibration for those pixels afterwards. It provides those functionality.
           @remark Insert index of bad pixel in arguments and it will set this pixel as bad pixel and calibartion will be done. To remove from bad pixel, call this function once more.
		*/
		virtual int AddDead(unsigned int pos);

		/**
           @brief Get image width
           @return Image width
           @remark Return width of image, i.e. it returns 384 for QVGA and 640 for VGA
		*/
		virtual int		GetImageWidth();

		/**
           @brief Get image height
           @return Image height
           @remark Return height of image, i.e. it returns 288 for QVGA and 480 for VGA
		*/
		virtual int		GetImageHeight();

		/**
           @brief Set emissivity value
           @param _emissivity : emissivity value to apply
           @remark It sets emissivity value and afterwards emissivity applied temperature value will be returned when calling CalcTemp function.
		*/
		virtual void	SetEmissivity(float _emissivity);

		/**
           @brief Get FPA temperature
           @return fpa temperature
           @remark This function returns fpa temperature. This value depends on environment temperature. Also it is different for every TE even though TEs are in same condition.
           @remark FPA temperature is updated when image is taken from TE and this function returns most recently received value.
		*/
		virtual float GetFpaTemp();

		/**
           @brief Get FPA temperature raw value
           @return fpa temperature
           @remark This function returns fpa temperature. This value depends on environment temperature. Also it is different for every TE even though TEs are in same condition.
           @remark FPA temperature is updated when image is taken from TE and this function returns most recently received value.
		*/
		virtual unsigned short GetFPATemp();

        /**
           @brief Get 1 frame temperature data
           @param pRecvTemp : output temperature buffer
           @return 1: Read image successfully
           @return 2: Read image of size 0
           @return 3: Recieved image size is not equal to requested size
           @return 4: Data read fail
           @return 7: Flash Data is not read
           @remark This function returns 1 frame temperature data. Compared to CalcEntireTemp function, it does not use previously received data. It takes new data and calaculate temperature values.
		*/
		virtual int getFrameTemperature(float *pRecvTemp);

		/**
           @brief Save calibration data
           @param _file : file name to save data
           @return true : succeeded to save data
           @return false : failed to save data (file open fail or incorrect data save)
           @remark User can use ShutterCalibrationOn function to make uniform image. If user want to save this calibration data and use it later, user can use this function. (call ShutterCalibrationOn function first)
           @remark It saves calibration data in _file. This file can be used in Loadcalibration.
		*/
		virtual bool SaveCalibration(const char *_file);

		/**
           @brief Load calibration data
           @param _file : file name to load data
           @return true : succeeded to load data
           @return false : failed to load data (file open fail, incorrect file size, or incorrect data load)
           @remark If user have calibration data (using SaveCalibration function), user can load that file and apply calibration data to improve image quality.
           @remark Incorrect file load can cause bad image quality or file load fail.
		*/
		virtual bool LoadCalibration(const char *_file);

		/**
           @brief Set shutter operation mode
           @param _mode : Shutter operation mode. (Time mode = I3_TIME_SHUTTER, Temperature mode = I3_TEMP_SHUTTER)
           @return  0  : Signal is transferred successfully
           @return -7  : Transfer of signal failed
           @return -11 : Command not supported
           @remark Shutter in TE engine is automatically closed and do calibration to maintain high image quality. This function set a condition when shutter is closed. It supports time mode which closes shutter periodically with specified period and temperature mode which closes shutter when temperature of shutter is changed with specified amount. Only works in V2 & V2Mini.
           @remark See SetShutterTemperature and SetShutterTime.
		*/
		virtual int SetShutterMode(unsigned short _mode);

		/**
           @brief Set period of shutter operation
           @param _time : Period of shutter operation. This value should be withnin I3_SHUTTER_TIME_MIN and I3_SHUTTER_TIME_MAX.
           @return  0  : Signal is transferred successfully
           @return -7  : Transfer of signal failed
           @return -11 : Command not supported
           @remark This function is used to set period of shutter operation. Shutter is close for every _time * 30 sec if time shutter mode is set. Only works in V2 & V2Mini.
           @remark See SetShutterMode.
		*/
		virtual int SetShutterTime(unsigned short _time);

		/**
           @brief Set temperature variation limit to close shutter
           @param _temp : temperature variation limit. This value should be withnin I3_SHUTTER_TEMP_MIN and I3_SHUTTER_TEMP_MAX.
           @return  0  : Signal is transferred successfully
           @return -7  : Transfer of signal failed
           @return -11 : Command not supported
           @remark When temperature shutter mode is set, shutter will be closed if temperature change of shutter is over temperature variation limit. This function set the limit. Only works in V2 & V2Mini.
           @remark See SetShutterMode.
		*/
		virtual int SetShutterTemperature(unsigned short _temp);

		/**
		 *	@brief Get Serial Number
		 *	@param serial: output array to get serial number. array length should be greater than length of serial number.
		 */
		virtual void GetSerialNumber(char *serial);

		/** V2Mini acquisition, raw-frame, calibration and maintenance APIs. */
		virtual bool SetSyncMode(unsigned short _mode);
		virtual int GetRawFrame(unsigned short *buf);
		virtual void DeadCorrection(unsigned short *buf);
		virtual void NonUniformityCorrection(unsigned short *buf);
		virtual unsigned int GetSerialNum();
		virtual unsigned int GetFirmwareVersion();
		virtual int AddBadPixel(unsigned int _x, unsigned int _y);
		virtual void UpdateBadPixel();
		virtual bool WriteBadPixel();
		virtual void GetBadPixel(unsigned char *arr);
		virtual void ClearBadPixel();
		virtual int SaveBadPixels(const char *path);
		virtual int LoadBadPixels(const char *path);
		virtual int FirmwareUpdate(const char *path);

#ifdef _WORKSWELL
		/**
           @brief Convert image data to temperature data
           @param dst_temp : output temperature buffer
           @param src_img : input image buffer (not agc applied)
		*/
		void ImageToTemp(float *dst_temp, float *src_img);

#endif

		/**
           @brief Convert temperature data to image data
           @param pDstImg : output image buffer
           @param pSrcTemp : input temperature buffer
           @remark This function take temperature data from user, and convert it to image data to which image processing algorithm is applied.
		*/
		virtual void TempToImg(unsigned short *pDstImg, float *pSrcTemp);

#ifdef FOR_INTERNAL
		virtual bool AddBadPixel(int _x, int _y, int _mode);
		virtual bool WriteLensOffset();
		/**
           @brief returns TE model
           @return 1 - TE-Q1
           @return 2 - TE-V1
           @return 3 - TE-EQ1
           @return 4 - TE-EV1
           @remark This function returns connected TE model
		*/
		virtual int		GetModel();

		virtual bool SaveDeadCal(const char *_fName);

		virtual int		ReadFlashDataQ1();
		virtual int		ReadFlashData(CString dead_path, CString *gain_offset_path);
		virtual int		ReadFlashData(CString low_path, CString high_path);

		virtual void SetRawOffset(float *buf);

		virtual int		RecvImage(WORD *_pRecvImage, float _minT, float _maxT);
		virtual void	GetRawData(float *_pbuffer);

		virtual float GetTempGain();
		virtual float GetTempOffset();
		virtual void GetAmbientTempCoeff(float *_buf);
		virtual void GetFlashFpaTemp(float *buf);

		virtual bool ReceiveRawdata(WORD *dst, float &fpa_temp);
		virtual int RecvImage(WORD *dst, UINT agc_mode);
		virtual void SetAgcMode(UINT agc_mode);
		virtual void SetADC(UINT adc);
		virtual bool SendControlSignal(WORD recog_reload, WORD fps, WORD window, WORD col_start, WORD row_start, WORD col_end, WORD row_end, WORD save);

		virtual float CalcTempRaw(int x, int y);
		virtual int RecvImage_FpaAcc(float *buf, int acc_num);

		virtual float GetAmbientCorrTemp();

		virtual int UpdateDead(const char *path, double _sigma);
		virtual int UpdateDead(double _sigma);

		/**
           @brief Add or remove bad pixel
           @param x : x coordinate of bad pixel
           @param y : y coordinate of bad pixel
           @return TRUE : pixel set as bad pixel
           @return FALSE : pixel set as not bad pixel
           @remark When some pixels look like dead pixels, user may want to set those pixels as bad pixels manually and do calibration for those pixels afterwards. It provides those functionality.
           @remark This function sets given pixel as bad pixel and calibrate in HW.
           @remark Insert x & y coordinate in arguments and it will set this pixel as bad pixel and calibartion will be done. To remove from bad pixel, call this function once more.
		*/
		/**	@brief Get pt100 temperature */
		virtual WORD GetPt100Val();

		/**	@brief Get pt100 data */
		virtual WORD GetPt100Raw();

		/**	@brief Get data value for shutter */
		virtual WORD GetShutterCenterVal();

		/**	@brief Get data value for given pixel	*/
		virtual WORD GetData(int _x, int _y);

		/**	@brief Get sl data value for given pixel (shutter offset correction X) */
		virtual WORD GetSLData(int _x, int _y);

		/** @brief save roi (Q2) */
		virtual bool SetVisibleRoi(RECT _roi);

		/** @brief read roi (Q2) */
		virtual RECT GetVisibleRoi();

		/** @brief read version (Q2) */
		virtual int GetVersion();

		/** @brief load lens offset data (Q2) */
		virtual void LoadLensOffset(float *_offset);

		/** @brief Select data to use in lens offset (0 - flash data, 1 - file data, 2 - none) */
		virtual void SelLensOffsetData(int _data);

		/** @brief shutter open / close (V2) */
		virtual int ShutterOperation(bool _close);
		virtual bool WriteBadPixel(int _mode);
		virtual BOOL ShutterControl(bool _isOn);
		virtual int ReadDead(byte *dead, int mode);
		virtual int WriteRoicNuc(const char *path);

		/**
           @brief Calibration without shutter close (calibrate image & temperature)
		*/
		virtual bool ImageAndTempCalibrationWoShutter();

		/**
           @brief Save current setting in TE
           @param _pSetting : Pointer of TE_SETTING struct which contains setting values to save
           @return true if save setting signal is transferred successfully, otherwise return false
           @remark It sends signal to save setting values in TE engine. Values in _pSetting struct will be saved. But, saved setting values are not applied until power is off. Keep cable connected more than 10 seconds. otherwise, it may remove data in flash memory. If settings are successfully saved, thsee values will be applied when TE is connected.
		*/
		virtual bool SaveSetting(TE_SETTING *_pSetting);

		/** @brief get image data which lens offset is not applied to. used in test program. (Q2/V2) */
		virtual void GetImgWoLensOffset(float *_dst);

#endif

#ifdef _TEST
		virtual void SaveFlashData();
		virtual void SaveRawData();
		virtual void GetLensCorrData(int _x, int _y, float *_gain, float *_offset);
#endif // _TEST

#ifdef _API_TEST
		virtual int TableChange(int i);
		virtual bool WriteFactoryDead();
		virtual bool WriteUserDead();
		virtual bool WriteCamInfo(WORD *buf);
		virtual bool SetDeviceMode(unsigned short _mode);
		virtual int ReadFW(byte *buf);
		virtual int ReadRoicNuc(byte *buf);
#endif

	private:
		/**
           @brief TE_B implementation class
		*/
		ITE_B_Impl *m_pTE_Impl;
	};


	/**
       @brief Apply color to input image
       @param dst : output image (24bit color image, brg888)
       @param src : input image (8bit gray image)
       @param color : colormap to apply. its value ranges from I3_COLORMAP_WHITEHOT to I3_COLORMAP_RAINBOW.
       @param width : width of image
       @param height : height of image
       @remark : This function convert 8 bit input gray image to 24 bit (bgr888) color image. Supported colormaps are whitehot, blackhot, iron, bluered, medical, purple, purpleyellow, darkblue, cyan, and rainbow.
       @remark : Since received image from Thermal Expert is 16 bit, it needs to be converted to 8 bit image before applay this function.
	*/
	extern "C" I3_LIB_API void ApplyColorMap(unsigned char *dst, unsigned char *src, int color, int width, int height);

	/**
       @brief Check connected TE.
       @param pDevCon : Buffer to get scan results. It should MAX_USB_NUM size array.
       @return 1 : Scan successfully
       @return Otherwise : Failed to scan
       @remark This function scans connected TE and return the results. The result contains connected devices's ID, Product Model, and device number.
       @remark For each connected TE, a device number(0 ~ MAX_USB_NUM - 1) is assigned. TE which has device number i corresponeds to i-th element of pDevCon and its scaned result is stored in i-th element of pDevCon. This device number is used in other function as hnd_dev.
	*/
	extern "C" I3_LIB_API int ScanTE(SCANINFO *pDevCon);

	/** Return the last USB scan/open result on the calling thread. */
	extern "C" I3_LIB_API bool GetLastUsbDiagnostic(USB_DIAGNOSTIC *diagnostic);

	/** Stable names for USB_DIAGNOSTIC fields. */
	extern "C" I3_LIB_API const char *GetUsbOperationName(int operation);
	extern "C" I3_LIB_API const char *GetUsbResultName(int result);

	/**
       @brief Connect Thermal Expert of Type A model.
       @param hnd_dev : device number for TE to connect
       @return  nullptr : fail to open TE.
       @return  TE_A*(not nullptr) : pointer of TE_A class
       @remark This function get TE device handle and make TE ready to communicate with host. It must be called to communicate with TE.
	*/
	extern "C" I3_LIB_API TE_A*  OpenTE_A(int hnd_dev);

	/**
       @brief Connect Thermal Expert of Type B model.
       @param _model : Indicator for TE model. Set I3_TE_Q1 for Q1, I3_TE_V1 for V1 and I3_TE_Q2 for Q2.
       @param hnd_dev : Device number for TE to connect
       @return  nullptr : fail to open TE.
       @return  TE_B*(not nullptr) : pointer of TE_B class
       @remark This function get TE device handle and make TE ready to communicate with host. After connection, calibration data will be read from flash memory to create image. It may take few seconds.
       @remark This function must be called to communicate with TE.
	*/
	extern "C" I3_LIB_API TE_B*  OpenTE_B(int _model, int hnd_dev);


#ifdef _WINDOWS
	/**
       @brief Check TE connection
       @param iMsg : USB connection is changed or not
       @param wParam : TE is removed or arrived
       @param lParam : device information
       @return  1 : TE is arrived successfully
       @return  2 : TE is arrived but driver is not opened successfully
       @return  3 : TE is removed successfully
       @remark This function checks TE connection. Insert this function in WindowProc function of MFC dialog. Then it will return 1 if TE is connected through usb port and return 3 if TE is removed from usb port.
	*/
	extern "C" I3_LIB_API int __cdecl WindowProcTE(UINT iMsg, WPARAM wParam, LPARAM lParam);

	/**
       @brief Register TE device to get PNP information
       @param hwnd : A handle to the window that will receive device events.
       @return true : succeed in register
       @return false : failed to register
       @remark : This function register device for PNP notification. To get PNP information, call this function once when initialize program
	*/
	extern "C" I3_LIB_API bool __cdecl RegisterTE(HWND hwnd);

	/**
       @brief Unregister TE
       @remark : This function unregister device. call this function when PNP information is not required
	*/
	extern "C" I3_LIB_API void __cdecl UnregisterTE();

	//extern "C" I3_LIB_API void __cdecl testfnc();

#ifdef _LIG
	/**
       @brief Connect Thermal Expert of Type A model.
       @param hwnd : A handle to the window that will receive device events.
       @param model : model number to connect TE engine. (I3_TE_EQ1 or I3_TE_EV1)
       @param hnd_dev : device number for TE to connect
       @return  nullptr : fail to open TE.
       @return  TE_A*(not nullptr) : pointer of TE_A class
       @remark This function get TE device handle and make TE ready to communicate with host. It must be called to communicate with TE. This function is for TE engine which sends raw data.
	*/
	extern "C" I3_LIB_API TE_A* __cdecl OpenTE_A_Raw(HWND hwnd, int model, int hnd_dev);
#endif // _LIG
#elif defined(_LINUX)

#ifndef _USBSTATE
#define _USBSTATE
	/*! \brief struct for getting TE state change when TE is arrived or removed
     *
     * This structure is used for hotplug. When TE is arrived to or removed from usb port, hotplug callback function get this structure.
     */
	typedef struct UsbState {
		int nUsbState; /**< indicate if TE connection state is changed. 1 if TE arrived, 2 if TE removed  */
		int nUsbNum; /**< Device number of TE of which state is changed*/

		UsbState() {
			nUsbState = 0;
			nUsbNum = -1;
		}
		UsbState(int _nUsbState, int _nUsbNum) {
			nUsbState = _nUsbState;
			nUsbNum = _nUsbNum;
		}

		void operator=(struct UsbState UsbStateInput) {
			nUsbState = UsbStateInput.nUsbState;
			nUsbNum = UsbStateInput.nUsbNum;
		}
	}TE_STATE;
#endif // _USBSTATE

	/*! \brief function to be called when TE is arrived or removed
     *
     * This type definition is for hotplug callback function which can be called if TE is arrived or removed. To call this function, user should set hotplug callback function by calling SetHotplugcallback.
     */
	typedef void(*hotplug_callback_func)(TE_STATE _teState);

	/**
       @brief Set callback function which is called when TE is removed or arrived
       @remark TE connection is continuously checked internally and callback function is executed if TE is arrived to or removed from usb port. This function sets callback function to be executed.
	*/
	extern "C" I3_LIB_API void SetHotplugCallback(hotplug_callback_func _pFunc);

	/**
       @brief Clear callback function which is called when TE is removed or arrived
       @remark This function clears previsouly set callback function which is executed when TE is arrived to or removed from usb port.
	*/
	extern "C" I3_LIB_API void ClearHotplugCallback();
#endif 

#ifdef FOR_INTERNAL
	extern "C" I3_LIB_API TE_B* __cdecl OpenTE_Q1(int hnd_dev = 0);
	extern "C" I3_LIB_API void __cdecl AGC(WORD *_psrc, WORD *_pdst, float &_lowGain, float &_highGain, WORD &_mean, int _size);
	extern "C" I3_LIB_API void __cdecl ClipAGC(WORD * Recvimage, WORD * DstData, int size);
	extern I3_LIB_API TE_A* __cdecl OpenTE_A(int hnd_dev, int model);
	extern I3_LIB_API TE_B* __cdecl OpenTE_B(int hnd_dev);
#ifndef _x64
	extern "C" I3_LIB_API int __cdecl WindowProcTE_New(UINT iMsg, WPARAM wParam, LPARAM lParam, int &_hnd_dev);
#endif // _x64

#endif // FOR_INTERNAL
}
#endif // !I3SYSTEM_TE_H
#endif // ASTROHN
