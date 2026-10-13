#ifndef WINTYPES_H
#define WINTYPES_H

#ifndef _AFXEXT

#ifndef ASSERT
#include <assert.h>
#define ASSERT(x)   assert(x)
#endif

#ifndef TRUE
#define TRUE    (1)
#endif
#ifndef FALSE
#define FALSE   (0)
#endif

#ifndef INFINITE
#define INFINITE    (0xFFFFFFFFU)
#endif

typedef unsigned char   byte;
typedef unsigned char   uchar;
typedef unsigned char   BYTE;
typedef unsigned long   DWORD;
typedef unsigned short  WORD;
typedef int             BOOL;
typedef unsigned int    UINT;
typedef void*           LPVOID;
typedef unsigned int    UINT32;
typedef signed int      INT32;
typedef long long       INT64;
typedef unsigned long long UINT64;
typedef unsigned short  USHORT;
typedef void* HANDLE;
#endif // _AFXEXT

#ifdef _ANDROID
#include <jni.h>
#endif // _ANDROID

#ifndef _WINDOWS
#include <unistd.h>
#define Sleep(x)    usleep(x * 1000)
#endif // _WINDOWS

#ifndef FLT_MAX
#define FLT_MAX std::numeric_limits<float>::max()
#endif

#ifndef INFINITE
#define INFINITE 0xffffffff
#endif

typedef struct __CPoint{
    int x;
    int y;

    __CPoint(){
        x = y = 0;
    }

    __CPoint(int _x, int _y){
        x = _x;
        y = _y;
    }
}CPoint;

typedef struct __RECT {
    int left;
    int right;
    int top;
    int bottom;

    __RECT() {
        left = right = top = bottom = 0;
    }
} RECT;


#endif // WINTYPES_H
