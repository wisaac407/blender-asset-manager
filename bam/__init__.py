# -*- coding: utf-8 -*-

import sys
__version__ = "1.0"

def main(argv=sys.argv):
    from .cli import main
    sys.exit(main(argv[1:]))

if __name__ == '__main__':
    sys.exit(main(sys.argv))
