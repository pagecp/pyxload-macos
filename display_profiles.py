"""Display-configuration signatures for restoring macOS window positions."""

from __future__ import annotations

import ctypes
import json
import sys


class CGPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


class CGSize(ctypes.Structure):
    _fields_ = [("width", ctypes.c_double), ("height", ctypes.c_double)]


class CGRect(ctypes.Structure):
    _fields_ = [("origin", CGPoint), ("size", CGSize)]


def _display_uuid(quartz, core_foundation, display_id: int) -> str:
    try:
        quartz.CGDisplayCreateUUIDFromDisplayID.restype = ctypes.c_void_p
        quartz.CGDisplayCreateUUIDFromDisplayID.argtypes = [ctypes.c_uint32]
        uuid = quartz.CGDisplayCreateUUIDFromDisplayID(display_id)
        core_foundation.CFUUIDCreateString.restype = ctypes.c_void_p
        core_foundation.CFUUIDCreateString.argtypes = [ctypes.c_void_p,
                                                       ctypes.c_void_p]
        string = core_foundation.CFUUIDCreateString(None, uuid)
        buffer = ctypes.create_string_buffer(128)
        core_foundation.CFStringGetCString.restype = ctypes.c_bool
        core_foundation.CFStringGetCString.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
        core_foundation.CFRelease.argtypes = [ctypes.c_void_p]
        ok = core_foundation.CFStringGetCString(string, buffer, len(buffer),
                                                0x08000100)
        core_foundation.CFRelease(uuid); core_foundation.CFRelease(string)
        if ok:
            return buffer.value.decode("utf-8")
    except (AttributeError, OSError, TypeError, ValueError):
        pass
    return f"display-{display_id}"


def display_signature() -> str:
    if sys.platform != "darwin":
        return "default"
    try:
        quartz = ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
        core_foundation = ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        displays = (ctypes.c_uint32 * 32)(); count = ctypes.c_uint32()
        quartz.CGGetActiveDisplayList.argtypes = [
            ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32)]
        if quartz.CGGetActiveDisplayList(32, displays, ctypes.byref(count)) != 0:
            return "default"
        quartz.CGDisplayBounds.restype = CGRect
        quartz.CGDisplayBounds.argtypes = [ctypes.c_uint32]
        configuration = []
        for display_id in displays[:count.value]:
            bounds = quartz.CGDisplayBounds(display_id)
            configuration.append({
                "id": _display_uuid(quartz, core_foundation, display_id),
                "x": round(bounds.origin.x), "y": round(bounds.origin.y),
                "w": round(bounds.size.width), "h": round(bounds.size.height),
            })
        configuration.sort(key=lambda item: item["id"])
        return json.dumps(configuration, sort_keys=True, separators=(",", ":"))
    except (OSError, AttributeError, TypeError, ValueError):
        return "default"
