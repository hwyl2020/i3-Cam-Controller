#ifndef WINTYPES_H
#define WINTYPES_H

#include <unistd.h>
#include <assert.h>
#include <jni.h>

#define ASSERT(x)   assert(x)

#define Sleep(x)    usleep(x * 1000)

#define TRUE    (1)
#define FALSE   (0)

#define INFINITE    (0xFFFFFFFFU)

typedef unsigned char   byte;
typedef unsigned char   BYTE;
typedef unsigned long   DWORD;
typedef unsigned short  WORD;
typedef int             BOOL;
typedef unsigned int    UINT;
typedef void*           LPVOID;
typedef unsigned long   UINT32;
typedef long            INT32;
typedef long long       INT64;
typedef unsigned long long UINT64;
typedef unsigned short  USHORT;

typedef struct {
    long left;
    long top;
    long right;
    long bottom;
} RECT;

#endif // WINTYPES_H