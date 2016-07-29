import yaml

import click

from clickclick import AliasedGroup, Action

from zmon_cli.cmds.cli import cli
from zmon_cli.output import dump_yaml
from zmon_cli.client import ZmonArgumentError


@cli.group('grafana', cls=AliasedGroup)
@click.pass_context
def grafana(ctx):
    """Manage Grafana dashboards"""
    pass


@grafana.command('get')
@click.argument('dashboard_id', type=click.STRING)
@click.pass_context
def grafana_get(ctx, dashboard_id):
    """Get ZMON grafana dashboard"""
    with Action('Retrieving grafana dashboard ...'):
        dashboard = ctx.obj.client.get_grafana_dashboard(dashboard_id)
        print(dump_yaml(dashboard))


@grafana.command('update')
@click.argument('yaml_file', type=click.File('rb'))
@click.pass_context
def grafana_update(ctx, yaml_file):
    """Create/Update a single ZMON dashboard"""
    dashboard = yaml.safe_load(yaml_file)

    title = dashboard.get('dashboard', {}).get('title', '')

    with Action('Updating dashboard {} ...'.format(title)):
        try:
            ctx.obj.client.update_grafana_dashboard(dashboard)
        except ZmonArgumentError as e:
            click.UsageError(str(e))
