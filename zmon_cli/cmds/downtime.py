import time

import click

from clickclick import AliasedGroup, Action

from zmon_cli.cmds.cli import cli
from zmon_cli.output import dump_yaml
from zmon_cli.client import ZmonArgumentError


@cli.group('downtimes', cls=AliasedGroup)
def downtimes():
    """Manage downtimes"""
    pass


@downtimes.command('create')
@click.argument('entity_ids', nargs=-1)
@click.option('-d', '--duration', type=int, help='downtime duration in minutes', default=60)
@click.option('-c', '--comment')
@click.pass_context
def create_downtime(ctx, entity_ids, duration, comment):
    start_ts = time.time()
    end_ts = time.time() + (duration * 60)

    downtime = {
        'entities': entity_ids,
        'comment': comment or 'downtime by ZMON CLI',
        'start_time': start_ts,
        'end_time': end_ts
    }

    with Action('Creating downtime ...', nl=True) as act:
        try:
            new_downtime = ctx.obj.client.create_downtime(downtime)
            print(dump_yaml(new_downtime))
        except ZmonArgumentError as e:
            act.error('Invalid downtime')
            act.error(str(e))
