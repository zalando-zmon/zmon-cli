import click
import logging
import os

from clickclick import AliasedGroup
from easydict import EasyDict

from zmon_cli import __version__

from zmon_cli.config import DEFAULT_CONFIG_FILE, DEFAULT_TIMEOUT
from zmon_cli.config import get_config_data, configure_logging, set_config_file

from zmon_cli.output import Output, render_status

from zmon_cli.client import Zmon


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

output_option = click.option('-o', '--output', type=click.Choice(['text', 'json', 'yaml']), default='text',
                             help='Use alternative output format')

yaml_output_option = click.option('-o', '--output', type=click.Choice(['text', 'json', 'yaml']), default='yaml',
                                  help='Use alternative output format. Default is YAML.')

pretty_json = click.option('--pretty', is_flag=True,
                           help='Pretty print JSON output. Ignored if output format is not JSON')


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo('ZMON CLI {}'.format(__version__))
    ctx.exit()


def get_client(config):
    verify = config.get('verify', True)

    if 'user' in config and 'password' in config:
        return Zmon(config['url'], username=config['user'], password=config['password'], verify=verify,
                    timeout=config.get('timeout', DEFAULT_TIMEOUT))
    elif os.environ.get('ZMON_TOKEN'):
        return Zmon(config['url'], token=os.environ.get('ZMON_TOKEN'), verify=verify,
                    timeout=config.get('timeout', DEFAULT_TIMEOUT))
    elif 'token' in config:
        return Zmon(config['url'], token=config['token'], verify=verify, timeout=config.get('timeout', DEFAULT_TIMEOUT))

    raise RuntimeError('Failed to intitialize ZMON client. Invalid configuration!')


########################################################################################################################
# CLI
########################################################################################################################

@click.group(cls=AliasedGroup, context_settings=CONTEXT_SETTINGS)
@click.option('-c', '--config-file', help='Use alternative config file', default=DEFAULT_CONFIG_FILE, metavar='PATH')
@click.option('-v', '--verbose', help='Verbose logging', is_flag=True)
@click.option('-V', '--version', is_flag=True, callback=print_version, expose_value=False, is_eager=True)
@click.option('-t', '--timeout', help='timeout for calls', default=DEFAULT_TIMEOUT)
@click.pass_context
def cli(ctx, config_file, verbose, timeout=DEFAULT_TIMEOUT):
    """
    ZMON command line interface
    """
    configure_logging(logging.DEBUG if verbose else logging.INFO)

    fn = os.path.expanduser(config_file)
    config = {}

    if os.path.exists(fn):
        config = get_config_data(config_file)

    config['timeout'] = timeout

    ctx.obj = EasyDict(config=config)


@cli.command()
@click.option('-c', '--config-file', help='Use alternative config file', default=DEFAULT_CONFIG_FILE, metavar='PATH')
@click.pass_obj
def configure(obj, config_file):
    """Configure ZMON URL and credentials"""
    set_config_file(config_file, obj.config.get('url'))


@cli.command()
@click.pass_obj
@output_option
@pretty_json
def status(obj, output, pretty):
    """Check ZMON system status"""
    client = get_client(obj.config)

    with Output('Retrieving status ...', printer=render_status, output=output, pretty_json=pretty) as act:
        status = client.status()
        act.echo(status)


@click.command()
@click.pass_context
def help(ctx):
    print(ctx.get_help())


cli.add_command(help)
