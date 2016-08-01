import yaml

import click

from clickclick import AliasedGroup, Action, ok

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
        'condition': '>100',
        'description': 'Example Alert Description',
        'entities': [],
        'entities_exclude': [],
        'id': '',
        'name': name,
        'parameters': {},
        'parent_id': '',
        'priority': 2,
        'responsible_team': team,
        'status': 'ACTIVE',
        'tags': [],
        'team': team,
        'template': False,
    }

    yaml_file.write(dump_yaml(data).encode('utf-8'))
    ok()


@alert_definitions.command('get')
@click.argument('alert_id', type=int)
@click.pass_context
def get_alert_definition(ctx, alert_id):
    """Get a single alert definition"""
    with Action('Retrieving alert definition ...', nl=True):
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

    with Action('Creating alert definition ...', nl=True) as act:
        try:
            new_alert = ctx.obj.client.create_alert_definition(alert)

            print(ctx.obj.client.alert_details_url(new_alert))
        except ZmonArgumentError as e:
            act.error('Invalid alert definition')
            act.error(str(e))


@alert_definitions.command('update')
@click.argument('yaml_file', type=click.File('rb'))
@click.pass_context
def update_alert_definition(ctx, yaml_file):
    """Update a single alert definition"""
    alert = yaml.safe_load(yaml_file)

    alert['last_modified_by'] = ctx.obj.config.get('user', 'unknown')

    with Action('Updating alert definition ...', nl=True) as act:
        try:
            ctx.obj.client.update_alert_definition(alert)
            print(ctx.obj.client.alert_details_url(alert))
        except ZmonArgumentError as e:
            act.error('Invalid alert definition')
            act.error(str(e))


@alert_definitions.command('delete')
@click.argument('alert_id', type=int)
@click.pass_context
def delete_alert_definition(ctx, alert_id):
    """Get a single alert definition"""
    with Action('Deleting alert definition ...'):
        ctx.obj.client.delete_alert_definition(alert_id)
