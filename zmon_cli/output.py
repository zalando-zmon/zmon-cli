import yaml

from clickclick import print_table, OutputFormat


# fields to dump as literal blocks
LITERAL_FIELDS = set(['command', 'condition', 'description'])

# custom sorting of YAML fields (i.e. we are not using the default lexical YAML ordering)
FIELD_ORDER = ['id', 'check_definition_id', 'type', 'name', 'team', 'owning_team', 'responsible_team', 'description',
               'condition',
               'command', 'interval', 'entities', 'entities_exclude', 'status', 'last_modified_by']
FIELD_SORT_INDEX = {k: chr(i) for i, k in enumerate(FIELD_ORDER)}


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


########################################################################################################################
# RENDERERS
########################################################################################################################
def render_entities(entities, output):
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
