import os
import json
import yaml

import requests
import click

from clickclick import AliasedGroup, Action, action, ok

from zmon_cli.cmds.command import cli, get_client, output_option, yaml_output_option, pretty_json
from zmon_cli.output import render_entities, Output, log_http_exception

from zmon_cli.client import ZmonArgumentError


########################################################################################################################
# ENTITIES
########################################################################################################################

@cli.group('entities', cls=AliasedGroup, invoke_without_command=True)
@click.pass_context
@output_option
@pretty_json
def entities(ctx, output, pretty):
    """Manage entities"""
    if not ctx.invoked_subcommand:
        client = get_client(ctx.obj.config)

        with Output('Retrieving all entities ...', output=output, printer=render_entities, pretty_json=pretty) as act:
            entities = client.get_entities()
            act.echo(entities)


@entities.command('get')
@click.argument('entity_id')
@click.pass_obj
@yaml_output_option
@pretty_json
def get_entity(obj, entity_id, output, pretty):
    """Get a single entity by ID"""
    client = get_client(obj.config)

    with Output('Retrieving entity {} ...'.format(entity_id), nl=True, output=output, pretty_json=pretty) as act:
        entity = client.get_entity(entity_id)
        act.echo(entity)


@entities.command('filter')
@click.argument('key')
@click.argument('value')
@click.pass_obj
@output_option
@pretty_json
def filter_entities(obj, key, value, output, pretty):
    """List entities filtered by a certain key"""
    client = get_client(obj.config)
    with Output('Retrieving and filtering entities ...', nl=True, output=output, printer=render_entities,
                pretty_json=pretty) as act:
        entities = client.get_entities(query={key: value})
        act.echo(entities)


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

    with Action('Creating new entities ...', nl=True) as act:
        for e in data:
            action('Creating entity {} ...'.format(e['id']))
            try:
                client.add_entity(e)
                ok()
            except ZmonArgumentError as e:
                act.error(str(e))
            except requests.HTTPError as e:
                log_http_exception(e, act)
            except Exception as e:
                act.error('Failed: {}'.format(str(e)))


@entities.command('delete')
@click.argument('entity_id')
@click.pass_obj
def delete_entity(obj, entity_id):
    """Delete a single entity by ID"""
    client = get_client(obj.config)

    with Action('Deleting entity {} ...'.format(entity_id)) as act:
        deleted = client.delete_entity(entity_id)
        if not deleted:
            act.error('Failed')
