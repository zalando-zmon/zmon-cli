import yaml

import click

from clickclick import AliasedGroup, Action

from zmon_cli.cmds.command import cli, get_client
from zmon_cli.output import dump_yaml
from zmon_cli.client import ZmonArgumentError


@cli.group('grafana', cls=AliasedGroup)
@click.pass_obj
def grafana(obj):
    """Manage Grafana dashboards"""
    pass


@grafana.command('get')
@click.argument('dashboard_id', type=click.STRING)
@click.pass_obj
def grafana_get(obj, dashboard_id):
    """Get ZMON grafana dashboard"""
    client = get_client(obj.config)

    with Action('Retrieving grafana dashboard ...', nl=True):
        dashboard = client.get_grafana_dashboard(dashboard_id)
        print(dump_yaml(dashboard))


@grafana.command('update')
@click.argument('yaml_file', type=click.File('rb'))
@click.pass_obj
def grafana_update(obj, yaml_file):
    """Create/Update a single ZMON dashboard"""
    dashboard = yaml.safe_load(yaml_file)

    title = dashboard.get('dashboard', {}).get('title', '')

    client = get_client(obj.config)

    with Action('Updating dashboard {} ...'.format(title), nl=True) as act:
        try:
            g = client.update_grafana_dashboard(dashboard)
            print(g)
        except ZmonArgumentError as e:
            act.error(e)
