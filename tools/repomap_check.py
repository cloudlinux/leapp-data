"""
Simple checker to make sure that repomap is valid.
"""

import json
import argparse


def _check_path(path):
    with open(path) as f:
        try:
            json.load(f)
        except json.decoder.JSONDecodeError:
            print("FAIL. Invalid json: %s" % path)
            return False
        else:
            print("OK")
            return True


def main(args):

    errors = 0
    for file in args.path:
        print("Checking %s" % file, end='... ')

        # so far checks only for json validity
        # add other checks when other problems happen
        errors += 0 if _check_path(file) else 1

    return errors


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="+")

    args = parser.parse_args()

    errors = main(args)
    exit(errors)
