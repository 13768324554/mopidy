from __future__ import unicode_literals

import argparse
import mock
import unittest

from mopidy.utils import command


class CommandParsingTest(unittest.TestCase):
    def test_command_parsing_returns_namespace(self):
        cmd = command.Command(None)
        self.assertIsInstance(cmd.parse([]), argparse.Namespace)

    def test_command_parsing_does_not_contain_args(self):
        cmd = command.Command(None)
        result = cmd.parse([])
        self.assertFalse(hasattr(result, '_args'))

    def test_sub_command_delegation(self):
        mock_cmd = mock.Mock(spec=command.Command)
        mock_cmd.name = 'foo'

        cmd = command.Command(None)
        cmd.add_child(mock_cmd)

        cmd.parse(['foo'])
        mock_cmd.parse.assert_called_with([], mock.ANY)

    def test_unknown_options_raises_error(self):
        cmd = command.Command(None)
        with self.assertRaises(command.CommandError):
            cmd.parse(['--foobar'])

    def test_invalid_sub_command_raises_error(self):
        cmd = command.Command(None)
        with self.assertRaises(command.CommandError):
            cmd.parse(['foo'])

    def test_command_arguments(self):
        cmd = command.Command(None)
        cmd.add_argument('--bar')

        result = cmd.parse(['--bar', 'baz'])
        self.assertEqual(result.bar, 'baz')

    def test_command_arguments_and_sub_command(self):
        child = command.Command('foo')
        child.add_argument('--baz')

        cmd = command.Command(None)
        cmd.add_argument('--bar')
        cmd.add_child(child)

        result = cmd.parse(['--bar', 'baz', 'foo'])
        self.assertEqual(result.bar, 'baz')
        self.assertEqual(result.baz, None)

    def test_multiple_sub_commands(self):
        mock_foo_cmd = mock.Mock(spec=command.Command)
        mock_foo_cmd.name = 'foo'

        mock_bar_cmd = mock.Mock(spec=command.Command)
        mock_bar_cmd.name = 'bar'

        mock_baz_cmd = mock.Mock(spec=command.Command)
        mock_baz_cmd.name = 'baz'

        cmd = command.Command(None)
        cmd.add_child(mock_foo_cmd)
        cmd.add_child(mock_bar_cmd)
        cmd.add_child(mock_baz_cmd)

        cmd.parse(['bar'])
        mock_bar_cmd.parse.assert_called_with([], mock.ANY)

        cmd.parse(['baz'])
        mock_baz_cmd.parse.assert_called_with([], mock.ANY)

    def test_subcommand_may_have_positional(self):
        child = command.Command('foo')
        child.add_argument('bar')

        cmd = command.Command(None)
        cmd.add_child(child)

        result = cmd.parse(['foo', 'baz'])
        self.assertEqual(result.bar, 'baz')

    def test_subcommand_may_have_remainder(self):
        child = command.Command('foo')
        child.add_argument('bar', nargs=argparse.REMAINDER)

        cmd = command.Command(None)
        cmd.add_child(child)

        result = cmd.parse(['foo', 'baz', 'bep', 'bop'])
        self.assertEqual(result.bar, ['baz', 'bep', 'bop'])

    def test_result_stores_choosen_command(self):
        child = command.Command('foo')

        cmd = command.Command(None)
        cmd.add_child(child)

        result = cmd.parse(['foo'])
        self.assertEqual(result.command, child)

        result = cmd.parse([])
        self.assertEqual(result.command, cmd)
