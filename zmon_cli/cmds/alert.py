import json

import yaml

import click

from clickclick import AliasedGroup, Action, ok

from zmon_cli.cmds.command import cli, get_client, yaml_output_option, output_option, pretty_json
from zmon_cli.output import dump_yaml, Output, render_alerts
from zmon_cli.client import ZmonArgumentError


@cli.group('alert-definitions', cls=AliasedGroup)
@click.pass_obj
def alert_definitions(obj):
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
@click.pass_obj
@yaml_output_option
@pretty_json
def get_alert_definition(obj, alert_id, output, pretty):
    """Get a single alert definition"""
    client = get_client(obj.config)

    with Output('Retrieving alert definition ...', nl=True, output=output, pretty_json=pretty) as act:
        alert = client.get_alert_definition(alert_id)

        keys = list(alert.keys())
        for k in keys:
            if alert[k] is None:
                del alert[k]

        act.echo(alert)


@alert_definitions.command('list')
@click.pass_obj
@output_option
@pretty_json
def list_alert_definitions(obj, output, pretty):
    """List all active alert definitions"""
    client = get_client(obj.config)

    with Output('Retrieving active alert definitions ...', nl=True, output=output, pretty_json=pretty,
                printer=render_alerts) as act:
        alerts = client.get_alert_definitions()

        for alert in alerts:
            alert['link'] = client.alert_details_url(alert)

        act.echo(alerts)


@alert_definitions.command('filter')
@click.argument('field')
@click.argument('value')
@click.pass_obj
@output_option
@pretty_json
def filter_alert_definitions(obj, field, value, output, pretty):
    """Filter active alert definitions"""
    client = get_client(obj.config)

    with Output('Retrieving and filtering alert definitions ...', nl=True, output=output, pretty_json=pretty,
                printer=render_alerts) as act:
        alerts = client.get_alert_definitions()

        if field == 'check_definition_id':
            value = int(value)

        filtered = [alert for alert in alerts if alert.get(field) == value]

        for alert in filtered:
            alert['link'] = client.alert_details_url(alert)

        act.echo(filtered)


@alert_definitions.command('create')
@click.argument('yaml_file', type=click.File('rb'))
@click.pass_obj
def create_alert_definition(obj, yaml_file):
    """Create a single alert definition"""
    client = get_client(obj.config)

    alert = yaml.safe_load(yaml_file)

    alert['last_modified_by'] = obj.config.get('user', 'unknown')

    with Action('Creating alert definition ...', nl=True) as act:
        try:
            new_alert = client.create_alert_definition(alert)
            ok(client.alert_details_url(new_alert))
        except ZmonArgumentError as e:
            act.error(str(e))


@alert_definitions.command('update')
@click.argument('yaml_file', type=click.File('rb'))
@click.pass_obj
def update_alert_definition(obj, yaml_file):
    """Update a single alert definition"""
    alert = yaml.safe_load(yaml_file)

    alert['last_modified_by'] = obj.config.get('user', 'unknown')

    client = get_client(obj.config)

    with Action('Updating alert definition ...', nl=True) as act:
        try:
            # Workaround API inconsistency!
            if alert.get('parameters'):
                for k, v in alert['parameters'].items():
                    if type(v) is str:
                        alert['parameters'][k] = json.loads(v)

            client.update_alert_definition(alert)
            ok(client.alert_details_url(alert))
        except ZmonArgumentError as e:
            act.error(str(e))


@alert_definitions.command('delete')
@click.argument('alert_id', type=int)
@click.pass_obj
def delete_alert_definition(obj, alert_id):
    """Delete a single alert definition"""
    client = get_client(obj.config)

    with Action('Deleting alert definition ...'):
        client.delete_alert_definition(alert_id)


@alert_definitions.command('help')
@click.pass_context
def help(ctx):
    print(ctx.parent.get_help())
