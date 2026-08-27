import pytest

from blurb._cli import build_parser, main


class TestParser:
    """Pin the invocation forms used by external automation.

    Known consumers: python/release-tools, python/blurb_it,
    CPython's Doc/Makefile and Tools/patchcheck/patchcheck.py.
    """

    def test_merge_bare(self):
        args = build_parser().parse_args(['merge'])
        assert args.output is None
        assert args.forced is False

    def test_merge_forced_with_output(self):
        # Doc/Makefile: blurb merge -f build/NEWS
        args = build_parser().parse_args(['merge', '-f', 'build/NEWS'])
        assert args.output == 'build/NEWS'
        assert args.forced is True

    def test_merge_forced_long_option(self):
        args = build_parser().parse_args(['merge', '--forced'])
        assert args.forced is True

    def test_release_version(self):
        # release-tools: blurb release <version>
        args = build_parser().parse_args(['release', '3.14.0'])
        assert args.version == '3.14.0'

    def test_release_dot(self):
        args = build_parser().parse_args(['release', '.'])
        assert args.version == '.'

    def test_release_requires_version(self):
        with pytest.raises(SystemExit) as excinfo:
            build_parser().parse_args(['release'])
        assert excinfo.value.code != 0

    def test_add_bare(self):
        args = build_parser().parse_args(['add'])
        assert args.issue is None
        assert args.section is None

    def test_add_short_options(self):
        args = build_parser().parse_args(['add', '-i', '12345', '-s', 'Library'])
        assert args.issue == '12345'
        assert args.section == 'Library'

    def test_add_long_options(self):
        args = build_parser().parse_args([
            'add',
            '--issue',
            '12345',
            '--section',
            'Library',
        ])
        assert args.issue == '12345'
        assert args.section == 'Library'

    def test_add_long_options_with_equals(self):
        args = build_parser().parse_args(['add', '--issue=12345', '--section=C API'])
        assert args.issue == '12345'
        assert args.section == 'C API'

    def test_export(self):
        args = build_parser().parse_args(['export'])
        assert args.subcommand == 'export'

    def test_populate(self):
        args = build_parser().parse_args(['populate'])
        assert args.subcommand == 'populate'

    def test_unknown_subcommand(self):
        with pytest.raises(SystemExit) as excinfo:
            build_parser().parse_args(['garglemox'])
        assert excinfo.value.code != 0

    def test_unknown_option(self):
        with pytest.raises(SystemExit) as excinfo:
            build_parser().parse_args(['merge', '--garglemox'])
        assert excinfo.value.code != 0


class TestMain:
    @pytest.mark.parametrize('argv', [['--version'], ['-V']])
    def test_version_option(self, argv, capfd):
        with pytest.raises(SystemExit) as excinfo:
            main(argv)
        assert excinfo.value.code in (None, 0)
        captured = capfd.readouterr()
        assert captured.out.startswith('blurb version ')

    @pytest.mark.parametrize('argv', [['--help'], ['-h']])
    def test_help_lists_subcommands(self, argv, capfd):
        with pytest.raises(SystemExit) as excinfo:
            main(argv)
        assert excinfo.value.code in (None, 0)
        captured = capfd.readouterr()
        for name in ('add', 'export', 'merge', 'populate', 'release'):
            assert name in captured.out

    def test_help_for_subcommand(self, capfd):
        with pytest.raises(SystemExit) as excinfo:
            main(['merge', '--help'])
        assert excinfo.value.code in (None, 0)
        captured = capfd.readouterr()
        assert 'blurb merge' in captured.out
        assert '--forced' in captured.out

    def test_legacy_help_subcommand(self, capfd):
        # python-docs-* translation Makefiles probe with 'blurb help'
        with pytest.raises(SystemExit) as excinfo:
            main(['help'])
        assert excinfo.value.code in (None, 0)
        captured = capfd.readouterr()
        for name in ('add', 'export', 'merge', 'populate', 'release'):
            assert name in captured.out

    def test_legacy_help_for_subcommand(self, capfd):
        with pytest.raises(SystemExit) as excinfo:
            main(['help', 'merge'])
        assert excinfo.value.code in (None, 0)
        captured = capfd.readouterr()
        assert 'blurb merge' in captured.out
        assert '--forced' in captured.out

    def test_legacy_help_unknown_subcommand(self):
        with pytest.raises(SystemExit) as excinfo:
            main(['help', 'garglemox'])
        assert excinfo.value.code != 0

    def test_legacy_version_subcommand(self, capfd):
        with pytest.raises(SystemExit) as excinfo:
            main(['version'])
        assert excinfo.value.code in (None, 0)
        captured = capfd.readouterr()
        assert captured.out.startswith('blurb version ')

    def test_no_arguments_runs_add(self, monkeypatch):
        # 'blurb' with no arguments is equivalent to 'blurb add'
        calls = []

        def fake_add(*, issue, section):
            """Add a blurb."""
            calls.append((issue, section))

        monkeypatch.setattr('blurb._add.add', fake_add)
        monkeypatch.setattr('blurb._cli.chdir_to_repo_root', lambda: '/')
        main([])
        assert calls == [(None, None)]

    def test_subcommand_gets_repo_root(self, monkeypatch):
        chdir_calls = []

        def fake_release(version):
            """Move blurbs to a release file."""

        monkeypatch.setattr('blurb._release.release', fake_release)
        monkeypatch.setattr(
            'blurb._cli.chdir_to_repo_root', lambda: chdir_calls.append(True)
        )
        main(['release', '3.14.0'])
        assert chdir_calls == [True]

    def test_version_does_not_need_repo(self, monkeypatch):
        def explode():
            raise AssertionError('--version must not require a CPython repo')

        monkeypatch.setattr('blurb._cli.chdir_to_repo_root', explode)
        with pytest.raises(SystemExit) as excinfo:
            main(['--version'])
        assert excinfo.value.code in (None, 0)
