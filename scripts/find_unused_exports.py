#!/usr/bin/env python3
#
#-------------------------------------------------------------------------------

import argparse
import json
import os
import re
import subprocess
import sys
import textwrap


MY_NAME = os.path.basename(__file__)
DEFAULT_EXP_OUTPUT='exports.json'
DEFAULT_IMP_OUTPUT='imports.json'
DEFAULT_UNREF_OUTPUT='unreferenced_functions.json'


DESCRIPTION = f"""
Take the output from get_exports_imports.py (exports.json and imports.json) and
save unreferenced exported functions as {DEFAULT_UNREF_OUTPUT}
"""
USAGE_EXAMPLE = f"""
Example:
For just ASpecificDLL.dll
> get_exports_imports.py -t ..\\..\\refdefs\\apps -u ASpecificDLL.dll
> {MY_NAME} -t .
or for them all
> get_exports_imports.py -t ..\\..\\refdefs\\apps
> {MY_NAME} -t .

"""

#-------------------------------------------------------------------------------
def parse_arguments():
    parser = argparse.ArgumentParser(
        MY_NAME,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(DESCRIPTION),
        epilog=textwrap.dedent(USAGE_EXAMPLE)
    )
    add = parser.add_argument
    add('-d', '--debug_level', type=int, default=0, help='set debug level')

    add('-q', '--quiet', action='store_true',
        help='be more quiet')
    add('-t', '--target_dir', metavar='DIR',
        default=os.getcwd(),
        help='root path to exports.json and imports.json of interest')
    add('-v', '--verbose', action='store_true',
        help='be more verbose')

    return parser.parse_args()

#-------------------------------------------------------------------------------
'''Get current code page'''
def ccp():
    try:
        return ccp.codepage
    except AttributeError:
        reply = os.popen('cmd /c CHCP').read()
        cp = re.match(r'^.*:\s+(\d*)$', reply)
        if cp:
            ccp.codepage = cp.group(1)
        else:
            ccp.codepage = 'utf-8'
        return ccp.codepage

#-------------------------------------------------------------------------------
def run_process(command, do_check, extra_dir=os.getcwd()):
    try:
        my_command = command
        status = subprocess.run(command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                encoding=ccp(),  # See https://bugs.python.org/issue27179
                                check=do_check)
        if status.returncode == 0:
            reply = status.stdout
        else:
            reply = status.stdout
            reply += status.stderr

    except Exception as e:
        reply = '\n-start of exception-\n'
        reply += f'The command\n>{command}\nthrew an exception'
        if extra_dir:
            reply += f' (standing in directory {extra_dir})'
        reply += f':\n\n'
        reply += f'type:  {type(e)}\n'
        reply += f'text:  {e}\n'
        reply += '\n-end of exception-\n'
        reply += f'stdout: {e.stdout}\n'
        reply += f'stderr: {e.stderr}\n'

    return reply

#-------------------------------------------------------------------------------
def load_json_data(file):
    data = {}
    if not os.path.exists(file):
        return data

    with open(file) as fp:
        try:
            data = json.load(fp)
        except json.decoder.JSONDecodeError:
            pass

    return data

#-------------------------------------------------------------------------------
def store_json_data(file, data):
    with open(file, 'w') as fp:
        json.dump(data, fp, indent=2)

#-------------------------------------------------------------------------------
def find_references_to(defining_exe, import_references,
    pruning_list_of_defines, options):

    for importing_exe in import_references.keys():
        if options.verbose:
            print(f'  - Check if {importing_exe} has imports from ' +
                f'{defining_exe}')
        imported_exes = import_references[importing_exe]
        if not imported_exes:
            if options.verbose:
                print(f'    - had no imported DLL:s')
            continue
        if not defining_exe in imported_exes:
            if options.verbose:
                print(f'    - {defining_exe} not imported by {importing_exe}')
            continue
        if options.verbose:
            print(f'    - {defining_exe} imported by {importing_exe}')

        referenced_functions = imported_exes[defining_exe]
        for current_function in referenced_functions:
            if current_function in pruning_list_of_defines:
                pruning_list_of_defines.remove(current_function)
                if options.verbose:
                    print(f'      - Pruning: {current_function} - first occurence')
                    continue

    return pruning_list_of_defines

#-------------------------------------------------------------------------------
def main():
    options = parse_arguments()
    root = options.target_dir
    export_file = os.path.join(root, 'exports.json')
    import_file = os.path.join(root, 'imports.json')
    if not os.path.exists(export_file):
        print(f'No export file found as {export_file}')
        return 3
    if not os.path.exists(import_file):
        print(f'No import file found as {import_file}')
        return 3

    print('Collecting the exports')
    exports_defined = load_json_data(export_file)
    import_references = load_json_data(import_file)

    results = {}
    print('Pruning out the used exported functions')
    for exporting_exe in exports_defined.keys():
        if options.verbose:
            print(f'Pruning exported functions from {exporting_exe}')
        defined_functions = exports_defined[exporting_exe]
        if not defined_functions:
            if options.verbose:
                print(f'  - had no exported functions')
            continue

        # Make a copy for pruning out all references
        pruning_list_of_defined_functions = defined_functions
        exporting_exe_key = os.path.basename(exporting_exe)
        pruning_list_of_defined_functions = find_references_to(
            exporting_exe_key, import_references,
            pruning_list_of_defined_functions, options)

        # What is left in pruning_list_of_defined_functions are unreferenced
        # functions exported by the exporting_exe
        results[exporting_exe] = pruning_list_of_defined_functions

    store_json_data(DEFAULT_UNREF_OUTPUT, results)
    print(f'  Saved as {DEFAULT_UNREF_OUTPUT}')

    return 0

#-------------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())

