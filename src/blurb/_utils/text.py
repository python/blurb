from __future__ import annotations

import base64
import hashlib
import itertools
import textwrap

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Iterable


def textwrap_body(body: str | Iterable[str], *, subsequent_indent: str = '') -> str:
    """Wrap body text.

    Accepts either a string or an iterable of strings.
    (Iterable is assumed to be individual lines.)
    Returns a string.
    """
    if isinstance(body, str):
        text = body
    else:
        text = '\n'.join(body).rstrip()

    # textwrap merges paragraphs, ARGH

    # step 1: remove trailing whitespace from individual lines
    #   (this means that empty lines will just have \n, no invisible whitespace)
    lines = []
    for line in text.split('\n'):
        lines.append(line.rstrip())
    text = '\n'.join(lines)
    # step 2: break into paragraphs and wrap those
    paragraphs = text.split('\n\n')
    paragraphs2 = []
    kwargs: dict[str, object] = {'break_long_words': False, 'break_on_hyphens': False}
    if subsequent_indent:
        kwargs['subsequent_indent'] = subsequent_indent
    dont_reflow = False
    for paragraph in paragraphs:
        # don't reflow bulleted / numbered lists
        dont_reflow = dont_reflow or paragraph.startswith(('* ', '1. ', '#. '))
        if dont_reflow:
            initial = kwargs.get('initial_indent', '')
            subsequent = kwargs.get('subsequent_indent', '')
            if initial or subsequent:
                lines = [line.rstrip() for line in paragraph.split('\n')]
                indents = itertools.chain(
                    itertools.repeat(initial, 1),
                    itertools.repeat(subsequent),
                )
                lines = [indent + line for indent, line in zip(indents, lines)]
                paragraph = '\n'.join(lines)
            paragraphs2.append(paragraph)
        else:
            # Why do we reflow the text twice?  Because it can actually change
            # between the first and second reflows, and we want the text to
            # be stable.  The problem is that textwrap.wrap is deliberately
            # dumb about how many spaces follow a period in prose.
            #
            # We're reflowing at 76 columns, but let's pretend it's 30 for
            # illustration purposes.  If we give textwrap.wrap the following
            # text--ignore the line of 30 dashes, that's just to help you
            # with visualization:
            #
            #  ------------------------------
            #  xxxx xxxx xxxx xxxx xxxx.  xxxx
            #
            # The first textwrap.wrap will return this:
            #  'xxxx xxxx xxxx xxxx xxxx.\nxxxx'
            #
            # If we reflow it again, textwrap will rejoin the lines, but
            # only with one space after the period!  So this time it'll
            # all fit on one line, behold:
            #  ------------------------------
            #  xxxx xxxx xxxx xxxx xxxx. xxxx
            # and so it now returns:
            #  'xxxx xxxx xxxx xxxx xxxx. xxxx'
            #
            # textwrap.wrap supports trying to add two spaces after a peroid:
            #    https://docs.python.org/3/library/textwrap.html#textwrap.TextWrapper.fix_sentence_endings
            # But it doesn't work all that well, because it's not smart enough
            # to do a really good job.
            #
            # Since blurbs are eventually turned into reST and rendered anyway,
            # and since the Zen says 'In the face of ambiguity, refuse the
            # temptation to guess', I don't sweat it.  I run textwrap.wrap
            # twice, so it's stable, and this means occasionally it'll
            # convert two spaces to one space, no big deal.

            paragraph = '\n'.join(
                textwrap.wrap(paragraph.strip(), width=76, **kwargs)
            ).rstrip()
            paragraph = '\n'.join(
                textwrap.wrap(paragraph.strip(), width=76, **kwargs)
            ).rstrip()
            paragraphs2.append(paragraph)
        # don't reflow literal code blocks (I hope)
        dont_reflow = paragraph.endswith('::')
        if subsequent_indent:
            kwargs['initial_indent'] = subsequent_indent
    text = '\n\n'.join(paragraphs2).rstrip()
    if not text.endswith('\n'):
        text += '\n'
    return text


def generate_nonce(body: str) -> str:
    digest = hashlib.md5(body.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest)[0:6].decode('ascii')
