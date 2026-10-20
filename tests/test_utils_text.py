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
        (
            'This is a test of the textwrap_body function with a dashed list and subsequent indent. The list should not be wrapped.\n'
            '\n'
            '- Item 1\n'
            '- Item 2\n',
            '    ',
            'This is a test of the textwrap_body function with a dashed list and\n'
            '    subsequent indent. The list should not be wrapped.\n'
            '\n'
            '    - Item 1\n'
            '    - Item 2\n',
        ),
        (
            'The following `threading` methods are now deprecated and should be replaced:\n'
            '\n'
            '- `threading.activeCount` => :func:`threading.active_count`\n'
            '\n'
            '- `threading.Condition.notifyAll` =>\n'
            '    :meth:`threading.Condition.notify_all`\n',
            '  ',
            'The following `threading` methods are now deprecated and should be replaced:\n'
            '\n'
            '  - `threading.activeCount` => :func:`threading.active_count`\n'
            '\n'
            '  - `threading.Condition.notifyAll` =>\n'
            '      :meth:`threading.Condition.notify_all`\n',
        ),
    ),
)
def test_textwrap_body(body, subsequent_indent, expected):
    assert textwrap_body(body, subsequent_indent=subsequent_indent) == expected


@pytest.mark.parametrize(
    'body, expected',
    (
        (
            'gh-123456: This is a long sentence that keeps going on and on so that it must wrap when\n'
            'merged into the NEWS file.\n',
            '- gh-123456: This is a long sentence that keeps going on and on so that it\n'
            '  must wrap when merged into the NEWS file.\n',
        ),
        (
            'First paragraph.\n\nSecond paragraph.\n',
            '- First paragraph.\n\n  Second paragraph.\n',
        ),
        (
            'Some changes:\n\n- Item 1\n- Item 2\n',
            '- Some changes:\n\n  - Item 1\n  - Item 2\n',
        ),
    ),
)
def test_textwrap_body_initial_indent(body, expected):
    assert textwrap_body(body, initial_indent='- ', subsequent_indent='  ') == expected
