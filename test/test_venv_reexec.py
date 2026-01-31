#!/usr/bin/env python3

import unittest

import os

import intonation_trainer as trainer


class _ExecCalled(RuntimeError):
    def __init__(self, path, args):
        super().__init__(path)
        self.path = path
        self.args = args


class TestVenvReexec(unittest.TestCase):
    def test_defaults_path_no_venv(self):
        # Exercise default env/argv/python_executable/execv/print_fn branches.
        did = trainer._maybe_reexec_with_project_venv(
            exists=lambda _p: False,
            execv=lambda _path, _args: (_path, _args),
        )
        self.assertFalse(did)

    def test_no_venv_no_reexec(self):
        env = {}
        called = []

        def execv(_path, _args):
            called.append((_path, _args))
            raise AssertionError('execv must not be called')

        did = trainer._maybe_reexec_with_project_venv(
            env=env,
            argv=['intonation_trainer.py', 'cfg.yaml'],
            python_executable='/usr/bin/python3',
            exists=lambda _p: False,
            execv=execv,
            print_fn=lambda _msg: None,
        )
        self.assertFalse(did)
        self.assertEqual(called, [])

    def test_venv_triggers_execv(self):
        env = {}
        argv = ['intonation_trainer.py', 'tracks/vocal_range_example/ladder_down_A2_B4.yaml']

        def exists(p):
            return str(p).endswith('/.venv/bin/python')

        def execv(path, args):
            raise _ExecCalled(path, args)

        with self.assertRaises(_ExecCalled) as ctx:
            trainer._maybe_reexec_with_project_venv(
                env=env,
                argv=argv,
                python_executable='/usr/bin/python3',
                exists=exists,
                execv=execv,
                print_fn=lambda _msg: None,
            )

        self.assertEqual(env.get('INTONATION_TRAINER_REEXECED'), '1')
        self.assertTrue(str(ctx.exception.path).endswith('/.venv/bin/python'))
        exec_args = list(ctx.exception.args)
        self.assertTrue(str(exec_args[0]).endswith('/.venv/bin/python'))
        self.assertEqual(exec_args[1:], argv)

    def test_already_reexeced_does_nothing(self):
        env = {'INTONATION_TRAINER_REEXECED': '1'}
        called = []

        def execv(_path, _args):
            called.append((_path, _args))
            raise AssertionError('execv must not be called')

        did = trainer._maybe_reexec_with_project_venv(
            env=env,
            argv=['intonation_trainer.py', 'cfg.yaml'],
            python_executable='/usr/bin/python3',
            exists=lambda _p: True,
            execv=execv,
            print_fn=lambda _msg: None,
        )
        self.assertFalse(did)
        self.assertEqual(called, [])

    def test_already_using_venv_python_does_nothing(self):
        env = {}
        called = []

        venv_python = os.path.join(os.path.dirname(os.path.abspath(trainer.__file__)), '.venv', 'bin', 'python')

        def exists(p):
            return os.path.abspath(str(p)) == os.path.abspath(venv_python)

        def execv(_path, _args):
            called.append((_path, _args))
            raise AssertionError('execv must not be called')

        did = trainer._maybe_reexec_with_project_venv(
            env=env,
            argv=['intonation_trainer.py', 'cfg.yaml'],
            python_executable=venv_python,
            exists=exists,
            execv=execv,
            print_fn=lambda _msg: None,
        )
        self.assertFalse(did)
        self.assertEqual(called, [])


if __name__ == '__main__':
    unittest.main()
