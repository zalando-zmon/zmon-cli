import yaml

import click

from clickclick import AliasedGroup, Action, ok

from zmon_cli.cmds.command import cli, get_client
from zmon_cli.output import dump_yaml


@cli.group('dashboard', cls=AliasedGroup)
@click.pass_obj
def dashboard(obj):
    """Manage ZMON dashboards"""
    pass


@dashboard.command('init')
@click.argument('yaml_file', type=click.File('wb'))
@click.pass_obj
def init(obj, yaml_file):
    """Initialize a new dashboard YAML file"""
    name = click.prompt('Dashboard name', default='Example dashboard')
    alert_teams = click.prompt('Alert Teams (comma separated)', default='Team1, Team2')

    user = obj.config.get('user', 'unknown')

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
@click.pass_obj
def dashboard_get(obj, dashboard_id):
    """Get ZMON dashboard"""
    client = get_client(obj.config)
    with Action('Retrieving dashboard ...', nl=True):
        dashboard = client.get_dashboard(dashboard_id)
        print(dump_yaml(dashboard))


@dashboard.command('update')
@click.argument('yaml_file', type=click.Path(exists=True))
@click.pass_obj
def dashboard_update(obj, yaml_file):
    """Create/Update a single ZMON dashboard"""
    client = get_client(obj.config)
    dashboard = {}
    with open(yaml_file, 'rb') as f:
        dashboard = yaml.safe_load(f)

    msg = 'Creating new dashboard ...'
    if 'id' in dashboard:
        msg = 'Updating dashboard {} ...'.format(dashboard.get('id'))

    # TODO: check return value from API!
    with Action(msg, nl=True):
        dash_id = client.update_dashboard(dashboard)
        print(dash_id)
