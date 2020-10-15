#!/usr/bin/env ./.ot-test-env/bin/python3
'''
Simple to check connection to an open screen and mock screen send / receive keys
'''
import unittest
from device import ScreenEndpoint

class TestSerialConnectionScreenMocked(unittest.TestCase):

    screen_endpoint_name = "test_screen"
    custom_screen_endpoint = "-S {} -L /bin/sh".format(screen_endpoint_name)
    default_args = {
        'screenArgs': custom_screen_endpoint,
        'screenEnv': {'PS1':'> ', 'TERM':'vt100'},
        'defaultTimeoutSeconds': 0.1
    }

    def test_connect(self):
        with ScreenEndpoint(**self.default_args) as dev:
            pass

    def test_send_successful_command(self):
        with ScreenEndpoint(**self.default_args) as dev:
            dev.send_command('echo Done')

if __name__ == '__main__':
    unittest.main()
