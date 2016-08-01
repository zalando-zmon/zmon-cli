import click

from clickclick import Action

from zmon_cli.cmds.cli import cli
from zmon_cli.output import dump_yaml


@cli.command()
@click.argument('alert_id')
@click.argument('entity_ids', nargs=-1)
@click.pass_context
def data(ctx, alert_id, entity_ids):
    """Get check data for alert and entities"""

    with Action('Retrieving alert data ...', nl=True):
        data = ctx.obj.client.get_alert_data(alert_id)

        if not entity_ids:
            result = data
        else:
            result = [d for d in data if d['entity'] in entity_ids]

        values = {v['entity']: v['results'][0]['value'] for v in result if len(v['results'])}

        print(dump_yaml(values))
