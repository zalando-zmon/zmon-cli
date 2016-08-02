import os
import json
import yaml

import click

from clickclick import AliasedGroup, Action, action, error

from zmon_cli.cmds.command import cli, get_client, output_option
from zmon_cli.output import dump_yaml, render_entities


########################################################################################################################
# ENTITIES
########################################################################################################################

@cli.group('entities', cls=AliasedGroup, invoke_without_command=True)
@click.pass_context
@output_option
def entities(ctx, output):
    """Manage entities"""
    client = get_client(ctx.obj.config)
    if not ctx.invoked_subcommand:
        entities = client.get_entities()
        render_entities(entities, output)


@entities.command('get')
@click.argument('entity_id')
@click.pass_obj
def get_entity(obj, entity_id):
    """Get a single entity by ID"""
    client = get_client(obj.config)
    with Action('Retrieving entity {} ...'.format(entity_id), nl=True):
        entity = client.get_entity(entity_id)

        click.secho(dump_yaml(entity), nl=True)


@entities.command('filter')
@click.argument('key')
@click.argument('value')
@click.pass_obj
@output_option
def filter_entities(obj, key, value, output):
    """List entities filtered by a certain key"""
    client = get_client(obj.config)
    with Action('Retrieving and filtering entities ...', nl=True):
        entities = client.get_entities(query={key: value})
        render_entities(entities, output)


@entities.command('push')
@click.argument('entity')
@click.pass_obj
def push_entity(obj, entity):
    """Push one or more entities"""
    client = get_client(obj.config)

    if (entity.endswith('.json') or entity.endswith('.yaml')) and os.path.exists(entity):
        with open(entity, 'rb') as fd:
            data = yaml.safe_load(fd)
    else:
        data = json.loads(entity)

    if not isinstance(data, list):
        data = [data]

    with Action('Creating new entities ...', nl=True):
        for e in data:
            action('\nCreating entity {} ...'.format(e['id']))
            try:
                client.add_entity(e)
            except Exception as e:
                error('Exception while adding entity: {}'.format(str(e)))


@entities.command('delete')
@click.argument('entity_id')
@click.pass_obj
def delete_entity(obj, entity_id):
    """Delete a single entity by ID"""
    client = get_client(obj.config)

    with Action('Deleting entity {} ...'.format(entity_id)) as act:
        deleted = client.delete_entity(entity_id)
        if not deleted:
            act.error('Delete failed')
