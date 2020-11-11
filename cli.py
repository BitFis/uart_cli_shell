#!/usr/bin/env ./.ot-test-env/bin/python3
'''
Small cli application which enables
access to a device connected over UART
per usb
'''

import click, os, io, subprocess
from device import Device, JoinerMethod, SerialConnectionError, DeviceCommandFailed
from contextlib import contextmanager

DEFAULT_DEVICE_PATH=os.environ.get('DEFAULT_DEVICE_PATH', False)
DEFAULT_IMAGE=os.environ.get('DEFAULT_IMAGE', False)

if(not DEFAULT_IMAGE): raise "Set 'DEFAULT_IMAGE' env variable"
if(not DEFAULT_DEVICE_PATH): raise "Set 'DEFAULT_DEVICE_PATH' env variable"

'''
Creates a Device connection object
to work with
'''
@contextmanager
def open_device_connection(ctx: object):
    port = ctx.obj['port']
    simulation = ctx.obj["simulation"]
    custom = ctx.obj["custom"]

    default_args = {
        'log': ctx.obj['log'],
        'verbose': ctx.obj['verbose'],
        'timeout': ctx.obj['timeout']
    }

    if(custom):
        dev = Device(0, _custom_connect="{log} /bin/sh -c \""+custom+"\"", **default_args)
    elif(port):
        dev = Device(port, **default_args)
    else:
        console_path = os.path.abspath("{}/console.sh".format(DEFAULT_DEVICE_PATH))
        dev = Device(console_path, simulation, **default_args)

    try:
        with dev:
            yield dev
    except (SerialConnectionError, DeviceCommandFailed) as err:
        if(ctx.obj['verbose']):
            raise err
        raise click.ClickException(str(err))

class DefaultCommandGroup(click.Group):
    """allow a default command for a group"""

    def resolve_command(self, ctx, args):
        try:
            # test if the command parses
            return super(DefaultCommandGroup, self).resolve_command(ctx, args)
        except click.UsageError:
            # command did not parse, assume it is the default command
            args.insert(0, "send")
            return super(DefaultCommandGroup, self).resolve_command(ctx, args)

@click.group(cls=DefaultCommandGroup)
@click.option('-p', '--port', default=False,
              help='Define the usb serial port of the device aka. /dev/ttyACM0')
@click.option('-s', '--simulation', default=2, type=int,
              help='Define the dockerized device endpoint id to access')
@click.option('-c', '--custom', default=False, type=str,
              help='Define a custom way of starting the endpoint (like binary file), ! will always overwrite -s and -p')
@click.option('-v', '--verbose', default=False, is_flag=True,
              help='set verbose mode, output all device logs')
@click.option('-t', '--timeout', default=2, type=float,
              help='Set default timeout for command in sec.')
@click.option('-l', '--log', default=False, is_flag=True,
              help='Log interaction to file')
@click.pass_context
def cli(ctx, port, simulation, verbose, custom, log, timeout):
    ctx.obj['port'] = port
    ctx.obj["simulation"] = simulation
    ctx.obj["custom"] = custom
    ctx.obj['verbose'] = verbose
    ctx.obj['log'] = log
    ctx.obj['timeout'] = timeout

    if(port and simulation != 2):
        raise click.ClickException("UART device and Docker device can not be accessed simultaneously!")

    if(not (port or simulation)):
        raise click.ClickException("Eather UART device and Docker device needs to be defined for access!")

@cli.command(help = "Enable tracing logs [Currently only simulated device]")
@click.pass_context
def version(ctx):
    print(str(Device.version()))

def trace_simulation(ctx):
    sim_id = ctx.obj["simulation"]

    click.echo('Tracing device {}, CTRL-C to exit trace'.format(sim_id))

    trace_script = "{script_dir}/{rel_path}/trace.sh".format(script_dir = os.path.dirname(os.path.realpath(__file__)), rel_path = DEFAULT_DEVICE_PATH)

    subprocess.run([trace_script, str(sim_id)],
                     stdout=click.get_binary_stream('stdout'),
                     stdin=click.get_binary_stream('stdin'),
                     stderr=click.get_binary_stream('stderr'))

@cli.command(help = "Enable tracing logs [Currently only simulated device]")
@click.pass_context
def trace(ctx):
    if(ctx.obj["port"] or ctx.obj["custom"]):
        raise click.ClickException("Only possible for dockerized simulated device (--simulation)")

    trace_simulation(ctx)

@cli.command(help = "Will start the dockerized device")
@click.pass_context
def start(ctx, dockerimage = DEFAULT_IMAGE):
    """
    Will start a dockerized device.
    The --simulation arg represents the Openthread ID / communication ID in simulated network
    """
    if(ctx.obj["port"]):
        raise click.ClickException("Only possible for dockerized simulated device (--simulation)")
    sim_id = ctx.obj["simulation"]

    click.echo('Starting device with id "{}" and docker image "{}"'.format(sim_id, dockerimage))

    start_script = "{script_dir}/{rel_path}/start.sh".format(script_dir = os.path.dirname(os.path.realpath(__file__)), rel_path = DEFAULT_DEVICE_PATH)

    subprocess.run([start_script, str(sim_id), dockerimage],
                     stdout=click.get_binary_stream('stdout'), stdin=click.get_binary_stream('stdin'))

@cli.command(help = "Will stop the dockerized device")
@click.pass_context
def stop(ctx):
    """Will stop the dockerized device

    """
    if(ctx.obj["port"]):
        raise click.ClickException("Only possible for dockerized simulated device (--simulation)")
    sim_id = ctx.obj["simulation"]

    click.echo('Try to stop dockerized device with id "{}"'.format(sim_id))

    stop_script = "{script_dir}/{rel_path}/stop.sh".format(script_dir = os.path.dirname(os.path.realpath(__file__)), rel_path = DEFAULT_DEVICE_PATH)

    subprocess.run([stop_script, str(sim_id)],
                     stdout=click.get_binary_stream('stdout'),
                     stdin=click.get_binary_stream('stdin'),
                     stderr=click.get_binary_stream('stderr'))

@cli.command(help = "Will start a shell to the device")
@click.pass_context
def shell(ctx):
    """Connect the device an open a shell.

    """
    click.echo('Starting shell connection')
    with open_device_connection(ctx) as dev:
        dev.shell()
        print('Done')

@cli.command(help = "Send a command to the device (default)")
@click.argument('command', nargs=-1)
@click.pass_context
def send(ctx, command):
    """Print COMMAND.

    COMMAND to execute.
    """
    command = ' '.join(command)

    click.echo('Sending command "{}"'.format(command))
    with open_device_connection(ctx) as dev:
        dev.send_command(command)

if __name__ == '__main__':
    cli(obj={}, prog_name=os.getenv('_CLI_PROG_NAME', default=None))
