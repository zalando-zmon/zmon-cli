import os
import json
import yaml

import click

from clickclick import AliasedGroup, Action, action, error, ok

from zmon_cli.cmds.cli import cli, output_option
from zmon_cli.output import dump_yaml, render_entities


########################################################################################################################
# ENTITIES
########################################################################################################################

@cli.group('entities', cls=AliasedGroup, invoke_without_command=True)
@click.pass_context
@output_option
def entities(ctx, output):
    """Manage entities"""
    if not ctx.invoked_subcommand:
        entities = ctx.obj.client.get_entities()
        render_entities(entities, output)


@entities.command('get')
@click.argument('entity_id')
@click.pass_context
def get_entity(ctx, entity_id):
    """Get a single entity by ID"""
    with Action('Retrieving entity {} ...'.format(entity_id), nl=True):
        entity = ctx.obj.client.get_entity(entity_id)

        click.secho(dump_yaml(entity), nl=True)


@entities.command('filter')
@click.argument('key')
@click.argument('value')
@click.pass_context
@output_option
def filter_entities(ctx, key, value, output):
    '''List entities filtered by a certain key'''
    entities = ctx.obj.client.get_entities(query={key: value})
    render_entities(entities, output)


@entities.command('push')
@click.argument('entity')
@click.pass_context
def push_entity(ctx, entity):
    """Push one or more entities"""
    if (entity.endswith('.json') or entity.endswith('.yaml')) and os.path.exists(entity):
        with open(entity, 'rb') as fd:
            data = yaml.safe_load(fd)
    else:
        data = json.loads(entity)

    if not isinstance(data, list):
        data = [data]

    with Action('Creating new entities ...'):
        for e in data:
            action('\nCreating entity {} ...'.format(e['id']))
            try:
                ctx.obj.client.add_entity(e)
                ok()
            except Exception as e:
                error('Exception while adding entity: {}'.format(str(e)))


@entities.command('delete')
@click.argument('entity_id')
@click.pass_context
def delete_entity(ctx, entity_id):
    """Delete a single entity by ID"""

    with Action('Deleting entity {} ...'.format(entity_id)):
        deleted = ctx.obj.client.delete_entity(entity_id)
        if not deleted:
            error('Delete failed')
