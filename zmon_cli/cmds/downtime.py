import time

import click

from clickclick import AliasedGroup

from zmon_cli.cmds.command import cli, get_client, yaml_output_option, pretty_json
from zmon_cli.output import Output
from zmon_cli.client import ZmonArgumentError


@cli.group('downtimes', cls=AliasedGroup)
def downtimes():
    """Manage downtimes"""
    pass


@downtimes.command('create')
@click.argument('entity_ids', nargs=-1)
@click.option('-d', '--duration', type=int, help='downtime duration in minutes', default=60)
@click.option('-c', '--comment')
@click.pass_obj
@yaml_output_option
@pretty_json
def create_downtime(obj, entity_ids, duration, comment, output, pretty):
    """Create downtime for specified entities"""
    client = get_client(obj.config)

    start_ts = time.time()
    end_ts = time.time() + (duration * 60)

    downtime = {
        'entities': entity_ids,
        'comment': comment or 'downtime by ZMON CLI',
        'start_time': start_ts,
        'end_time': end_ts
    }

    with Output('Creating downtime ...', nl=True, output=output, pretty_json=pretty) as act:
        try:
            new_downtime = client.create_downtime(downtime)
            act.echo(new_downtime)
        except ZmonArgumentError as e:
            act.error(str(e))


@downtimes.command('help')
@click.pass_context
def help(ctx):
    print(ctx.parent.get_help())
