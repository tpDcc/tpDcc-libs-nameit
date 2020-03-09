#! /usr/bin/env python

"""
Library module related with naming convention for the complete rigging toolkit
"""


from __future__ import print_function, division, absolute_import, unicode_literals

import os
import re
import copy
import json
import yaml
import lucidity
import traceback
from collections import OrderedDict

import tpDcc
from tpDcc.libs import nameit
from tpDcc.libs.python import jsonio, yamlio, python, strings as string_utils, name as name_utils

logger = tpDcc.LogsMgr().get_logger('tpDcc-tools-nameit')


class Serializable(object):

    SKIP_ATTRIBUTES = list()

    def data(self):
        # We use copy.deepcopy because a dictionary in Python is a mutable type and we do not want
        # to change the dictionary outside this class
        ret_val = copy.deepcopy(self.__dict__)
        for attr in self.SKIP_ATTRIBUTES:
            if attr in ret_val:
                ret_val.pop(attr)

        # We create some internal properties to validate the new instance
        ret_val['_Serializable_classname'] = type(self).__name__
        ret_val['_Serializable_version'] = '1.0'

        return ret_val

    @classmethod
    def from_data(cls, data, skip_check=False):

        if not skip_check:
            # First of all, we have to validate the data
            if data.get('_Serializable_classname') != cls.__name__:
                return None

            # After the validation we delete validation property
            del data['_Serializable_classname']
            if data.get('_Serializable_version') is not None:
                del data['_Serializable_version']

        this = cls()
        this.__dict__.update(data)
        return this


class Token(Serializable, object):

    def __init__(self, name='New_Token'):
        super(Token, self).__init__()
        self.name = name
        self.default = 0
        self.values = {'key': [], 'value': []}
        self.override_value = ""
        self.description = None

    @staticmethod
    def is_iterator(name):
        """
        Returns true if the passed name is an iterator or False otherwise
        :param name: str, name to check
        :return: bool
        """

        if not isinstance(name, (str, unicode)):
            return False

        if '#' in name or '@' in name:
            return True
        return False

    def get_items(self):
        keys = self.values['key']
        values = self.values['value']
        items_dict = OrderedDict()
        for i, key in enumerate(keys):
            items_dict[key] = values[i]

        return items_dict

    def add_token_value(self):
        """
        Adds a new token value to the token
        :return:
        """

        self.values['key'].append('New_Tag')
        self.values['value'].append('New_Value')

        return self.values

    def remove_token_value(self, value_index):
        """
        Removes a token value from the token
        :return:
        """

        self.values['key'].pop(value_index)
        self.values['value'].pop(value_index)

        return self.values

    def set_token_key(self, item_row, token_key):
        """
        Sets the token key of the token
        :param item_row:
        :param token_key:
        :return:
        """

        if item_row > -1:
            self.values['key'][item_row] = token_key

    def set_token_value(self, item_row, token_value):
        """
        Sets the token key of the token
        :param item_row:
        :param token_value:
        :return:
        """

        if item_row > -1:
            self.values['value'][item_row] = token_value

    def is_required(self):
        """
        Return True if it is required to pass this token to solve the nomenclature
        """

        default = self._get_default()
        if default is None or default == -1:
            return True

        return False

        # return self._get_default() is None

    def solve(self, rule, name=None):
        """
        Solve the token | Fields -> Solved Name
        """

        if self.name == 'rule_name':
            return rule.name

        # If we don't pass any name the token will be solved as the default item value
        if name is None:
            if self.is_iterator(self._get_default()):
                return self._get_default_iterator_value(0, rule=rule)
            else:
                return self._get_default()

        if 'iterator' in self.get_items():
            if name not in self.get_items():
                return self._get_default_iterator_value(name, rule=rule)
            else:
                return name
        else:
            return self.get_items().get(name)

    def _get_default_iterator_value(self, name, rule):
        iterator_format = rule.iterator_format
        if '@' in iterator_format:
            return string_utils.get_alpha(name, capital=('^' in iterator_format))
        elif '#' in iterator_format:
            return str(name).zfill(len(iterator_format))
        else:
            return name

    def parse(self, value):

        """ Parse a value taking in account the items of the token | Solved Name - Fields """

        for k, v in self.get_items().items():
            if v == value:
                return k

    def save(self, file_path, parser_format='yaml'):

        """ Saves token to a file as JSON data """
        file_path = os.path.join(file_path, self.name + '.token')
        if self.data():
            with open(file_path, 'w') as fp:
                if parser_format == 'yaml':
                    yaml.dump(self.data(), fp)
                else:
                    json.dump(self.data(), fp)
            return True
        return False

    def _get_default(self):
        items = self.get_items()
        if not items:
            return None

        if items and python.is_number(self.default) and self.default >= 0:
            default_value = self.get_items().values()[self.default - 1]
            return default_value

        return self.default


