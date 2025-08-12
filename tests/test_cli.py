import blurb._cli


def test_version(capfd):
    # Act
    blurb._cli.version()

    # Assert
    captured = capfd.readouterr()
    assert captured.out.startswith("blurb version ")


