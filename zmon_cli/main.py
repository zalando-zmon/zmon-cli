import ast
import json
import textwrap
import zmon_cli
import urllib

from clickclick import Action, action, ok, error, info, AliasedGroup, print_table, OutputFormat

import click
import clickclick
import logging
import os
import requests
from requests.auth import HTTPBasicAuth
import yaml
import urllib.parse
import zign.api
import datetime

import keyring

# fields to dump as literal blocks
LITERAL_FIELDS = set(['command', 'condition', 'description'])

# custom sorting of YAML fields (i.e. we are not using the default lexical YAML ordering)
FIELD_ORDER = ['id', 'check_definition_id', 'type', 'name', 'team', 'owning_team', 'responsible_team', 'description',
               'condition',
               'command', 'interval', 'entities', 'entities_exclude', 'status', 'last_modified_by']
FIELD_SORT_INDEX = {k: chr(i) for i, k in enumerate(FIELD_ORDER)}

DEFAULT_CONFIG_FILE = '~/.zmon-cli.yaml'

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

output_option = click.option('-o', '--output', type=click.Choice(['text', 'json', 'tsv']), default='text',
                             help='Use alternative output format')


class literal_unicode(str):
    '''Empty class to serialize value as literal YAML block'''
    pass


def literal_unicode_representer(dumper, data):
    node = dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return node


yaml.add_representer(literal_unicode, literal_unicode_representer)


class CustomDumper(yaml.Dumper):
    '''Custom dumper to sort mapping fields as we like'''
    def represent_mapping(self, tag, mapping, flow_style=None):
        node = yaml.Dumper.represent_mapping(self, tag, mapping, flow_style)
        node.value = sorted(node.value, key=lambda x: FIELD_SORT_INDEX.get(x[0].value, x[0].value))
        return node


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo('ZMON CLI {}'.format(zmon_cli.__version__))
    ctx.exit()


def configure_logging(loglevel):
    # configure file logger to not clutter stdout with log lines
    logging.basicConfig(level=loglevel, filename='/tmp/zmon-cli.log',
                        format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
    logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.WARNING)


def get_base_url(url):
    '''
    >>> get_base_url('https://localhost:8443/example/api/v123')
    'https://localhost:8443/'
    '''
    split = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit(list(split[:2]) + ['/', '', ''])


@click.group(cls=AliasedGroup, context_settings=CONTEXT_SETTINGS)
@click.option('-c', '--config-file', help='Use alternative config file', default=DEFAULT_CONFIG_FILE, metavar='PATH')
@click.option('-v', '--verbose', help='Verbose logging', is_flag=True)
@click.option('-V', '--version', is_flag=True, callback=print_version, expose_value=False, is_eager=True)
@click.pass_context
def cli(ctx, config_file, verbose):
    """
    ZMON command line interface
    """
    configure_logging(logging.DEBUG if verbose else logging.INFO)
    fn = os.path.expanduser(config_file)
    data = {}
    if os.path.exists(fn):
        with open(fn) as fd:
            data = yaml.safe_load(fd)
    ctx.obj = data


@cli.command()
@click.option('-c', '--config-file', help='Use alternative config file', default=DEFAULT_CONFIG_FILE, metavar='PATH')
@click.pass_context
def configure(ctx, config_file):
    '''Configure ZMON URL and credentials'''

    while True:
        url = click.prompt('Please enter the ZMON base URL (e.g. https://demo.zmon.io/api/v1)',
                           default=ctx.obj.get('url'))
        with Action('Checking {}..'.format(url)) as act:
            try:
                requests.get(url, timeout=5, allow_redirects=False)
                break
            except:
                act.error('ERROR')

    data = {'url': url}

    if click.confirm('Is your ZMON using GitHub for authentication?'):
        token = click.prompt('Your personal access token (optional, only needed for GitHub auth)')
        data['token'] = token

    fn = os.path.expanduser(config_file)
    with Action('Writing configuration to {}..'.format(fn)):
        with open(fn, 'w') as fd:
            yaml.safe_dump(data, fd, default_flow_style=False)


def query_password(user):
    pw = click.prompt("Password for {}".format(user), hide_input=True)
    keyring.set_password("zmon-cli", user, pw)
    return pw


