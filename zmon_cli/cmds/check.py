import yaml

import click

from clickclick import AliasedGroup, Action, ok

from zmon_cli.cmds.command import cli, get_client, yaml_output_option, pretty_json, output_option
from zmon_cli.output import dump_yaml, Output, render_checks
from zmon_cli.client import ZmonArgumentError


@cli.group('check-definitions', cls=AliasedGroup)
@click.pass_obj
def check_definitions(obj):
    """Manage check definitions"""
    pass


@check_definitions.command('init')
@click.argument('yaml_file', type=click.File('wb'))
def init(yaml_file):
    """Initialize a new check definition YAML file"""
    # NOTE: sorted like FIELD_SORT_INDEX
    name = click.prompt('Check definition name', default='Example Check')
    owning_team = click.prompt('Team owning this check definition (i.e. your team)', default='Example Team')

    data = {
        'name': name,
        'owning_team': owning_team,
        'description': "Example ZMON check definition which returns a HTTP status code.\n" +
                       "You can write multiple lines here, including unicode ☺",
        'command': "# GET request on example.org and return HTTP status code\n" +
                   "http('http://example.org/', timeout=5).code()",
        'interval': 60,
        'entities': [{'type': 'GLOBAL'}],
        'status': 'ACTIVE'
    }

    yaml_file.write(dump_yaml(data).encode('utf-8'))
    ok()


@check_definitions.command('get')
@click.argument('check_id', type=int)
@click.pass_obj
@yaml_output_option
@pretty_json
def get_check_definition(obj, check_id, output, pretty):
    """Get a single check definition"""
    client = get_client(obj.config)

    with Output('Retrieving check definition ...', nl=True, output=output, pretty_json=pretty) as act:
        check = client.get_check_definition(check_id)

        keys = list(check.keys())
        for k in keys:
            if check[k] is None:
                del check[k]

        act.echo(check)


@check_definitions.command('list')
@click.pass_obj
@output_option
@pretty_json
def list_check_definitions(obj, output, pretty):
    """List all active check definitions"""
    client = get_client(obj.config)

    with Output('Retrieving active check definitions ...', nl=True, output=output, pretty_json=pretty,
                printer=render_checks) as act:
        checks = client.get_check_definitions()

        for check in checks:
            check['link'] = client.check_definition_url(check)

        act.echo(checks)


@check_definitions.command('filter')
@click.argument('field')
@click.argument('value')
@click.pass_obj
@output_option
@pretty_json
def filter_check_definitions(obj, field, value, output, pretty):
    """Filter active check definitions"""
    client = get_client(obj.config)

    with Output('Retrieving and filtering check definitions ...', nl=True, output=output, pretty_json=pretty,
                printer=render_checks) as act:
        checks = client.get_check_definitions()

        filtered = [check for check in checks if check.get(field) == value]

        for check in filtered:
            check['link'] = client.check_definition_url(check)

        act.echo(filtered)


@check_definitions.command('update')
@click.argument('yaml_file', type=click.File('rb'))
@click.option('--skip-validation', is_flag=True, help='Skip check command syntax validation.')
@click.pass_obj
def update(obj, yaml_file, skip_validation):
    """Update a single check definition"""
    check = yaml.safe_load(yaml_file)

    check['last_modified_by'] = obj.get('user', 'unknown')

    client = get_client(obj.config)

    with Action('Updating check definition ...', nl=True) as act:
        try:
            check = client.update_check_definition(check, skip_validation=skip_validation)
            ok(client.check_definition_url(check))
        except ZmonArgumentError as e:
            act.error(str(e))


@check_definitions.command('delete')
@click.argument('check_id', type=int)
@click.pass_obj
def delete_check_definition(obj, check_id):
    """Delete an orphan check definition"""
    client = get_client(obj.config)

    with Action('Deleting check {} ...'.format(check_id)) as act:
        resp = client.delete_check_definition(check_id)

        if not resp.ok:
            act.error(resp.text)


@check_definitions.command('help')
@click.pass_context
def help(ctx):
    print(ctx.parent.get_help())
