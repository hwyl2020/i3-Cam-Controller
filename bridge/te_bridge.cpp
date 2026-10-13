// te_bridge.cpp
// Flat C API over the i3system Thermal Expert SDK (TE_B class, Type B models
// such as TE-Q2) so it can be called from Python via ctypes.
//
// Every entry point catches C++ exceptions: an exception must never cross the
// DLL boundary into the Python interpreter.

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstring>
#include <cstdio>

#ifndef _WINDOWS
#define _WINDOWS
#endif
#include "i3system_TE.h"
#include "i3system_imgproc.h"

#define TB_API extern "C" __declspec(dllexport)

using namespace i3;

namespace {
    struct Handle {
        TE_B *te = nullptr;
        int model = 0;
        int width = 0;
        int height = 0;
        bool enhanceInit = false;
    };

    template <typename F, typename R>
    R guard(F f, R fallback) {
        try { return f(); } catch (...) { return fallback; }
    }
}

// ---------------------------------------------------------------- discovery

// Scan USB for connected cameras. Fills up to `max` entries and returns the
// number of connected devices, or a negative value if the scan failed.
TB_API int tb_scan(int *dev_index, int *model, unsigned int *core_id, int max)
{
    return guard([&]() -> int {
        SCANINFO info[MAX_USB_NUM];
        if (ScanTE(info) != 1) return -1;
        int n = 0;
        for (int i = 0; i < MAX_USB_NUM && n < max; ++i) {
            if (info[i].bDevCon != 1) continue;
            dev_index[n] = i;
            model[n] = (int)info[i].nProdVer;
            core_id[n] = info[i].nCoreID;
            ++n;
        }
        return n;
    }, -2);
}

// Last USB diagnostic recorded by the SDK on the calling thread.
TB_API int tb_last_diag(int *operation, int *result, int *device,
                        char *text, int text_len)
{
    return guard([&]() -> int {
        USB_DIAGNOSTIC d{};
        if (!GetLastUsbDiagnostic(&d)) return 0;
        *operation = d.operation;
        *result = d.result;
        *device = d.deviceIndex;
        if (text && text_len > 0) {
            _snprintf_s(text, text_len, _TRUNCATE, "%s: %s",
                        GetUsbOperationName(d.operation),
                        GetUsbResultName(d.result));
        }
        return 1;
    }, 0);
}

// ------------------------------------------------------------ open / close

TB_API void *tb_open(int model, int dev_index)
{
    return guard([&]() -> void * {
        TE_B *te = OpenTE_B(model, dev_index);
        if (!te) return nullptr;
        Handle *h = new Handle();
        h->te = te;
        h->model = model;
        h->width = te->GetImageWidth();
        h->height = te->GetImageHeight();
        return h;
    }, (void *)nullptr);
}

TB_API void tb_close(void *hp)
{
    Handle *h = static_cast<Handle *>(hp);
    if (!h) return;
    guard([&]() -> int {
        if (h->enhanceInit) ReleaseImageEnhancement();
        // CloseTE releases the device and the SDK's own data; deleting the
        // object afterwards crashes the process, so the wrapper is leaked.
        if (h->te) h->te->CloseTE();
        return 0;
    }, 0);
    delete h;
}

TB_API int tb_width(void *hp)  { return hp ? static_cast<Handle *>(hp)->width : 0; }
TB_API int tb_height(void *hp) { return hp ? static_cast<Handle *>(hp)->height : 0; }

TB_API int tb_serial(void *hp, char *buf, int len)
{
    Handle *h = static_cast<Handle *>(hp);
    if (!h || !buf || len < 2) return 0;
    return guard([&]() -> int {
        char tmp[256] = {0};
        h->te->GetSerialNumber(tmp);
        strncpy_s(buf, len, tmp, _TRUNCATE);
        return 1;
    }, 0);
}

TB_API unsigned int tb_firmware(void *hp)
{
    Handle *h = static_cast<Handle *>(hp);
    if (!h) return 0;
    return guard([&]() -> unsigned int { return h->te->GetFirmwareVersion(); }, 0u);
}

// ------------------------------------------------------------- acquisition

// AGC applied 16-bit image. Returns the SDK RecvImage code (1 = success).
TB_API int tb_recv_agc(void *hp, unsigned short *dst)
{
    Handle *h = static_cast<Handle *>(hp);
    if (!h) return -1;
    return guard([&]() -> int { return h->te->RecvImage(dst); }, -3);
}

// Raw 32-bit float image (no AGC).
TB_API int tb_recv_raw(void *hp, float *dst)
{
    Handle *h = static_cast<Handle *>(hp);
    if (!h) return -1;
    return guard([&]() -> int { return h->te->RecvImage(dst); }, -3);
}

