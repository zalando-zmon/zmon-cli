import click

from clickclick import Action

from zmon_cli.cmds.command import cli, get_client
from zmon_cli.output import dump_yaml


@cli.command()
@click.argument('alert_id')
@click.argument('entity_ids', nargs=-1)
@click.pass_obj
def data(obj, alert_id, entity_ids):
    """Get check data for alert and entities"""
    client = get_client(obj.config)
    with Action('Retrieving alert data ...', nl=True):
        data = client.get_alert_data(alert_id)

        if not entity_ids:
            result = data
        else:
            result = [d for d in data if d['entity'] in entity_ids]

        values = {v['entity']: v['results'][0]['value'] for v in result if len(v['results'])}

        print(dump_yaml(values))