def get_config_data():
    fn = os.path.expanduser(DEFAULT_CONFIG_FILE)
    data = {}
    try:
        if os.path.exists(fn):
            with open(fn) as fd:
                data = yaml.safe_load(fd)

            if 'password' in data:
                keyring.set_password("zmon-cli", data['user'], data['password'])
                del data['password']
                with open(fn, mode='w') as fd:
                    yaml.dump(data, fd, default_flow_style=False,
                              allow_unicode=True,
                              encoding='utf-8')
        else:
            clickclick.warning("No configuration file found at [{}]".format(DEFAULT_CONFIG_FILE))
            data['url'] = click.prompt("ZMON Base URL (e.g. https://zmon.example.org/api/v1)")
            # TODO: either ask for fixed token or Zign
            data['user'] = click.prompt("ZMON username", default=os.environ['USER'])

            with open(fn, mode='w') as fd:
                yaml.dump(data, fd, default_flow_style=False,
                          allow_unicode=True,
                          encoding='utf-8')
    except Exception as e:
        error(e)

    return validate_config(data)


def validate_config(data):
    '''
    >>> validate_config({'url': 'foo', 'token': '123'})['url']
    'foo'
    '''
    if not data.get('url'):
        raise Exception("Config file not properly configured: key 'url' is missing")
    if 'user' in data:
        data['password'] = keyring.get_password('zmon-cli', data['user'])
        if data['password'] is None:
            data['password'] = query_password(data['user'])
    elif 'token' not in data:
        data['token'] = zign.api.get_token('zmon', ['uid'])

    return data


def request(method, path, **kwargs):
    data = get_config_data()
    if 'token' in data:
        headers = kwargs.get('headers', {})
        headers['Authorization'] = 'Bearer {}'.format(data['token'])
        kwargs['headers'] = headers
    else:
        kwargs['auth'] = HTTPBasicAuth(data['user'], data['password'])
    if 'verify' in data:
        requests.packages.urllib3.disable_warnings()
        kwargs['verify'] = data['verify']
    response = method(data['url'] + path, **kwargs)
    if response.status_code == 401:
        # retry with new password
        clickclick.error("Authorization failed")
        data['password'] = query_password(data['user'])
        response = request(method, path, **kwargs)
    response.raise_for_status()
    return response


def get(url):
    response = request(requests.get, url)
    return response


def put(url, body):
    response = request(requests.put, url, data=body,
                       headers={'content-type': 'application/json'})
    return response


def post(url, body):
    response = request(requests.post, url, data=body,
                       headers={'content-type': 'application/json'})
    return response


def delete(url):
    response = request(requests.delete, url)
    return response


@cli.group()
@click.pass_context
def members(ctx):
    """Manage group membership"""
    pass


@cli.group('onetime-tokens', cls=AliasedGroup)
@click.pass_context
def tv_tokens(ctx):
    """Manage onetime tokens for TVs/View only login"""
    pass


@tv_tokens.command('get')
def get_tv_token():
    """retrieve a new token"""
    r = post('/onetime-tokens', {})
    action('Getting one-time token: ...')
    ok(r.text)


@tv_tokens.command('list')
def list_tv_token():
    """list onetime tokens for your user"""
    r = get('/onetime-tokens')
    ts = r.json()
    for t in ts:
        t["created"] = datetime.datetime.fromtimestamp(t["created"]/1000)
        if t["bound_at"] is not None:
            t["bound_at"] = datetime.datetime.fromtimestamp(t["bound_at"]/1000)

    print(dump_yaml(ts))


@cli.group('alert-definitions', cls=AliasedGroup)
@click.pass_context
def alert_definitions(ctx):
    """Manage alert definitions"""
    pass


@alert_definitions.command('init')
@click.argument('yaml_file', type=click.File('wb'))
def init(yaml_file):
    '''Initialize a new alert definition YAML file'''
    template = textwrap.dedent('''
    check_definition_id: {check_id}
    id:
    status: ACTIVE
    name: "{name}"
    description: "Example Alert Description"
    team: "{team}"
    responsible_team: "{team}"
    condition: |
      >100
    entities:
    entities_exclude:
    status: ACTIVE
    priority: 2
    tags:
    parent_id:
    parameters:
    ''')
    name = click.prompt('Alert name', default='Example Alert')
    check_id = click.prompt('Check ID')
    team = click.prompt('(Responsible-) Team', default='Example Team')
    data = template.format(name=name, team=team, check_id=check_id)
    yaml_file.write(data.encode('utf-8'))


