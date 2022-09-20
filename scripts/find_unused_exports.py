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
MAGIC_PATH = 'C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\VC\\Tools\\MSVC\\14.33.31629\\bin\\Hostx64\\x64'

DESCRIPTION = f"""
Take the output (exports.json and imports.json) and find the unreferenced
exports
"""
USAGE_EXAMPLE = f"""
Example:
> {MY_NAME} -t ../data
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
    add('-s', '--studio_dir', metavar='VS2022',
        default=MAGIC_PATH,
        help='Where your dumpbin.exe is located')
    add('-t', '--target_dir', metavar='bin-dir',
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
def find_references_to(defining_exe, defined_function, import_references,
    pruning_list_of_defines, options):
    for importing_exe in import_references.keys():
        if options.verbose:
            print(f'{importing_exe = }')
        imported_exes = import_references[importing_exe]
        if not imported_exes:
            if options.verbose:
                print(f'  =no imports=')
            continue
        if not defining_exe in imported_exes:
            if options.verbose:
                print(f'  {defining_exe} is not imported by {importing_exe}')
            continue

        referenced_functions = imported_exes[defining_exe]
        if defined_function in referenced_functions:
            if defined_function in pruning_list_of_defines:
                pruning_list_of_defines.remove(defined_function)
                print(f'  Ref: {defined_function} - first')
            if options.verbose:
                print(f'  Ref: {defined_function} - multiple')

    return pruning_list_of_defines

#-------------------------------------------------------------------------------
def main():
    options = parse_arguments()
    root = options.target_dir
    export_file = os.path.join(root, 'exports.json')
    import_file = os.path.join(root, 'imports.json')
    if not os.path.exists(export_file):
        print(f'No export file found as {exports_file}')
        return 3
    if not os.path.exists(import_file):
        print(f'No import file found as {imports_file}')
        return 3

    exports_defined = load_json_data(export_file)
    import_references = load_json_data(import_file)
    print('Collecting the exports')

    results = {}
    for exporting_exe in exports_defined.keys():
        if options.verbose:
            print(f'{exporting_exe = }')
        defined_functions = exports_defined[exporting_exe]
        if not defined_functions:
            if options.verbose:
                print(f'  =nothing=')
            continue

        # Make a copy for pruning out all references
        pruning_list_of_defined_functions = defined_functions
        for defined_function in defined_functions:
            if options.verbose:
                print(f'  {defined_function}')
            exporting_exe_key = os.path.basename(exporting_exe)
            pruning_list_of_defined_functions = find_references_to(
                exporting_exe_key, defined_function, import_references,
                pruning_list_of_defined_functions, options)

        results[exporting_exe] = pruning_list_of_defined_functions
        # What is left in pruning_list_of_defined_functions are unreferenced

    store_json_data('unreferenced_functions.json', results)
    print('  Saved as unreferenced_functions.json')

    return 0

#-------------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())