class Rule(Serializable, object):

    def __init__(self, name='New Rule', iterator_format='@', auto_fix=False):
        super(Rule, self).__init__()
        self.name = name
        self.expression = None
        self.description = None
        self.auto_fix = auto_fix
        self.iterator_format = iterator_format

    def fields(self):
        """
        Return a list of the fields of the rule
        """

        return re.findall(r"\{([^}]+)\}", re.sub('_', '_', self.expression))

    def iterator_format(self):
        """
        Returns iterator type for this rule
        """

        return self.iterator_format

    def auto_fix(self):
        """
        Returns if rule should auto fix its patter if necessary
        :return: bool
        """

        return self.auto_fix

    def set_auto_fix(self, flag):
        """
        Sets auto fix
        :param flag: bool
        """

        self.auto_fix = flag

    def solve(self, **values):
        """
        Solve the pattern taking into consideration the current fields of the rule
        """

        # if len(values) > 0:
        #     return self._pattern().format(**values)

        if len(values) <= 0:
            return

        # Get only valid pattern values (we don't use None values)
        valid_values = OrderedDict()
        for field in self.fields():
            for k, v in values.items():
                if k == field:
                    if v is None:
                        if self.auto_fix:
                            continue
                        else:
                            logger.warning(
                                'Missing field: "{}" when generating new name (None will be used instead)!'.format(k))
                    valid_values[k] = v

        # We get pattern taking into account if we want to fix automatically the pattern or not
        valid_pattern = self._pattern(valid_values.keys())

        return valid_pattern.format(**valid_values)

    def parse(self, name):
        """
        Parse a rule taking in account the fields of the rule
        """

        ret_val = dict()

        # Take tokens from the current name using a separator character
        split_name = name.split('_')

        # Loop trough each field of the current active rule
        for i, f in enumerate(self.fields()):

            # Get current value and its respective token
            value = split_name[i]
            token = self._tokens[f]

            if token.is_required():
                # We are in a required field, and we simply return the value from the split name
                ret_val[f] = value
                continue

            # Else, we parse the token directly
            ret_val[f] = token.parse(rule=self, name=value)

        return ret_val

    def save(self, file_path, parser_format='yaml'):
        """
        Saves rule to a file as JSON data
        """

        file_path = os.path.join(file_path, self.name() + '.rule')
        if self.data():
            with open(file_path, 'w') as fp:
                if parser_format == 'yaml':
                    yaml.dump(self.data(), fp)
                else:
                    json.dump(self.data(), fp)
            return True
        return False

    def _pattern(self, fields=None):
        """
        Returns the pattern for the rules
        """

        if fields is None:
            fields = self._fields

        return "{{{}}}".format("}_{".join(fields))


