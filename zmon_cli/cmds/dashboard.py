import yaml

import click

from clickclick import AliasedGroup, Action

from zmon_cli.cmds.cli import cli
from zmon_cli.output import dump_yaml


@cli.group('dashboard', cls=AliasedGroup)
@click.pass_context
def dashboard(ctx):
    """Manage ZMON dashboards"""
    pass


@dashboard.command('get')
@click.argument("dashboard_id", type=int)
@click.pass_context
def dashboard_get(ctx, dashboard_id):
    """Get ZMON dashboard"""
    with Action('Retrieving dashboard ...'):
        dashboard = ctx.obj.client.get_dashboard(dashboard_id)
        print(dump_yaml(dashboard))


@dashboard.command('update')
@click.argument('yaml_file', type=click.Path(exists=True))
@click.pass_context
def dashboard_update(ctx, yaml_file):
    """Create/Update a single ZMON dashboard"""
    dashboard = {}
    with open(yaml_file, 'rb') as f:
        dashboard = yaml.safe_load(f)

    msg = 'Creating new dashboard ...'
    if 'id' in dashboard:
        msg = 'Updating dashboard {} ...'.format(dashboard.get('id'))

    # TODO: check return value from API!
    with Action(msg):
        ctx.obj.client.update_dashboard(dashboard)
