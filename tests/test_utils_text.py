import pytest

from blurb._utils.text import textwrap_body


@pytest.mark.parametrize(
    'body, subsequent_indent, expected',
    (
        (
            'This is a test of the textwrap_body function with a string. It should wrap the text to 79 characters.',
            '',
            'This is a test of the textwrap_body function with a string. It should wrap\n'
            'the text to 79 characters.\n',
        ),
        (
            [
                'This is a test of the textwrap_body function',
                'with an iterable of strings.',
                'It should wrap the text to 79 characters.',
            ],
            '',
            'This is a test of the textwrap_body function with an iterable of strings. It\n'
            'should wrap the text to 79 characters.\n',
        ),
        (
            'This is a test of the textwrap_body function with a string and subsequent indent.',
            '    ',
            'This is a test of the textwrap_body function with a string and subsequent\n'
            '    indent.\n',
        ),
        (
            'This is a test of the textwrap_body function with a bullet list and subsequent indent. The list should not be wrapped.\n'
            '\n'
            '* Item 1\n'
            '* Item 2\n',
            '    ',
            'This is a test of the textwrap_body function with a bullet list and\n'
            '    subsequent indent. The list should not be wrapped.\n'
            '\n'
            '    * Item 1\n'
            '    * Item 2\n',
        ),
    ),
)
def test_textwrap_body(body, subsequent_indent, expected):
    assert textwrap_body(body, subsequent_indent=subsequent_indent) == expected