@alert_definitions.command('get')
@click.argument("alert_id", type=int)
def get_alert_definition(alert_id):
    '''Get a single alert definition'''

    data = get('/alert-definitions/{}'.format(alert_id)).json()
    keys = list(data.keys())
    for k in keys:
        if data[k] is None:
            del data[k]

    print(dump_yaml(data))


@alert_definitions.command("create")
@click.argument('yaml_file', type=click.File('rb'))
def create_alert_definition(yaml_file):
    """Create a single alert definition"""
    data = get_config_data()
    alert = yaml.safe_load(yaml_file)
    alert['last_modified_by'] = data.get('user', 'unknown')
    if 'status' not in alert:
        alert['status'] = 'ACTIVE'

    action('Creating alert definition..')

    if 'check_definition_id' not in alert:
        error('"check_definition_id" missing in definition')
        return

    r = post('/alert-definitions', json.dumps(alert))
    ok(get_base_url(get_config_data()["url"]) + "#/alert-details/" + str(r.json()["id"]))


@alert_definitions.command("update")
@click.argument('yaml_file', type=click.File('rb'))
def update_alert_definition(yaml_file):
    """Update a single alert definition"""
    data = get_config_data()
    alert = yaml.safe_load(yaml_file)
    alert['last_modified_by'] = data.get('user', 'unknown')
    if 'status' not in alert:
        alert['status'] = 'ACTIVE'

    action('Updating alert definition..')

    if 'id' not in alert:
        error('"id" missing in definition')
        return

    if 'check_definition_id' not in alert:
        error('"check_definition_id" missing in definition')
        return

    alert_id = alert['id']

    r = put('/alert-definitions/{}'.format(alert_id), json.dumps(alert))
    ok(get_base_url(get_config_data()["url"]) + "#/alert-details/" + str(r.json()["id"]))


@cli.group('check-definitions', cls=AliasedGroup)
@click.pass_context
def check_definitions(ctx):
    """Manage check definitions"""
    pass


def validate_check_command(src):
    try:
        ast.parse(src)
    except Exception as e:
        raise click.UsageError('Invalid check command: {}'.format(e))


@check_definitions.command("update")
@click.argument('yaml_file', type=click.File('rb'))
def update(yaml_file):
    """update a single check definition"""
    data = get_config_data()

    check = yaml.safe_load(yaml_file)
    check['last_modified_by'] = data.get('user', 'unknown')
    if 'status' not in check:
        check['status'] = 'ACTIVE'

    action('Updating check definition..')

    if not check.get('owning_team'):
        raise click.UsageError('Missing "owning_team" in check definition')

    validate_check_command(check['command'])

    r = post('/check-definitions', json.dumps(check))
    ok(get_base_url(get_config_data()["url"]) + "#/check-definitions/view/" + str(r.json()["id"]))


def remove_trailing_whitespace(text: str):
    '''Remove all trailing whitespace from all lines'''
    return '\n'.join([line.rstrip() for line in text.strip().split('\n')])


def dump_yaml(data):
    if isinstance(data, dict):
        for key, val in data.items():
            if key in LITERAL_FIELDS:
                # trailing whitespace would force YAML emitter to use doublequoted string
                data[key] = literal_unicode(remove_trailing_whitespace(val))
    return yaml.dump(data, default_flow_style=False, allow_unicode=True, Dumper=CustomDumper)


@check_definitions.command('init')
@click.argument('yaml_file', type=click.File('wb'))
def init_check_definition(yaml_file):
    '''Initialize a new check definition YAML file'''
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


@check_definitions.command("delete")
@click.argument("check_id", type=int)
def delete_check_definition(check_id):
    '''Delete an orphan check definition'''

    action('Deleting check {}..'.format(check_id))
    r = delete('/check-definitions/{}'.format(check_id))
    if r.status_code == 200:
        ok()
    else:
        error(r.text)


@check_definitions.command("get")
@click.argument("check_id", type=int)
def get_check_definition(check_id):
    '''get a single check definition'''

    r = get('/check-definitions/{}'.format(check_id))

    if r.status_code != 200 or r.text == "":
        action("Retrieving check " + str(check_id) + "..")
        error("not found")
        return

    data = r.json()

    keys = list(data.keys())
    for k in keys:
        if data[k] is None:
            del data[k]
    print(dump_yaml(data))