class Template(Serializable, object):
    """
    Class that defines a template in the naming manager
    Is stores naming patterns for files
    """

    SKIP_ATTRIBUTES = ['resolver']

    def __init__(self, name='New_Template', pattern=''):
        self.name = name
        self.pattern = pattern
        self.resolver = None

    @property
    def template(self):
        return self._create_template()

    def keys(self):
        """
        Returns keys of the template
        :return: list(str)
        """

        template = self.template
        return template.keys() if template else list()

    def set_resolver(self, resolver):
        if not resolver:
            return

        self.resolver = resolver

    def references(self):
        """
        Returns list of references of the template
        :return: list(str)
        """

        template = self.template
        return template.references() if template else list()

    def parse(self, path_to_parse):
        """
        Parses given path
        :param path_to_parse: str
        :return: list(str)
        """

        try:
            template = self.template
            if self.resolver:
                template.template_resolver = self.resolver
            return template.parse(path_to_parse)
        except Exception:
            logger.warning(
                'Given Path: {} does not match template pattern: {} | {}!'.format(
                    path_to_parse, self.name, self.pattern))
            return None

    def format(self, template_data):
        """
        Returns proper path with the given dict data
        :param template_data: dict(str, str)
        :return: str
        """

        template = self.template
        if self.resolver:
            template.template_resolver = self.resolver
        return template.format(template_data)

    def _create_template(self):
        """
        Internal function that creates the template with the stored data
        :return: lucidity.Template
        """

        template = lucidity.Template(self.name, self.pattern)
        if self.resolver:
            template.template_resolver = self.resolver

        return template


class TemplateToken(Serializable, object):
    """
    Class that defines a template token in the naming manager
    """

    def __init__(self, name='New_Template_Token', description=''):
        self.name = name
        self.description = description

# ======================= RULES ======================= #


