import yaml

import click

from clickclick import AliasedGroup, Action

from zmon_cli.cmds.cli import cli
from zmon_cli.output import dump_yaml
from zmon_cli.client import ZmonArgumentError


@cli.group('alert-definitions', cls=AliasedGroup)
@click.pass_context
def alert_definitions(ctx):
    """Manage alert definitions"""
    pass


@alert_definitions.command('init')
@click.argument('yaml_file', type=click.File('wb'))
def init(yaml_file):
    """Initialize a new alert definition YAML file"""
    name = click.prompt('Alert name', default='Example Alert')
    check_id = click.prompt('Check ID')
    team = click.prompt('(Responsible-) Team', default='Example Team')

    data = {
        'check_definition_id': check_id,
        'id': '',
        'name': name,
        'description': 'Example Alert Description',
        'team': team,
        'responsible_team': team,
        'condition': '>100',
        'entities': '',
        'entities_exclude': '',
        'status': 'ACTIVE',
        'priority': 2,
        'tags': '',
        'parent_id': '',
        'parameters': '',
    }

    yaml_file.write(dump_yaml(data).encode('utf-8'))


@alert_definitions.command('get')
@click.argument('alert_id', type=int)
@click.pass_context
def get_alert_definition(ctx, alert_id):
    """Get a single alert definition"""
    with Action('Retrieving alert definitions ...'):
        alert = ctx.obj.client.get_alert_definition(alert_id)

        keys = list(alert.keys())
        for k in keys:
            if alert[k] is None:
                del alert[k]

        print(dump_yaml(alert))


@alert_definitions.command('create')
@click.argument('yaml_file', type=click.File('rb'))
@click.pass_context
def create_alert_definition(ctx, yaml_file):
    """Create a single alert definition"""
    alert = yaml.safe_load(yaml_file)

    alert['last_modified_by'] = ctx.obj.config.get('user', 'unknown')

    with Action('Creating alert definition ...'):
        try:
            new_alert = ctx.obj.client.create_alert_definition(alert)

            print(ctx.obj.client.alert_details_url(new_alert))
        except ZmonArgumentError as e:
            click.UsageError(str(e))


@alert_definitions.command('update')
@click.argument('yaml_file', type=click.File('rb'))
@click.pass_context
def update_alert_definition(ctx, yaml_file):
    """Update a single alert definition"""
    alert = yaml.safe_load(yaml_file)

    alert['last_modified_by'] = ctx.obj.config.get('user', 'unknown')

    with Action('Updating alert definition ...'):
        try:
            ctx.obj.client.update_alert_definition(alert)
            print(ctx.obj.client.alert_details_url(alert))
        except ZmonArgumentError as e:
            click.UsageError(str(e))
