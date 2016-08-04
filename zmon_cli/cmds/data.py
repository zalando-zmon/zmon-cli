import click

from zmon_cli.cmds.command import cli, get_client, yaml_output_option, pretty_json
from zmon_cli.output import Output


@cli.command()
@click.argument('alert_id')
@click.argument('entity_ids', nargs=-1)
@click.pass_obj
@yaml_output_option
@pretty_json
def data(obj, alert_id, entity_ids, output, pretty):
    """Get check data for alert and entities"""
    client = get_client(obj.config)

    with Output('Retrieving alert data ...', nl=True, output=output, pretty_json=pretty) as act:
        data = client.get_alert_data(alert_id)

        if not entity_ids:
            result = data
        else:
            result = [d for d in data if d['entity'] in entity_ids]

        values = {v['entity']: v['results'][0]['value'] for v in result if len(v['results'])}

        act.echo(values)
