import yaml

import click

from clickclick import AliasedGroup, Action, error

from zmon_cli.cmds.cli import cli
from zmon_cli.output import dump_yaml
from zmon_cli.client import ZmonArgumentError


@cli.group('check-definitions', cls=AliasedGroup)
@click.pass_context
def check_definitions(ctx):
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


@check_definitions.command('get')
@click.argument('check_id', type=int)
@click.pass_context
def get_check_definition(ctx, check_id):
    """Get a single check definition"""
    with Action('Retrieving check definition ...'):
        check = ctx.obj.client.get_check_definition(check_id)

        keys = list(check.keys())
        for k in keys:
            if check[k] is None:
                del check[k]

        print(dump_yaml(check))


@check_definitions.command('update')
@click.argument('yaml_file', type=click.File('rb'))
@click.pass_context
def update(ctx, yaml_file):
    """Update a single check definition"""
    check = yaml.safe_load(yaml_file)

    check['last_modified_by'] = ctx.obj.get('user', 'unknown')

    with Action('Updating check definition ...'):
        try:
            check = ctx.obj.client.update_check_definition(check)
            print(ctx.obj.client.check_definition_url(check))
        except ZmonArgumentError as e:
            click.UsageError(str(e))


@check_definitions.command('delete')
@click.argument('check_id', type=int)
@click.pass_context
def delete_check_definition(ctx, check_id):
    """Delete an orphan check definition"""

    with Action('Deleting check {} ...'.format(check_id)):
        resp = ctx.obj.client.delete_check_definition(check_id)

        if not resp.ok:
            error(resp.text)