def render_entities(output, key=None, value=''):
    if key:
        r = get('/entities/?query={}'.format(json.dumps({key: value})))
    else:
        r = get('/entities/')

    entities = r.json()
    rows = []
    for e in entities:
        row = e
        s = sorted(e.keys())
        key_values = []
        for k in s:
            if k not in ('id', 'type'):
                key_values.append('{}={}'.format(k, e[k]))
        row['data'] = ' '.join(key_values)
        rows.append(row)

    rows.sort(key=lambda r: (r['id'], r['type']))
    with OutputFormat(output):
        print_table('id type data'.split(), rows)


@cli.group("entities", cls=AliasedGroup, invoke_without_command=True)
@click.pass_context
@output_option
def entities(ctx, output):
    '''Manage entities'''
    if not ctx.invoked_subcommand:
        render_entities(output)


@entities.command("push")
@click.argument("entity")
@click.pass_context
def push_entity(ctx, entity):
    '''Push one or more entities'''
    if (entity.endswith('.json') or entity.endswith('.yaml')) and os.path.exists(entity):
        # JSON is a subset of YAML, so we can use the YAML parser..
        with open(entity, 'rb') as fd:
            data = yaml.safe_load(fd)
    else:
        data = json.loads(entity)

    if not isinstance(data, list):
        data = [data]

    for e in data:
        action("Creating entity {}..".format(e['id']))
        try:
            entity = json.dumps(e)
            put('/entities/', entity)
            ok()
        except:
            error("failed")


@entities.command("delete")
@click.argument("entity-id")
@click.pass_context
def delete_entity(ctx, entity_id):
    '''Delete a single entity by ID'''
    action("Deleting entity {}..".format(entity_id))
    try:
        r = delete('/entities/?id={}'.format(urllib.parse.quote_plus(entity_id)))
        if r.status_code == 200 and r.text == "1":
            ok()
        else:
            error("Delete unsuccessfull")
    except Exception as ex:
        error("Exception during delete: " + str(ex))


@entities.command("get")
@click.argument("entity-id")
@click.pass_context
def get_entity(ctx, entity_id):
    '''Get a single entity by ID'''
    try:
        r = get('/entities/{}/'.format(urllib.parse.quote_plus(entity_id)))
        if r.status_code == 200 and r.text != "":
            print(dump_yaml(r.json()))
        else:
            action("Getting entity " + entity_id + "..")
            error("not found")
    except Exception as ex:
        error("Exception during get entity: " + str(ex))


@entities.command("filter")
@click.argument("key")
@click.argument("value")
@click.pass_context
@output_option
def filter_entities(ctx, key, value, output):
    '''List entities filtered by a certain key'''
    render_entities(output, key, value)


@cli.group(invoke_without_command=True)
@click.pass_context
def groups(ctx):
    """Manage contact groups"""
    if not ctx.invoked_subcommand:
        r = get("/groups/")
        for t in r.json():
            print("Name: {} Id: {}".format(t["name"], t["id"]))
            print("\tMembers:")
            for m in t["members"]:
                m = get("/groups/member/{}/".format(m)).json()
                print("\t\t{} {} {}".format(m["name"], m["email"], m["phones"]))
            print("\tActive:")
            for m in t["active"]:
                m = get("/groups/member/{}/".format(m)).json()
                print("\t\t{} {} {}".format(m["name"], m["email"], m["phones"]))


@groups.command("switch")
@click.argument("group_name")
@click.argument("user_name")
@click.pass_context
def switch_active(ctx, group_name, user_name):
    action("Switching active user..")
    r = delete("/groups/{}/active/".format(group_name))
    r = put("/groups/{}/active/{}/".format(group_name, user_name))
    if r.text == '1':
        ok()
    else:
        error("failed to switch")


@members.command("add")
@click.argument("group_name")
@click.argument("user_name")
@click.pass_context
def group_add(ctx, group_name, user_name):
    action("Adding user..")
    r = put("/groups/{}/member/{}/".format(group_name, user_name))
    if r.text == '1':
        ok()
    else:
        error("failed to insert")