class NameLib(object):

    DEFAULT_DATA = {
        "rules": [],
        "tokens": [],
        "template_tokens": [],
        "templates": []
    }

    _active_rule = ''

    _templates = list()
    _templates_tokens = list()
    _tokens = list()
    _rules = list()

    _tokens_key = 'tokens'
    _rules_key = 'rules'
    _keys_key = 'key'
    _values_key = 'value'
    _templates_key = 'templates'
    _template_tokens_key = 'template_tokens'

    def __init__(self):
        self._naming_repo_env = 'NAMING_REPO'
        self._parser_format = 'yaml'
        self._naming_file = None

    @property
    def naming_file(self):
        return self._naming_file

    @naming_file.setter
    def naming_file(self, naming_file_path):
        self._naming_file = naming_file_path

    @property
    def parser_format(self):
        return self._parser_format

    @parser_format.setter
    def parser_format(self, parser_str):
        self._parser_format = parser_str

    @property
    def naming_repo_env(self):
        return self._naming_repo_env

    @naming_repo_env.setter
    def naming_repo_env(self, value):
        self._naming_repo_env = value

    @property
    def rules(self):
        return self._rules

    @property
    def tokens(self):
        return self._tokens

    @property
    def templates(self):
        return self._templates

    @property
    def template_tokens(self):
        return self._templates_tokens

    def has_valid_naming_file(self):
        """
        Returns whether naming file is valid or not
        :return: bool
        """

        return self._naming_file and os.path.isfile(self._naming_file)

    def active_rule(self):
        """
        Return the current active rule
        """

        if not self.has_rule(self._active_rule):
            return None

        return self.get_rule(self._active_rule)

    def set_active_rule(self, name):
        """
        Sets the current active rule
        """

        if not self.has_rule(name):
            return False
        self._active_rule = name

        return True

    def set_rule_auto_fix(self, name, flag):
        """
        Sets if given rule should fix its pattern automatically if necessary or not
        :param name: str, name of the rule
        :param flag: bool
        """
        if not self.has_rule(name):
            return

        self._rules[name].set_auto_fix(flag)

    def has_rule(self, name):
        """
        Get True if a rule its in the curret rules list
        """

        for rule in self._rules:
            if rule.name == name:
                return True

        return False

    def add_rule(self, name, iterator_type='@', *fields):
        """
        Adds a new rule to the rules dictionary
        """

        name = self.get_rule_unique_name(name)
        rule = Rule(name, iterator_type)
        # rule.add_fields(fields)
        self._rules.append(rule)
        if self.active_rule() is None:
            self.set_active_rule(name)
        return rule

    def remove_rule(self, name):
        """
        Removes a rule, if exists, from the current rules list
        """

        if self.has_rule(name):
            rule = self.get_rule(name)
            self._rules.pop(self._rules.index(rule))
            return True
        return False

    def remove_all_rules(self):
        """
        Deletes any rules saved previosluy
        """

        python.clear_list(self._rules)
        self._active_rule = None
        return True

    def get_rule(self, name):
        """
        Gets a rule from the dictionary of rules by its name
        """

        for rule in self._rules:
            if rule.name == name:
                return rule

        return None

    def get_rule_unique_name(self, name):
        """
        Returns a unique name for the given rule name
        :param name: str
        :return: str
        """

        rule_names = [rule.name for rule in self._rules]
        return name_utils.get_unique_name_from_list(rule_names, name)

    def get_rule_by_index(self, index):
        """
        Get a rule from the dictionary of rule by its index
        """

        return self._rules[index]

    def add_token(self, name, **kwargs):
        """
        Adds a new token to the tokens dictionary
        """

        name = self.get_rule_unique_name(name)
        token = Token(name)
        for k, v in kwargs.items():
            # If there is a default value we set it
            if k == 'default':
                token.default = v
                continue
        self._tokens.append(token)
        return token

    def has_token(self, name):
        """
        Get True if a token its in the current tokens list
        """

        for token in self._tokens:
            if token.name == name:
                return True

        return False

    def remove_token(self, name):
        """
        Removes a token, if exists, from the current tokens list
        """

        # If the token name exists in the tokens list ...
        if self.has_token(name):
            token = self.get_token(name)
            self._tokens.pop(self._tokens.index(token))
            return True
        return False

    def remove_all_tokens(self):
        """
        Deletes any tokens saved previously
        """

        python.clear_list(self._tokens)
        return True

    def get_token(self, name):
        """
        Get a token from the dictionary of tokens by its name
        """

        for token in self._tokens:
            if token.name == name:
                return token

        return None

    def get_token_unique_name(self, name):
        """
        Returns a unique name for the given token name
        :param name: str
        :return: str
        """

        token_names = [token.name for token in self._tokens]
        return name_utils.get_unique_name_from_list(token_names, name)

    def get_token_by_index(self, index):
        """
        Get a token from the dictionary of token by its index
        """

        return self._tokens[index]

    def add_template(self, name, pattern=''):
        """
        Adds a new template
        :param name: str
        :param pattern: str
        """

        name = self.get_template_unique_name(name)
        template = Template(name, pattern)
        self._templates.append(template)

        return template

    def has_template(self, name):
        """
        Get True if a template its in the current tokens list
        """

        for template in self._templates:
            if template.name == name:
                return template

        return None

    def remove_template(self, name):
        """
        Removes a template, if exists, from the current tokens list
        """

        if self.has_template(name):
            template = self.get_template(name)
            self._templates.pop(self._templates.index(template))
            return True
        return False

    def remove_all_templates(self):
        """
        Deletes any template saved previously
        """

        python.clear_list(self._templates)
        return True

    def get_template(self, name):
        """
        Get a template from the dictionary of templates by its name
        """

        template_found = None
        for template in self._templates:
            if template.name == name:
                template_found = template
                break

        if not template_found:
            return None

        resolver = dict()
        for template in self._templates:
            if template.name == name:
                continue
            resolver[template.name] = template.template

        for ref in template_found.references():
            ref_template = self.get_template(ref)
            resolver[ref] = ref_template.template

        template_found.set_resolver(resolver)

        return template_found

    def get_template_unique_name(self, name):
        """
        Returns a unique name for the given template name
        :param name: str
        :return: str
        """

        template_names = [template.name for template in self._templates]
        return name_utils.get_unique_name_from_list(template_names, name)

    def get_template_by_index(self, index):
        """
        Get a template from the dictionary of token by its index
        """

        return self._templates[index]

    def add_template_token(self, name, description=''):
        """
        Adds a new template
        :param name: str
        :param description: str
        """

        name = self.get_template_token_unique_name(name)
        template = TemplateToken(name, description)
        self._templates_tokens.append(template)

        return template

    def has_template_token(self, name):
        """
        Get True if a template token its in the current tokens list
        """

        for template_token in self._templates_tokens:
            if template_token.name == name:
                return True

        return False

    def remove_template_token(self, name):
        """
        Removes a template token, if exists, from the current tokens list
        """

        if self.has_template_token(name):
            template_token = self.get_template_token(name)
            self._templates_tokens.pop(self._templates_tokens.index(template_token))
            return True
        return False

    def remove_all_template_tokens(self):
        """
        Deletes any template tokens saved previously
        """

        python.clear_list(self._templates_tokens)
        return True

    def get_template_token(self, name):
        """
        Get a template token from the dictionary of template tokens by its name
        :param name: str
        :return:
        """

        for template_token in self._templates_tokens:
            if template_token.name == name:
                return template_token

        return None

    def get_template_token_unique_name(self, name):
        """
        Returns a unique name for the given template token name
        :param name: str
        :return: str
        """

        template_token_names = [template_token.name for template_token in self._templates_tokens]
        return name_utils.get_unique_name_from_list(template_token_names, name)

    def get_template_token_by_index(self, index):
        """
        Get a template token from the dictionary of token by its index
        """

        return self._templates_tokens[index]

    def solve(self, *args, **kwargs):
        """
        Solve the nomenclature using different techniques:
            - Explicit Conversion
            - Default Conversion
            - Token Management
        """

        i = 0
        values = dict()
        rule = self.active_rule()
        if not rule:
            logger.warning('Impossible to solve because no rule is activated!')
            return

        # Loop trough each field of the current active rule
        for f in rule.fields():
            # Get tpToken object from the dictionary of tokens
            if self.has_token(f):
                token = self.get_token(f)
                if token.is_required():
                    # We are in a required token (a token is required if it does not has default value)
                    if kwargs.get(f) is not None:
                        # If the field is in the keywords passed, we get its value
                        values[f] = kwargs[f]
                        continue
                    else:
                        # Else, we get the passed argument (without using keyword)
                        try:
                            values[f] = args[i]
                        except Exception:
                            values[f] = None
                        i += 1
                        continue
                # If all fails, we try to get the field for the token
                values[f] = token.solve(rule, kwargs.get(f))
            else:
                logger.warning('Expression not valid: token {} not found in tokens list'.format(f))
                return
        return rule.solve(**values)

    def parse_field_from_string(self, string_to_parse, field_name):
        active_rule = self.active_rule()
        if not active_rule:
            return None

        string_split = string_to_parse.split('_')
        if len(string_split) <= 0:
            return None

        rule_fields = active_rule.fields()
        if len(rule_fields) != len(string_split):
            logger.warning(
                'Given string "{}" is not a valid name generated with current nomenclature rule: {}'.format(
                    string_to_parse, active_rule.name()))
            return None

        found_index = -1
        for rule_field in rule_fields:
            if rule_field == field_name:
                found_index += 1
                break
            found_index += 1

        if found_index > -1:
            return string_split[found_index]

        return None

    def parse(self, name):
        """
        Parse a current solved name and return its different fields (metadata information)
            - Implicit Conversion
        """

        # Parse name comparing it with the active rule
        rule = self.active_rule()
        return rule.parse(name)

    def init_naming_data(self):
        """
        Function that initializes naming data file
        """

        if not self.has_valid_naming_file():
            try:
                f = open(self._naming_file, 'w')
                f.close()
            except Exception:
                pass

        if not self.has_valid_naming_file():
            logger.warning(
                'Impossible to initialize naming data because naming file: "{}" does not exists!'.format(
                    self._naming_file))
            return None

        if self._parser_format == 'yaml':
            data = yamlio.read_file(self.naming_file)
        else:
            data = jsonio.read_file(self._naming_file)
        if not data:
            data = self.DEFAULT_DATA
            if self._parser_format == 'yaml':
                yamlio.write_to_file(data, self._naming_file)
            else:
                jsonio.write_to_file(data, self._naming_file)
        else:
            self.load_session()

        return None

    def get_naming_data(self):
        """
        Returns a dictionary containing current naming data
        :return: dict
        """

        rules = list()
        tokens = list()
        templates = list()
        template_tokens = list()

        for rule in self.rules:
            rules.append(rule.data())

        for token in self.tokens:
            tokens.append(token.data())

        for template in self.templates:
            templates.append(template.data())

        for template_token in self.template_tokens:
            template_tokens.append(template_token.data())

        return {
            'active_rule': self._active_rule,
            'rules': rules,
            'tokens': tokens,
            'template_tokens': template_tokens,
            'templates': templates
        }

    def load_naming_data(self):
        """
        Loads data contained in wrapped naming file
        :return: dict
        """

        if not self.has_valid_naming_file():
            logger.warning(
                'Impossible to read naming file because naming file: "{}" does not exists!'.format(self._naming_file))
            return None

        try:
            if self._parser_format == 'yaml':
                data = yamlio.read_file(self._naming_file)
            else:
                data = jsonio.read_file(self._naming_file)
            return data
        except Exception as exc:
            logger.error(
                'Impossible to read naming file "{}": {} | {}'.format(self._naming_file, exc, traceback.format_exc()))

        return None

    def save_naming_data(self, data):
        """
        Saves data into the wrapped naming file
        """

        if not self.has_valid_naming_file():
            logger.warning(
                'Impossible to save naming file because naming file: "{}" does not exists!'.format(self._naming_file))
            return None

        try:
            if self._parser_format == 'yaml':
                yamlio.write_to_file(data, self._naming_file)
            else:
                jsonio.write_to_file(data, self._naming_file)
        except Exception as exc:
            logger.error(
                'Impossible to read naming file "{}": {} | {}'.format(self._naming_file, exc, traceback.format_exc()))

    # def save_rule(self, name, filepath):
    #     """
    #     Saves a serialized rule in a JSON format file
    #     """
    #
    #     rule = self.get_rule(name)
    #     if not rule:
    #         return False
    #     with open(filepath, 'w') as fp:
    #         if self._parser_format == 'yaml':
    #             yaml.dump(rule.data(), fp)
    #         else:
    #             json.dump(rule.data(), fp)
    #     return True

    def load_rule(self, filepath, skip_check=False):
        """
        Loads a serialized rule from a JSON and deserialize it and creates a new one
        """

        if not os.path.isfile(filepath):
            return False
        try:
            with open(filepath) as fp:
                if self._parser_format == 'yaml':
                    data = yaml.safe_load(fp)
                else:
                    data = json.load(fp)
        except Exception:
            return False

        return self.load_rule_from_dict(data, skip_check=skip_check)

    def load_rule_from_dict(self, rule_dict, skip_check=False):
        """
        Loads a new rule from a given serialized dict
        :param rule_dict: dict
        :return: bool
        """

        rule = Rule.from_data(rule_dict, skip_check=skip_check)
        self._rules.append(rule)

        return True

    # def save_token(self, name, filepath):
    #     """
    #     Saves a serialized token in a JSON format file
    #     """
    #
    #     token = self.get_token(name)
    #     if not token:
    #         return False
    #     with open(filepath, 'w') as fp:
    #         if self._parser_format == 'yaml':
    #             yaml.dump(token.data(), fp)
    #         else:
    #             json.dump(token.data(), fp)
    #     return True

    def load_token(self, filepath, skip_check=False):
        """
        Loads a serialized token from a JSON and deserialize it and creates a new one
        """

        if not os.path.isfile(filepath):
            return False
        try:
            with open(filepath) as fp:
                if self._parser_format == 'yaml':
                    data = yaml.safe_load(fp)
                else:
                    data = json.load(fp)
        except Exception:
            return False

        return self.load_token_from_dict(data, skip_check=skip_check)

    def load_token_from_dict(self, token_dict, skip_check=False):
        """
        Loads a new token from a given serialized dict
        :param token_dict: dict
        :return: bool
        """

        token = Token.from_data(token_dict, skip_check=skip_check)
        self._tokens.append(token)

        return True

    def load_template_from_dict(self, template_dict, skip_check=False):
        """
        Loads a new template from a given serialized dict
        :param template_dict: dict
        :return: bool
        """

        template = Template.from_data(template_dict, skip_check=skip_check)
        self._templates.append(template)

        return True

    def load_template_token_from_dict(self, template_token_dict, skip_check=False):
        """
        Loads a new template token from a given serialized dict
        :param template_token_dict: dict
        :return: bool
        """

        template_token = TemplateToken.from_data(template_token_dict, skip_check=skip_check)
        self._templates_tokens.append(template_token)

        return True

    def parse_template(self, template_name, path_to_parse):
        """
        Parses given path in the given template
        :param template_name: str
        :param path_to_parse: str
        :return: list(str)
        """

        if not self.templates:
            return False

        for template in self.templates:
            if template.name == template_name:
                return template.parse(path_to_parse)

        return None

    def check_template_validity(self, template_name, path_to_check):
        """
        Returns whether given path matches given pattern or not
        :param template_name: str
        :param path_to_check: str
        :return: bool
        """

        parse = self.parse_template(template_name, path_to_check)
        if parse is not None and type(parse) is dict:
            return True

        return False

    def format_template(self, template_name, template_tokens):
        """
        Returns template path filled with template tokens data
        :param template_name: str
        :param template_tokens: dict
        :return: str
        """

        templates = self.templates
        if not templates:
            return False

        for template in templates:
            if template.name == template_name:
                return template.format(template_tokens)

        return None

    def get_repo(self):
        env_repo = os.environ.get(self._naming_repo_env)
        local_repo = os.path.join(os.path.expanduser('~'), '.config', 'naming')
        return env_repo, local_repo

    def load_session(self, repo=None):

        self._active_rule = ''
        python.clear_list(self._rules)
        python.clear_list(self._tokens)
        python.clear_list(self._templates)
        python.clear_list(self._templates_tokens)

        if self.has_valid_naming_file():
            logger.info('Loading session from Naming File: {}'.format(self._naming_file))

            naming_data = self.load_naming_data()
            if not naming_data:
                logger.warning('No naming data found!')
                return

            rules = naming_data.get(self._rules_key)
            if rules:
                for rule_data in rules:
                    self.load_rule_from_dict(rule_data, skip_check=True)

            tokens = naming_data.get(self._tokens_key)
            if tokens:
                for token_data in tokens:
                    self.load_token_from_dict(token_data, skip_check=True)

            templates = naming_data.get(self._templates_key)
            if templates:
                for template_data in templates:
                    self.load_template_from_dict(template_data, skip_check=True)

            template_tokens = naming_data.get(self._template_tokens_key)
            if template_tokens:
                for template_token_data in template_tokens:
                    self.load_template_token_from_dict(template_token_data, skip_check=True)

        else:
            repo = repo or self.get_repo()
            if not os.path.exists(repo):
                os.mkdir(repo)

            logger.info('Loading session from directory files: {}'.format(repo))

            # Tokens and rules
            for dir_path, dir_names, file_names in os.walk(repo):
                for file_name in file_names:
                    file_path = os.path.join(dir_path, file_name)
                    if file_name.endswith('.token'):
                        self.load_token(file_path)
                    elif file_name.endswith('.rule'):
                        self.load_rule(file_path)

            # Extra configuration
            file_path = os.path.join(repo, 'naming.conf')
            if os.path.exists(file_path):
                with open(file_path) as fp:
                    if self._parser_format == 'yaml':
                        config = yaml.safe_load(fp)
                    else:
                        config = json.load(fp)
                for k, v in config.items():
                    globals()[k](v)
            return True

    def save_session(self, repo=None):

        if self.has_valid_naming_file():
            logger.info('Saving session from Naming File: {}'.format(self._naming_file))

            naming_data = self.get_naming_data()
            if naming_data:
                self.save_naming_data(naming_data)
        else:

            repo = repo or self.get_repo()

            logger.info('Saving session to directory: {}'.format(repo))

            # Tokens and rules
            for name, token in self._tokens.items():
                file_path = os.path.join(repo, name + '.token')
                self.save_token(name, file_path)

            for name, rule in self._rules.items():
                if not isinstance(rule, Rule):
                    continue
                file_path = os.path.join(repo, name + '.rule')
                self.save_rule(name, file_path)

            for name, template in self._templates.items():
                if not isinstance(template, Template):
                    continue
                file_path = os.path.join(repo, name + '.template')
                self.save_template(name, file_path)

            # Extra configuration
            active = self.active_rule()
            config = {'set_active_rule': active.name() if active else None}
            file_path = os.path.join(repo, 'naming.conf')
            with open(file_path, 'w') as fp:
                if self._parser_format == 'yaml':
                    yaml.dump(config, fp)
                else:
                    json.dump(config, fp)
            return True
