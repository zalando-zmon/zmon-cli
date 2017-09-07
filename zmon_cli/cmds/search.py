import click

from zmon_cli.cmds.command import cli, get_client, output_option, pretty_json
from zmon_cli.output import Output, render_search

from zmon_cli.client import ZmonArgumentError


@cli.command()
@click.argument('search_query', default="")
@click.option('--team', '-t', multiple=True, required=False,
              help='Filter search by team. Multiple teams filtering is supported.')
@click.option('--limit', '-l', multiple=False, required=False,
              help='Limit number of results, default is 25')
@click.pass_obj
@output_option
@pretty_json
def search(obj, search_query, team, limit, output, pretty):
    """
    Search dashboards, alerts, checks and grafana dashboards.

    Example:

        $ zmon search "search query" -t team-1 -t team-2
    """
    client = get_client(obj.config)

    with Output('Searching ...', nl=True, output=output, pretty_json=pretty, printer=render_search) as act:
        try:
            data = client.search(search_query, limit=limit, teams=team)

            for check in data['checks']:
                check['link'] = client.check_definition_url(check)

            for alert in data['alerts']:
                alert['link'] = client.alert_details_url(alert)

            for dashboard in data['dashboards']:
                dashboard['link'] = client.dashboard_url(dashboard['id'])

            for dashboard in data['grafana_dashboards']:
                dashboard['link'] = client.grafana_dashboard_url(dashboard)

            act.echo(data)
        except ZmonArgumentError as e:
            act.error(str(e))
