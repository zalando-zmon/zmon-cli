import yaml

import click

from clickclick import AliasedGroup, Action, ok

from zmon_cli.cmds.cli import cli
from zmon_cli.output import dump_yaml


@cli.group('dashboard', cls=AliasedGroup)
@click.pass_context
def dashboard(ctx):
    """Manage ZMON dashboards"""
    pass


@dashboard.command('init')
@click.argument('yaml_file', type=click.File('wb'))
@click.pass_context
def init(ctx, yaml_file):
    """Initialize a new dashboard YAML file"""
    name = click.prompt('Dashboard name', default='Example dashboard')
    alert_teams = click.prompt('Alert Teams (comma separated)', default='Team1, Team2')

    user = ctx.obj.config.get('user', 'unknown')

    data = {
        'id': '',
        'name': name,
        'last_modified_by': user,
        'alert_teams': [t.strip() for t in alert_teams.split(',')],
        'tags': [],
        'view_mode': 'FULL',
        'shared_teams': [],
        'widget_configuration': [],
    }

    yaml_file.write(dump_yaml(data).encode('utf-8'))
    ok()


@dashboard.command('get')
@click.argument("dashboard_id", type=int)
@click.pass_context
def dashboard_get(ctx, dashboard_id):
    """Get ZMON dashboard"""
    with Action('Retrieving dashboard ...', nl=True):
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
    with Action(msg, nl=True):
        dash_id = ctx.obj.client.update_dashboard(dashboard)
        print(dash_id)