@members.command("remove")
@click.argument("group_name")
@click.argument("user_name")
@click.pass_context
def group_remove(ctx, group_name, user_name):
    action("Removing user..")
    r = delete("/groups/{}/member/{}/".format(group_name, user_name))
    if r.text == '1':
        ok()
    else:
        error("failed to remove")


@members.command("add-phone")
@click.argument("member_email")
@click.argument("phone_nr")
@click.pass_context
def add_phone(ctx, member_email, phone_nr):
    action("Adding phone..")
    r = put("/groups/{}/phone/{}/".format(member_email, phone_nr))
    if r.text == '1':
        ok()
    else:
        error("failed to set phone")


@members.command("remove-phone")
@click.argument("member_email")
@click.argument("phone_nr")
@click.pass_context
def remove_phone(ctx, member_email, phone_nr):
    action("Removing phone number..")
    r = delete("/groups/{}/phone/{}/".format(member_email, phone_nr))
    if r.text == '1':
        ok()
    else:
        error("failed to remove phone")


@members.command("change-name")
@click.argument("member_email")
@click.argument("member_name")
@click.pass_context
def set_name(ctx, member_email, member_name):
    action("Changing user name..")
    put("/groups/{}/name/{}/".format(member_email, member_name))
    ok()


@cli.group('grafana', cls=AliasedGroup)
@click.pass_context
def grafana(ctx):
    """Manage Grafana dashboards"""
    pass


@grafana.command('get')
@click.argument("dashboard_id", type=click.STRING)
@click.pass_context
def grafana_get(ctx, dashboard_id):
    """Get ZMON dashboard"""
    r = get("/grafana2-dashboards/{}".format(dashboard_id))
    print(dump_yaml(r.json()))


@grafana.command('update')
@click.argument('yaml_file', type=click.Path(exists=True))
@click.pass_context
def grafana_update(ctx, yaml_file):
    """Create/Update a single ZMON dashboard"""

    with open(yaml_file, 'rb') as f:
        data = yaml.safe_load(f)

    title = data.get('dashboard', {}).get('title', None)
    id = data.get('dashboard', {}).get('id', None)

    if id is None and title is None:
        error("id and title missing")

    if title is None:
        error("title is missing")

    action('Updating dashboard "{}"..'.format(title))
    r = post('/grafana2-dashboards', json.dumps(data))
    if r.status_code == 200:
        ok()
    else:
        error(r.text)


@cli.group('dashboard', cls=AliasedGroup)
@click.pass_context
def dashboard(ctx):
    """Manage ZMON dashboards"""
    pass


@dashboard.command('get')
@click.argument("dashboard_id", type=int)
@click.pass_context
def dashboard_get(ctx, dashboard_id):
    """Get ZMON dashboard"""
    r = get("/dashboard/{}".format(dashboard_id))
    print(dump_yaml(r.json()))


@dashboard.command('update')
@click.argument('yaml_file', type=click.Path(exists=True))
@click.pass_context
def dashboard_update(ctx, yaml_file):
    """Create/Update a single ZMON dashboard"""

    with open(yaml_file, 'rb') as f:
        data = yaml.safe_load(f)

    if 'id' in data:
        action('Updating dashboard {}..'.format(data.get('id')))
        post('/dashboard/{}'.format(data['id']), json.dumps(data))
        ok()
    else:
        action('Creating new dashboard..')
        r = post('/dashboard/', json.dumps(data))
        data['id'] = int(r.text)

        with open(yaml_file, 'wb') as f:
            f.write(dump_yaml(data).encode('utf-8'))

        ok("new id: {}".format(r.text))


@cli.command()
@click.pass_obj
def status(config):
    """Check system status"""
    response = get('/status')
    data = response.json()
    click.secho('Alerts active: {}'.format(data.get('alerts_active')))
    info('Workers:')
    rows = []
    for worker in data.get('workers', []):
        rows.append(worker)
    rows.sort(key=lambda x: x.get('name'))
    print_table(['name', 'check_invocations', 'last_execution_time'], rows)
    info('Queues:')
    rows = []
    for queue in data.get('queues', []):
        rows.append(queue)
    rows.sort(key=lambda x: x.get('name'))
    print_table(['name', 'size'], rows)


def main():
    try:
        cli()
    except requests.HTTPError as e:
        clickclick.error('ERROR: {}'.format(e))
