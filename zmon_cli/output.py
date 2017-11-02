import json
import time

import yaml
import calendar

from clickclick import print_table, OutputFormat, action, secho, error, ok, info


# fields to dump as literal blocks
LITERAL_FIELDS = set(['command', 'condition', 'description'])

# custom sorting of YAML fields (i.e. we are not using the default lexical YAML ordering)
FIELD_ORDER = ['id', 'check_definition_id', 'type', 'name', 'team', 'owning_team', 'responsible_team', 'description',
               'condition',
               'command', 'interval', 'entities', 'entities_exclude', 'status', 'last_modified_by']
FIELD_SORT_INDEX = {k: chr(i) for i, k in enumerate(FIELD_ORDER)}

LAST_MODIFIED_FMT = '%Y-%m-%d %H:%M:%S.%f'


class literal_unicode(str):
    '''Empty class to serialize value as literal YAML block'''
    pass


class CustomDumper(yaml.Dumper):
    '''Custom dumper to sort mapping fields as we like'''

    def represent_mapping(self, tag, mapping, flow_style=None):
        node = yaml.Dumper.represent_mapping(self, tag, mapping, flow_style)
        node.value = sorted(node.value, key=lambda x: FIELD_SORT_INDEX.get(x[0].value, x[0].value))
        return node


def literal_unicode_representer(dumper, data):
    node = dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return node


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


yaml.add_representer(literal_unicode, literal_unicode_representer)


def log_http_exception(e, act=None):
    err = act.error if act else error
    try:
        err('HTTP error: {} - {}'.format(e.response.status_code, e.response.reason))
        try:
            err(json.dumps(e.response.json(), indent=4))
        except Exception:
            err(e.response.text)
    except Exception:
        err('HTTP ERROR: {}'.format(e))


########################################################################################################################
# RENDERERS
########################################################################################################################
class Output:

    def __init__(self, msg, ok_msg=' OK', nl=False, output='text', pretty_json=False, printer=None,
                 suppress_exception=False):
        self.msg = msg
        self.ok_msg = ok_msg
        self.output = output
        self.nl = nl
        self.errors = []
        self.printer = printer
        self.indent = 4 if pretty_json else None
        self._suppress_exception = suppress_exception

    def __enter__(self):
        if self.output == 'text' and not self.printer:
            action(self.msg)
            if self.nl:
                secho('')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            if self.output == 'text' and not self.printer and not self.errors:
                ok(self.ok_msg)
        elif not self._suppress_exception:
            error(' EXCEPTION OCCURRED: {}'.format(exc_val))

    def error(self, msg, **kwargs):
        error(' {}'.format(msg), **kwargs)
        self.errors.append(msg)

    def echo(self, out):
        if self.output == 'yaml':
            print(dump_yaml(out))
        elif self.output == 'json':
            print(json.dumps(out, indent=self.indent))
        elif self.printer:
            self.printer(out, self.output)
        else:
            print(out)


def render_entities(entities, output):
    rows = []
    for e in entities:
        row = e
        s = sorted(e.keys())

        key_values = []

        for k in s:
            if k not in ('id', 'type'):
                if k == 'last_modified':
                    row['last_modified_time'] = (
                        calendar.timegm(time.strptime(row.pop('last_modified'), LAST_MODIFIED_FMT)))
                else:
                    key_values.append('{}={}'.format(k, e[k]))

        row['data'] = ' '.join(key_values)
        rows.append(row)

    rows.sort(key=lambda r: (r['last_modified_time'], r['id'], r['type']))

    with OutputFormat(output):
        print_table('id type last_modified_time data'.split(),
                    rows, titles={'last_modified_time': 'Modified'})


def render_status(status, output=None):
    secho('Alerts active: {}'.format(status.get('alerts_active')))

    info('Workers:')
    rows = []
    for worker in status.get('workers', []):
        rows.append(worker)

    rows.sort(key=lambda x: x.get('name'))

    print_table(['name', 'check_invocations', 'last_execution_time'], rows)

    info('Queues:')
    rows = []
    for queue in status.get('queues', []):
        rows.append(queue)

    rows.sort(key=lambda x: x.get('name'))

    print_table(['name', 'size'], rows)


def render_checks(checks, output=None):
    rows = []

    for check in checks:
        row = check

        row['last_modified_time'] = calendar.timegm(time.gmtime(row.pop('last_modified') / 1000))

        row['name'] = row['name'][:60]
        row['owning_team'] = row['owning_team'][:60].replace('\n', '')

        rows.append(row)

    rows.sort(key=lambda c: c['id'])

    # Not really used since all checks are ACTIVE!
    check_styles = {
        'ACTIVE': {'fg': 'green'},
        'DELETED': {'fg': 'red'},
        'INACTIVE': {'fg': 'yellow'},
    }

    print_table(['id', 'name', 'owning_team', 'last_modified_time', 'last_modified_by', 'status', 'link'], rows,
                titles={'last_modified_time': 'Modified', 'last_modified_by': 'Modified by'}, styles=check_styles)


def render_alerts(alerts, output=None):
    rows = []

    for alert in alerts:
        row = alert

        row['last_modified_time'] = calendar.timegm(time.gmtime(row.pop('last_modified') / 1000))

        row['name'] = row['name'][:60]
        row['responsible_team'] = row['responsible_team'][:40].replace('\n', '')
        row['team'] = row['team'][:40].replace('\n', '')

        priorities = {1: 'HIGH', 2: 'MEDIUM', 3: 'LOW'}
        row['priority'] = priorities.get(row['priority'], 'LOW')

        rows.append(row)

    rows.sort(key=lambda c: c['id'])

    check_styles = {
        'ACTIVE': {'fg': 'green'},
        'REJECTED': {'fg': 'red'},
        'INACTIVE': {'fg': 'yellow'},
        'HIGH': {'fg': 'red'},
        'MEDIUM': {'fg': 'yellow', 'bold': True},
        'LOW': {'fg': 'yellow'},
    }

    titles = {
        'last_modified_time': 'Modified',
        'last_modified_by': 'Modified by',
        'check_definition_id': 'Check ID',
    }

    headers = [
        'id', 'name', 'check_definition_id', 'responsible_team', 'team', 'priority', 'last_modified_time',
        'last_modified_by', 'status', 'link',
    ]

    print_table(headers, rows, titles=titles, styles=check_styles)


def render_search(search, output):

    def _print_table(title, rows):
        info(title)
        rows.sort(key=lambda x: x.get('title'))
        print_table(['id', 'title', 'team', 'link'], rows)
        secho('')

    _print_table('Checks:', search['checks'])
    _print_table('Alerts:', search['alerts'])
    _print_table('Dashboards:', search['dashboards'])
    _print_table('Grafana Dashboards:', search['grafana_dashboards'])
