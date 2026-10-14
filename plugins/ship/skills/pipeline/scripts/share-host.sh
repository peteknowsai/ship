#!/bin/bash
# Chrome's native messaging entry for the Ship tabs Share button (com.pete.ship.share).
# Chrome's PATH is bare, so no dirname: the shell strips the file name itself.
exec /usr/bin/python3 "${0%/*}/share.py" host
