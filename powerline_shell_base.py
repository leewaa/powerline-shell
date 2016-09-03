#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import argparse
import os
import sys

py3 = sys.version_info.major == 3


def warn(msg):
    print('[powerline-bash] ', msg)


if py3:
    def unicode(x):
        return x


class Powerline:
    symbols = {
        'compatible': {
            'lock': 'RO',
            'network': 'SSH',
            'separator': u'\u25B6',
            'separator_thin': u'\u276F'
        },
        'patched': {
            'lock': u'\uE0A2',
            'network': u'\uE0A2',
            'separator': u'\uE0B0',
            'separator_thin': u'\uE0B1'
        },
        'flat': {
            'lock': '',
            'network': '',
            'separator': '',
            'separator_thin': ''
        },
    }

    color_templates = {
        'bash': '\\[\\e%s\\]',
        'zsh': '%%{%s%%}',
        'bare': '%s',
    }

    def __init__(self, args, cwd):
        self.args = args
        self.cwd = cwd
        mode, shell = args.mode, args.shell
        self.color_template = self.color_templates[shell]
        self.reset = self.color_template % '[0m'
        self.lock = Powerline.symbols[mode]['lock']
        self.network = Powerline.symbols[mode]['network']
        self.separator = Powerline.symbols[mode]['separator']
        self.separator_thin = Powerline.symbols[mode]['separator_thin']
        self.segments = []

    def color(self, prefix, code):
        if code is None:
            return ''
        else:
            return self.color_template % ('[%s;5;%sm' % (prefix, code))

    def fgcolor(self, code):
        return self.color('38', code)

    def bgcolor(self, code):
        return self.color('48', code)

    def append(self, content, fg, bg, separator=None, separator_fg=None, state_info=None):
        self.segments.append((content, fg, bg,
            separator if separator is not None else self.separator,
            separator_fg if separator_fg is not None else bg,
            True if state_info is not None else False))

    def draw(self):
        text = (''.join(self.draw_segment(i) for i in range(len(self.segments)))
                + self.reset) + ' '
        if py3:
            return text
        else:
            return text.encode('utf-8')

    def draw_segment(self, idx):
        segments_count = len(self.segments)
        segment = self.segments[idx]
        next_segment = self.segments[idx + 1] if idx < len(self.segments)-1 else None
        previous_segment = self.segments[idx - 1] if idx > 0 else None

        s = ''

        # Don't display the branch segment, this is merged in with the repo name segment.
        if len(self.segments) > 3 and idx == 2:
            return ''

        # Branch status
        if segment[5]:
            first = True if previous_segment[5] == False and segment[5] == True else False
            last = True if next_segment[5] == False else False

            if first and last:
                s = ''.join((
                    self.fgcolor(segment[1]),
                    self.bgcolor(segment[2]),
                    '[%s] ' % segment[0],
                    self.bgcolor(next_segment[2]) if next_segment else self.reset,
                    self.fgcolor(segment[4]),
                    segment[3]))

            elif first:
                s = ''.join((
                    self.fgcolor(segment[1]),
                    self.bgcolor(segment[2]),
                    '[',
                    segment[0],
                    self.bgcolor(next_segment[2]) if next_segment else self.reset,
                    self.fgcolor(segment[4])))

            elif last:
                s = ''.join((
                    self.fgcolor(segment[1]),
                    self.bgcolor(segment[2]),
                    segment[0],
                    '] ',
                    self.bgcolor(next_segment[2]) if next_segment else self.reset,
                    self.fgcolor(segment[4]),
                    segment[3]))


            else:
                s = ''.join((
                    self.fgcolor(segment[1]),
                    self.bgcolor(segment[2]),
                    segment[0],
                    self.bgcolor(next_segment[2]) if next_segment else self.reset,
                    self.fgcolor(segment[4])))

        elif segments_count > 3 and idx == 1:
            repo_name = segment[0].rstrip()
            branch_name = next_segment[0].strip()

            if segments_count == 4:
                s = ''.join((
                        self.fgcolor(segment[1]),
                        self.bgcolor(segment[2]),
                        repo_name,
                        self.fgcolor(15),
                        '(',
                        self.fgcolor(next_segment[1]),
                        branch_name,
                        self.fgcolor(15),
                        ') ',
                        self.bgcolor(235),
                        self.fgcolor(segment[4]),
                        segment[3]))

            else:
                s = ''.join((
                        self.fgcolor(segment[1]),
                        self.bgcolor(segment[2]),
                        repo_name,
                        self.fgcolor(15),
                        '(',
                        self.fgcolor(next_segment[1]),
                        branch_name,
                        self.fgcolor(15),
                        ') ',
                        self.bgcolor(segment[2]) if next_segment else self.reset,
                        self.fgcolor(segment[4])))

        # Standard segemnt
        else:
            s = ''.join((
                    self.fgcolor(segment[1]),
                    self.bgcolor(segment[2]),
                    segment[0],
                    self.bgcolor(next_segment[2]) if next_segment else self.reset,
                    self.fgcolor(segment[4]),
                    segment[3]))

        return s


