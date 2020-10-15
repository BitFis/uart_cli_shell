import pexpect
import pexpect.popen_spawn
import time
import re
import traceback

from typing import TextIO, Callable

from enum import Enum
from cmd import Cmd

class JoinerMethod(Enum):
    AE = 'joiner startae'
    NMKP = 'joiner startnmkp'
    DEFAULT = 'joiner start'

class SerialConnectionError(Exception):
    pass

class DeviceCommandFailed(Exception):
    def __init__(self, cmd:str, error):
        super(DeviceCommandFailed, self).__init__('"{}" command failed: {}'.format(cmd, error))
        self.error = error
        self.cmd = cmd

class JoinerTimeoutException(DeviceCommandFailed):
    pass

class SimpleDevicePrompt(Cmd):
    prompt = '> '

    def __init__(self,
        command_callback: Callable[[str], bool],
        empty_callback: Callable[[], bool],
        verbose=False
        ):
        super(SimpleDevicePrompt, self).__init__()
        self.command_callback = command_callback
        self.empty_callback = empty_callback

    def do_quit(self, arg):
        'exit'
        return True

    def do_exit(self, arg):
        'exit'
        return True

    def do_help(self, arg):
        if(arg == ''):
            print('exit,quit    closes connection')
        self.default("help " + arg)

    def emptyline(self):
        return self.empty_callback()

    def default(self, line):
        try:
            return self.command_callback(line)
        except (DeviceCommandFailed, JoinerTimeoutException) as err:
            print(str(err.error))
        except SerialConnectionError as err:
            print(err)
            return True

class ScreenEndpoint:
    def __init__(self,
        screenArgs: str = "", #> default define screenArgs
        commandList='help', #> Command to show available commands
        screenEnv: object = None, #> define env variable passed to command
        successRegex:[str] = ['Done'], #> Set Success string / can be multiple as list
        errorRegex:[str] = ['Error .+:.*\n'], #> Set Error string / can be multiple as list
        defaultTimeoutSeconds = 2, #> set default timeout for function in sec.
        _custom_connect = "screen {screenArgs}", #> customize process call
        verbose = False, #> show verbously hints and everything
        quite=False, #> define if any output of device is hidden
        ):
        self.verbose = verbose
        self.success_regex = successRegex
        self.error_regex = errorRegex
        self.defaultTimeout = defaultTimeoutSeconds
        self.cmd = _custom_connect.format(screenArgs = screenArgs)
        self.screen_env = screenEnv
        self.command_list = commandList

        if(verbose):
            print("Start command: '{}'".format(self.cmd))

    @staticmethod
    def version() -> str:
        return "v0.0.1"

    def open_connection(self):
        self.child = pexpect.spawn(self.cmd, env=self.screen_env)
        time.sleep(0.1)
        self.test_connected()

    def test_connected(self):
        try:
            # test connection
            self.child.sendline()
            res1 = self.child.expect(['>'], timeout=self.defaultTimeout)
            self.child.sendline()
            res2 = self.child.expect(['>'], timeout=self.defaultTimeout)

            if(not self.child.isalive()):
                error = str(self.child.before)

                # cleanup output, removing special characters
                error = re.sub(r'(\[[^A-Z^a-z]*.|\\x[a-f0-9]{2})', '', error)
                # remove binary info
                error = re.sub(r'(^b\"(=\(B)?|\"$)', '', error)
                # readd new line
                error = re.sub(r'((\\r)?\\n)', '\n', error)

                raise SerialConnectionError('{}\n"{}" failed'.format(error, self.cmd))

        except pexpect.exceptions.EOF:
            raise SerialConnectionError('"{}" stopped, maybe its somewhere else in use?'.format(self.cmd))
        except pexpect.exceptions.TIMEOUT:
            raise SerialConnectionError('"{}" timedout, screen timedout?'.format(self.cmd))

    def close_connection(self):
        # check if screen
        if(self.cmd.startswith('screen')):
            self.child.sendcontrol('a')
            self.child.sendline(':quit')
        else:
            self.child.sendintr()

        # expect it to close
        self.child.expect(pexpect.EOF, timeout=4)

    def send_command(self, cmd: str, io: TextIO = None):
        self.child.sendline(cmd)
        try:
            result = self.child.expect(self.success_regex + self.error_regex, timeout=2)
        except pexpect.exceptions.TIMEOUT as ex:
            self._print(io, cmd=cmd)
            if(self.verbose):
                traceback.print_exc()

            if(io == None):
                print("call has timedout")
            else:
                io.write("call has timedout")
            return

        if(result >= self.success_regex.__len__()):
            raise DeviceCommandFailed(cmd, self._cleanup_string(self.child.after))

        self._print(io, cmd=cmd)

    def shell(self):
        SimpleDevicePrompt(
            command_callback=lambda cmd: self.send_command(str(cmd)),
            empty_callback=lambda: self.test_connected()
        ).cmdloop()

    def _print(self, io: TextIO = None, cmd:str = ""):
        before = self._cleanup_string(self.child.before)
        # remove cmd if it is reoccuring
        before = re.sub(r'^(\n *)*>? *'+cmd+'(\n *)*', '', str(before))
        after = self._cleanup_string(self.child.after)
        if(io == None):
            print(before, after)
        else:
            io.write(before)
            io.write(after)

    def __enter__(self):
            #ttysetattr etc goes here before opening and returning the file object
            self.open_connection()
            return self

    def __exit__(self, type, value, traceback):
            self.close_connection()

    def _cleanup_string(self, string: str):
        # setup new lines
        string = re.sub(r'(\\r)?\\n', '\n', str(string))
        # remove start end of byte info
        return re.sub(r'(^b(\'|")|(\'|")$)', '', string)

class Device(ScreenEndpoint):
    '''
    Start device
    @param usbPort device com
    '''
    def __init__(self,
            usbPort: str,
            baudrate: int = 115200,
            _custom_connect = " {usbPort} {baudrate}",
            verbose = False
        ):
        super(Device, self).__init__(
            screenArgs=_custom_connect.format(usbPort = usbPort, baudrate = baudrate),
            verbose=verbose
        )

    '''
    process line read from device
    '''
    def process(self, line: str):
        pass
