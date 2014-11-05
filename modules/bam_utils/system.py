# ***** BEGIN GPL LICENSE BLOCK *****
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
# ***** END GPL LICENCE BLOCK *****

_USE_COLOR = True
if _USE_COLOR:
    color_codes = {
        'black':        '\033[0;30m',
        'bright_gray':  '\033[0;37m',
        'blue':         '\033[0;34m',
        'white':        '\033[1;37m',
        'green':        '\033[0;32m',
        'bright_blue':  '\033[1;34m',
        'cyan':         '\033[0;36m',
        'bright_green': '\033[1;32m',
        'red':          '\033[0;31m',
        'bright_cyan':  '\033[1;36m',
        'purple':       '\033[0;35m',
        'bright_red':   '\033[1;31m',
        'yellow':       '\033[0;33m',
        'bright_purple':'\033[1;35m',
        'dark_gray':    '\033[1;30m',
        'bright_yellow':'\033[1;33m',
        'normal':       '\033[0m',
    }

    def colorize(msg, color=None):
        return (color_codes[color] + msg + color_codes['normal'])
else:
    def colorize(msg, color=None):
        return msg


def sha1_from_file(fn, block_size=1 << 20):
    with open(fn, 'rb') as f:
        import hashlib
        sha1 = hashlib.new('sha1')
        while True:
            data = f.read(block_size)
            if not data:
                break
            sha1.update(data)
        return sha1.hexdigest()

