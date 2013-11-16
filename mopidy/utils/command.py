from __future__ import unicode_literals

import argparse
import collections
import os
import sys


class _ParserError(Exception):
    pass


class _HelpError(Exception):
    pass


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise _ParserError(message)


class _HelpAction(argparse.Action):
    def __init__(self, option_strings, dest=None, help=None):
        super(_HelpAction, self).__init__(
            option_strings=option_strings,
            dest=dest or argparse.SUPPRESS,
            default=argparse.SUPPRESS,
            nargs=0,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        raise _HelpError()


class Command(object):
    help = None

    def __init__(self):
        self._children = collections.OrderedDict()
        self._arguments = []
        self._overrides = {}

    def _build(self):
        actions = []
        parser = _ArgumentParser(add_help=False)
        parser.register('action', 'help', _HelpAction)

        for args, kwargs in self._arguments:
            actions.append(parser.add_argument(*args, **kwargs))

        parser.add_argument('_args', nargs=argparse.REMAINDER,
                            help=argparse.SUPPRESS)
        return parser, actions

    def add_child(self, name, command):
        self._children[name] = command

    def add_argument(self, *args, **kwargs):
        self._arguments.append((args, kwargs))

    def set(self, **kwargs):
        self._overrides.update(kwargs)

    def exit(self, status_code=0, message=None, usage=None):
        print '\n\n'.join(m for m in (usage, message) if m)
        sys.exit(status_code)

    def format_usage(self, prog=None):
        actions = self._build()[1]
        prog = prog or os.path.basename(sys.argv[0])
        return self._usage(actions, prog) + '\n'

    def _usage(self, actions, prog):
        formatter = argparse.HelpFormatter(prog)
        formatter.add_usage(None, actions, [])
        return formatter.format_help().strip()

    def format_help(self, prog=None):
        actions = self._build()[1]
        prog = prog or os.path.basename(sys.argv[0])

        formatter = argparse.HelpFormatter(prog)
        formatter.add_usage(None, actions, [])

        if self.help:
            formatter.add_text(self.help)

        if actions:
            formatter.add_text('OPTIONS:')
            formatter.start_section(None)
            formatter.add_arguments(actions)
            formatter.end_section()

        subhelp = []
        for name, child in self._children.items():
            child._subhelp(name, subhelp)

        if subhelp:
            formatter.add_text('COMMANDS:')
            subhelp.insert(0, '')

        return formatter.format_help() + '\n'.join(subhelp)

    def _subhelp(self, name, result):
        actions = self._build()[1]

        if self.help or actions:
            formatter = argparse.HelpFormatter(name)
            formatter.add_usage(None, actions, [], '')
            formatter.start_section(None)
            formatter.add_text(self.help)
            formatter.start_section(None)
            formatter.add_arguments(actions)
            formatter.end_section()
            formatter.end_section()
            result.append(formatter.format_help())

        for childname, child in self._children.items():
            child._subhelp(' '.join((name, childname)), result)

    def parse(self, args, prog=None):
        prog = prog or os.path.basename(sys.argv[0])
        try:
            return self._parse(
                args, argparse.Namespace(), self._overrides.copy(), prog)
        except _HelpError:
            self.exit(0, self.format_help(prog))

    def _parse(self, args, namespace, overrides, prog):
        overrides.update(self._overrides)
        parser, actions = self._build()

        try:
            result = parser.parse_args(args, namespace)
        except _ParserError as e:
            self.exit(1, e.message, self._usage(actions, prog))

        if not result._args:
            for attr, value in overrides.items():
                setattr(result, attr, value)
            delattr(result, '_args')
            result.command = self
            return result

        child = result._args.pop(0)
        if child not in self._children:
            usage = self._usage(actions, prog)
            self.exit(1, 'unrecognized command: %s' % child, usage)

        return self._children[child]._parse(
            result._args, result, overrides, ' '.join([prog, child]))

    def run(self, *args, **kwargs):
        raise NotImplementedError
