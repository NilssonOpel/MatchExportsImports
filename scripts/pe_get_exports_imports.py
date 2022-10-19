#!/usr/bin/env python3
#
#----------------------------------------------------------------------

import argparse
import json
import os
# from   pathlib import Path
import pefile
#import subprocess
import sys
import textwrap

MY_NAME = os.path.basename(__file__)
DEFAULT_EXP_OUTPUT='exports.json'
DEFAULT_IMP_OUTPUT='imports.json'

DESCRIPTION = f"""
Index the executable files in the --target_dir, taking the information from
    the pefile and gather the data into
    {DEFAULT_EXP_OUTPUT} and {DEFAULT_IMP_OUTPUT}
"""
USAGE_EXAMPLE = f"""
Example:
> {MY_NAME} -t ../data
> {MY_NAME} -t ../data -u just_this.dll
"""

#-------------------------------------------------------------------------------
def parse_arguments():
    parser = argparse.ArgumentParser(MY_NAME,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(DESCRIPTION),
        epilog=textwrap.dedent(USAGE_EXAMPLE))
    add = parser.add_argument
    add('-d', '--debug_level', type=int, default=0, help='set debug level')

    add('-t', '--target_dir', metavar='bin_dir',
        required=True,
        help='root path to check (recursively)')
    add('-u', '--unly_one', metavar='dll_under_test.dll',
        help='exports from this exe only')

    add('-q', '--quiet', action='store_true',
        help='be more quiet')
    add('-v', '--verbose', action='store_true',
        help='be more verbose')

    return parser.parse_args()

#-------------------------------------------------------------------------------
def list_all_files(directory, the_chosen_files, ext):
    for root, _dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(ext):
                abs_path = os.path.abspath(os.path.join(root, file))
                the_chosen_files.append(abs_path)

    return the_chosen_files

#-------------------------------------------------------------------------------
def list_all_executables(directory):
    found_exes = []
    list_all_files(directory, found_exes, ".exe")
    list_all_files(directory, found_exes, ".dll")

    return found_exes

#-------------------------------------------------------------------------------
def get_import(file, interesting_dlls, options):
    imports = {}

    try:
        import_dir = [pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]]
        pe = pefile.PE(file, fast_load=True)
        pe.parse_data_directories(directories=import_dir)
    except:
        print(pe.dump_info())
        raise Exception(f'File {file} pefile threw exception on imports\n {sys.exc_info()[0]}')

    try:
        import_directories = pe.DIRECTORY_ENTRY_IMPORT
    except:
        if options.verbose:
            print(f'  {file} had no DIRECTORY_ENTRY_IMPORT')
        return imports

    for entry in import_directories:
        imported_dll = str(entry.dll.decode('utf8'))
        if not imported_dll in interesting_dlls:
#           print(f'  Skipping {imported_dll}')
            continue

        if options.verbose:
            print(f'  Importing from {imported_dll}')

        signatures = []
        for imp in entry.imports:
            if imp.name:
                name_as_string = imp.name.decode('utf8')
                signatures.append(name_as_string)
            else:
                if imp.ordinal:
                    name_as_string = f'Ordinal    {imp.ordinal}'
                    signatures.append(name_as_string)
                else:
                    print(f'({imported_dll} - import {imp} has no name)')
        imports[imported_dll] = signatures

    return imports

#-------------------------------------------------------------------------------
def get_basenames(inputs):
    outputs = []
    for input in inputs:
        outputs.append(os.path.basename(input))

    return outputs

#-------------------------------------------------------------------------------
def get_imports(executables, options):
    imports = {}
    interesting_dlls = get_basenames(executables)
    for exe in executables:
        if options.verbose:
            print(exe)
        imports[os.path.basename(exe)] = get_import(exe, interesting_dlls,
            options)

    return imports

#-------------------------------------------------------------------------------
def get_signatures(file, options):
    signatures = []
    try:
        export_dir = [pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]]
        pe = pefile.PE(file, fast_load=True)
        pe.parse_data_directories(directories=export_dir)
    except:
#        print(pe.dump_info())
        raise Exception(f'File {file} pefile threw exception on exports\n {sys.exc_info()[0]}')

    try:
        export_directory = pe.DIRECTORY_ENTRY_EXPORT
    except:
        if options.verbose:
            print(f'  Found no exports in {file}')
        return signatures

    for export in export_directory.symbols:
        if export.name is None:
            continue
        try:
            name_as_string = export.name.decode('utf8')
            signatures.append(name_as_string)
        except:
            print(f'{export_directory.symbols} has no symbols\n {sys.exc_info()[0]}')
            print(f'{export} is a fail\n {sys.exc_info()[0]}')

    return signatures

#-------------------------------------------------------------------------------
def get_exports(executables, options):
    exports = {}
    for file in executables:
#        file = str(file)
        if options.unly_one and os.path.basename(file) != options.unly_one:
            if options.verbose:
                print(f'Skipping {file} because of -u {options.unly_one}')
            continue

        if not os.path.exists(file):
            print(f'Test file {file} does not exist')
            return

        if options.verbose:
            print(file)
        signatures = get_signatures(file, options)
        exports[file] = signatures

    return exports

#-------------------------------------------------------------------------------
def store_json_data(file, data):
    with open(file, 'w') as fp:
        json.dump(data, fp, indent=2)

#-------------------------------------------------------------------------------
def main(options):
    ret_val = 0
    options = parse_arguments()
    root = options.target_dir

    exes = list_all_executables(root)
    if len(exes) == 0:
        print(f'No executables found in directory {root}')
        return 3

    print('Collecting the exports')
    exports = get_exports(exes, options)
    if not len(exports):
        print(f'Got no exports - giving up')
        return 3
    store_json_data(DEFAULT_EXP_OUTPUT, exports)
    print(f'  Saved as {DEFAULT_EXP_OUTPUT}')

    print('Collecting the imports')
    imports = get_imports(exes, options)
    store_json_data(DEFAULT_IMP_OUTPUT, imports)
    print(f'  Saved as {DEFAULT_IMP_OUTPUT}')

    return ret_val

#-------------------------------------------------------------------------------
if __name__ == '__main__':
    sys.exit(main(parse_arguments()))
