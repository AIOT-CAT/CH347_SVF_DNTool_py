import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from py_ch347_libarary import *

def test_jtag():
    # Try to open a device
    try:
        device = ch347()
        device.list_devices()
        assert device is not None, "Failed to create device instance"

        # Open the first available device
        result = device.open_device()
        assert result, "Failed to open device"

        # Get device information
        device_info = device.get_device_info()

        result = device.jtag_init(3)
        assert result, "Failed to init device"

        result = device.jtag_switch_tap(0)
        assert result, "Failed to change tap states"

        idcode = (ctypes.c_ubyte * 4)()
        write_buf = (ctypes.c_ubyte * 4)()
        write_length = 0
        read_length = 4

        result = device.jtag_write_read_fast(True, write_length, write_buf, read_length, idcode)
        assert result, "Failed to transfer the jtag data"

        for i in range(len(idcode)):
            print(f"idcode[{i}] = 0x{idcode[i]:02x}")

        # Close the device
        device.close_device()

    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")

if __name__ == "__main__":
    test_jtag()