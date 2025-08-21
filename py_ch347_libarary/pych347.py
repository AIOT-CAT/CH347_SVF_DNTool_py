# py_ch347_libarary/pych347.py

import array
import cmd
import os
import ctypes
from ctypes import *
from pickle import TRUE
from weakref import ref

# Define the argument and return types for CH347GetDeviceInfor
MAX_PATH = 260

class mDeviceInforS(ctypes.Structure):
    _fields_ = [("iIndex", ctypes.c_ubyte),
                ("DevicePath", ctypes.c_char * MAX_PATH),
                ("UsbClass", ctypes.c_ubyte),
                ("FuncType", ctypes.c_ubyte),
                ("DeviceID", ctypes.c_char * 64),
                ("ChipMode", ctypes.c_ubyte),
                ("DevHandle", ctypes.c_void_p),
                ("BulkOutEndpMaxSize", ctypes.c_ushort),
                ("BulkInEndpMaxSize", ctypes.c_ushort),
                ("UsbSpeedType", ctypes.c_ubyte),
                ("CH347IfNum", ctypes.c_ubyte),
                ("DataUpEndp", ctypes.c_ubyte),
                ("DataDnEndp", ctypes.c_ubyte),
                ("ProductString", ctypes.c_char * 64),
                ("ManufacturerString", ctypes.c_char * 64),
                ("WriteTimeout", ctypes.c_ulong),
                ("ReadTimeout", ctypes.c_ulong),
                ("FuncDescStr", ctypes.c_char * 64),
                ("FirewareVer", ctypes.c_ubyte)
    ]

class ch347:
    MAX_DEVICE_NUMBER = 16
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
    
    def __init__(self, device_index=0, dll_path=None):
        if dll_path is None:
            # Let Windows find the DLL in system directories
            self.ch347dll = ctypes.cdll.LoadLibrary('D:/WCH/WCH_application/CH347/FAE-Test/PYCH347/CH341PAR/LIB/i386/CH347DLL.dll')
        else:
            # Use the specified path
            self.ch347dll = ctypes.WinDLL(dll_path)

        self.device_index = device_index
        # Define the argument and return types for CH347OpenDevice
        self.ch347dll.CH347OpenDevice.argtypes = [ctypes.c_ulong]
        self.ch347dll.CH347OpenDevice.restype = ctypes.c_void_p

        # Define the argument and return types for CH347CloseDevice
        self.ch347dll.CH347CloseDevice.argtypes = [ctypes.c_ulong]
        self.ch347dll.CH347CloseDevice.restype = ctypes.c_bool

        # Set the function argument types and return type for CH347Jtag_INIT
        self.ch347dll.CH347Jtag_INIT.argtypes = [ctypes.c_ulong, ctypes.c_ulong]
        self.ch347dll.CH347Jtag_INIT.restype = ctypes.c_bool

        # Set the function argument types and return type for CH347Jtag_IoScanT
        self.ch347dll.CH347Jtag_IoScanT.argtypes = [ctypes.c_ulong, ctypes.c_void_p, ctypes.c_ulong, ctypes.c_bool, ctypes.c_bool]
        self.ch347dll.CH347Jtag_IoScanT.restype = ctypes.c_bool

        # Set the function argument types and return type for CH347Jtag_WriteRead
        self.ch347dll.CH347Jtag_WriteRead.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong, ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong), ctypes.c_void_p]
        self.ch347dll.CH347Jtag_WriteRead.restype = ctypes.c_bool

    def list_devices(self):
        # List all devices
        num_devices = 0
        dev_info = mDeviceInforS()
        for i in range(self.MAX_DEVICE_NUMBER):
            if self.ch347dll.CH347OpenDevice(i) == self.INVALID_HANDLE_VALUE:
                break
            num_devices += 1
            if self.ch347dll.CH347GetDeviceInfor(i, ctypes.byref(dev_info)):
                for field_name, _ in dev_info._fields_:
                    value = getattr(dev_info, field_name)
                    print(f"{field_name}: {value}")
            print("-" * 40)
            self.ch347dll.CH347CloseDevice(i)
        print(f"Number of devices: {num_devices}")
        return num_devices

    def open_device(self):
        """
        Open USB device.

        Returns:
            int: Handle to the opened device if successful, None otherwise.
        """
        handle = self.ch347dll.CH347OpenDevice(self.device_index)
        if handle != self.INVALID_HANDLE_VALUE:
            return handle
        else:
            return None
        
    def close_device(self):
        """
        Close USB device.

        Returns:
            bool: True if successful, False otherwise.
        """
        result = self.ch347dll.CH347CloseDevice(self.device_index)
        return result
    
    def write_data(self, buffer: ctypes.c_void_p, length: ctypes.c_ulong) -> bool:
        result = self.ch347dll.CH347WriteData(self.device_index, buffer, ctypes.byref(ctypes.c_ulong(length)))
        return result

    def get_device_info(self):
        """
        Retrieve the information of the connected device.

        This method uses the device index to call the CH347 DLL and obtain the device's details.

        Returns:
            DeviceInfo: An instance of DeviceInfo with the device details if successful.
            None: If the retrieval fails.
        """
        dev_info = mDeviceInforS()
        result = self.ch347dll.CH347GetDeviceInfor(
            self.device_index, ctypes.byref(dev_info)
        )
        if result:
            return dev_info
        else:
            return None
        
    def jtag_init(self, clock: int) -> bool:
        clock_index = clock
        result = self.ch347dll.CH347Jtag_INIT(self.device_index, clock_index)
        return result

    def jtag_switch_tap(self, state: ctypes.c_ubyte) -> bool:
        tap_state = state
        result = self.ch347dll.CH347Jtag_SwitchTapStateEx(self.device_index, tap_state)
        return result
    
    def jtag_tms_shift(self, tmsvalue: ctypes.c_ubyte, step: int, skip: int):
        result = self.ch347dll.CH347Jtag_TmsChange(self.device_index, ctypes.byref(ctypes.c_ubyte(tmsvalue)), step, skip)
        return result

    def jtag_write_read_fast(self, is_dr: bool, w_len: ctypes.c_ulong, w_buf: ctypes.c_void_p, r_len: int, r_buf: ctypes.c_void_p) -> bool:
        result = self.ch347dll.CH347Jtag_WriteRead_Fast(self.device_index, is_dr, w_len, w_buf, ctypes.byref(ctypes.c_ulong(r_len)), r_buf)
        return result
    
    def jtag_ioscan_t(self, data_buffer: ctypes.c_void_p, data_bits: ctypes.c_ulong, is_read: bool, is_last_packge: bool) -> bool:
        result = self.ch347dll.CH347Jtag_IoScanT(self.device_index, data_buffer, data_bits, is_read, is_last_packge)
        return result
    
    def jtag_ioscan(self, data_buffer: ctypes.c_void_p, data_bits: ctypes.c_ulong, is_read: bool) -> bool:
        result = self.ch347dll.CH347Jtag_IoScan(self.device_index, data_buffer, data_bits, is_read)
        return result