class RepoStats:
    symbols = {
        'detached': u'\u2693',
        'ahead': u'⇡',
        'behind': u'⇣',
        'staged': u'+',
        'not_staged': u'!',
        'untracked': u'?',
        'conflicted': u'x'
    }

    def __init__(self):
        self.ahead = 0
        self.behind = 0
        self.untracked = 0
        self.not_staged = 0
        self.staged = 0
        self.conflicted = 0

    @property
    def dirty(self):
        qualifiers = [
            self.untracked,
            self.not_staged,
            self.staged,
            self.conflicted,
        ]
        return sum(qualifiers) > 0

    def __getitem__(self, _key):
        return getattr(self, _key)

    def n_or_empty(self, _key):
        """Given a string name of one of the properties of this class, returns
        the value of the property as a string when the value is greater than
        1. When it is not greater than one, returns an empty string.

        As an example, if you want to show an icon for untracked files, but you
        only want a number to appear next to the icon when there are more than
        one untracked files, you can do:

            segment = repo_stats.n_or_empty("untracked") + icon_string
        """
        return unicode(self[_key]) if int(self[_key]) > 1 else u''

    def add_to_powerline(self, powerline, color):
        def add(_key):
            if self[_key]:
                s = u"{}{}".format(self.symbols[_key], unicode(self[_key]))

                if (_key == 'ahead'):
                    powerline.append(s, color.AHEAD_FG, color.PATH_BG)
                elif (_key == 'behind'):
                    powerline.append(s, color.BEHIND_FG, color.PATH_BG)
                else:
                    s = u"{}".format(self.symbols[_key])
                    powerline.append(s, color.STATUS_FG, color.PATH_BG, None, None, True)

        add('ahead')
        add('behind')
        add('staged')
        add('not_staged')
        add('untracked')
        add('conflicted')


def get_valid_cwd():
    """ We check if the current working directory is valid or not. Typically
        happens when you checkout a different branch on git that doesn't have
        this directory.
        We return the original cwd because the shell still considers that to be
        the working directory, so returning our guess will confuse people
    """
    # Prefer the PWD environment variable. Python's os.getcwd function follows
    # symbolic links, which is undesirable. But if PWD is not set then fall
    # back to this func
    try:
        cwd = os.getenv('PWD') or os.getcwd()
    except:
        warn("Your current directory is invalid. If you open a ticket at " +
            "https://github.com/milkbikis/powerline-shell/issues/new " +
            "we would love to help fix the issue.")
        sys.stdout.write("> ")
        sys.exit(1)

    parts = cwd.split(os.sep)
    up = cwd
    while parts and not os.path.exists(up):
        parts.pop()
        up = os.sep.join(parts)
    if cwd != up:
        warn("Your current directory is invalid. Lowest valid directory: "
            + up)
    return cwd


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--cwd-mode', action='store',
            help='How to display the current directory', default='fancy',
            choices=['fancy', 'plain', 'dironly'])
    arg_parser.add_argument('--cwd-only', action='store_true',
            help='Deprecated. Use --cwd-mode=dironly')
    arg_parser.add_argument('--cwd-max-depth', action='store', type=int,
            default=5, help='Maximum number of directories to show in path')
    arg_parser.add_argument('--cwd-max-dir-size', action='store', type=int,
            help='Maximum number of letters displayed for each directory in the path')
    arg_parser.add_argument('--colorize-hostname', action='store_true',
            help='Colorize the hostname based on a hash of itself.')
    arg_parser.add_argument('--mode', action='store', default='patched',
            help='The characters used to make separators between segments',
            choices=['patched', 'compatible', 'flat'])
    arg_parser.add_argument('--shell', action='store', default='bash',
            help='Set this to your shell type', choices=['bash', 'zsh', 'bare'])
    arg_parser.add_argument('prev_error', nargs='?', type=int, default=0,
            help='Error code returned by the last command')
    args = arg_parser.parse_args()

    powerline = Powerline(args, get_valid_cwd())