// Image after the SDK's output pipeline configured with tb_set_output.
// With AGC or processing enabled the output is 16-bit; dst must hold
// 4 bytes per pixel to be safe in either case.
TB_API int tb_recv_processed(void *hp, void *dst)
{
    Handle *h = static_cast<Handle *>(hp);
    if (!h) return -1;
    return guard([&]() -> int { return h->te->RecvImage(dst); }, -3);
}

TB_API void tb_set_output(void *hp, int agc, int proc_enable, int tnf, int snf,
                          float edge_level)
{
    Handle *h = static_cast<Handle *>(hp);
    if (!h) return;
    guard([&]() -> int {
        IMGOUTPRMS p{};
        p.agc = agc != 0;
        p.imgProc.enable = proc_enable != 0;
        p.imgProc.tnf = tnf != 0;
        p.imgProc.snf = snf != 0;
        p.imgProc.edgeLevel = edge_level;
        h->te->SetImgOutPrms(p);
        return 0;
    }, 0);
}

// i3 image enhancement (denoise + contrast + edge) on a raw float frame.
TB_API int tb_enhance(void *hp, unsigned short *dst, float *raw_src)
{
    Handle *h = static_cast<Handle *>(hp);
    if (!h) return 0;
    return guard([&]() -> int {
        if (!h->enhanceInit) {
            InitImageEnhancement(h->width * h->height);
            h->enhanceInit = true;
        }
        ImageEnhancement_B(dst, raw_src, h->width, h->height);
        return 1;
    }, 0);
}

// -------------------------------------------------------------- radiometry

// Temperature (deg C) of every pixel of the most recently received frame.
TB_API int tb_entire_temp(void *hp, float *dst)
{
    Handle *h = static_cast<Handle *>(hp);
    if (!h) return 0;
    return guard([&]() -> int { h->te->CalcEntireTemp(dst); return 1; }, 0);
}

TB_API float tb_calc_temp(void *hp, int x, int y)
{
    Handle *h = static_cast<Handle *>(hp);
    if (!h) return -999.f;
    return guard([&]() -> float { return h->te->CalcTemp(x, y); }, -999.f);
}

TB_API void tb_set_emissivity(void *hp, float e)
{
    Handle *h = static_cast<Handle *>(hp);
    if (!h) return;
    guard([&]() -> int { h->te->SetEmissivity(e); return 0; }, 0);
}

TB_API float tb_fpa_temp(void *hp)
{
    Handle *h = static_cast<Handle *>(hp);
    if (!h) return -999.f;
    return guard([&]() -> float { return h->te->GetFpaTemp(); }, -999.f);
}

// ------------------------------------------------------------- calibration

TB_API int tb_nuc(void *hp)
{
    Handle *h = static_cast<Handle *>(hp);
    if (!h) return -1;
    return guard([&]() -> int { return h->te->ShutterCalibrationOn(); }, -3);
}

TB_API int tb_lens_offset_cal(void *hp)
{
    Handle *h = static_cast<Handle *>(hp);
    if (!h) return -1;
    return guard([&]() -> int { return h->te->LensOffsetCalibration(); }, -3);
}

TB_API int tb_update_dead(void *hp)
{
    Handle *h = static_cast<Handle *>(hp);
    if (!h) return -1;
    return guard([&]() -> int { return h->te->UpdateDead(); }, -3);
}

TB_API int tb_add_dead(void *hp, int x, int y)
{
    Handle *h = static_cast<Handle *>(hp);
    if (!h) return -1;
    return guard([&]() -> int { return h->te->AddDead((unsigned)x, (unsigned)y); }, -3);
}

TB_API int tb_save_cal(void *hp, const char *path)
{
    Handle *h = static_cast<Handle *>(hp);
    if (!h) return 0;
    return guard([&]() -> int { return h->te->SaveCalibration(path) ? 1 : 0; }, 0);
}

TB_API int tb_load_cal(void *hp, const char *path)
{
    Handle *h = static_cast<Handle *>(hp);
    if (!h) return 0;
    return guard([&]() -> int { return h->te->LoadCalibration(path) ? 1 : 0; }, 0);
}

// ---------------------------------------------------------------- palettes

// 8-bit gray -> BGR888 using one of the SDK's 10 colormaps. Works without a
// camera, so the UI can build palette lookup tables at startup.
TB_API void tb_colormap(unsigned char *dst_bgr, unsigned char *src_gray,
                        int color, int width, int height)
{
    guard([&]() -> int { ApplyColorMap(dst_bgr, src_gray, color, width, height); return 0; }, 0);
}
