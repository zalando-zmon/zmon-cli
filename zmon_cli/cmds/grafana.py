import yaml

import click

from clickclick import AliasedGroup, Action, ok

from zmon_cli.cmds.command import cli, get_client, yaml_output_option, pretty_json
from zmon_cli.output import Output
from zmon_cli.client import ZmonArgumentError


@cli.group('grafana', cls=AliasedGroup)
@click.pass_obj
def grafana(obj):
    """Manage Grafana dashboards"""
    pass


@grafana.command('get')
@click.argument('dashboard_id', type=click.STRING)
@click.pass_obj
@yaml_output_option
@pretty_json
def grafana_get(obj, dashboard_id, output, pretty):
    """Get ZMON grafana dashboard"""
    client = get_client(obj.config)

    with Output('Retrieving grafana dashboard ...', nl=True, output=output, pretty_json=pretty) as act:
        dashboard = client.get_grafana_dashboard(dashboard_id)
        act.echo(dashboard)


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
            client.update_grafana_dashboard(dashboard)
            ok(client.grafana_dashboard_url(dashboard))
        except ZmonArgumentError as e:
            act.error(e)


@grafana.command('help')
@click.pass_context
def help(ctx):
    print(ctx.parent.get_help())
