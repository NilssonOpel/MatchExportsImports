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
DEFAULT_EXP_OUTPUT='exports.json'
DEFAULT_IMP_OUTPUT='imports.json'

DESCRIPTION = f"""
Index the executable files in the --target_dir, taking the information from
    dumpbin /exports and /imports and gather the data into
    {DEFAULT_EXP_OUTPUT} and {DEFAULT_IMP_OUTPUT}
  --studio_dir may for example be
        {MAGIC_PATH}
"""
USAGE_EXAMPLE = f"""
Example:
> {MY_NAME} -t ../data
> {MY_NAME} -t ../data -u just_this.dll
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
    add('-b', '--backup', action='store_true',
        help='make a backup of the .pdb file as <path>.orig')
    add('-d', '--debug_level', type=int, default=0, help='set debug level')

    add('-q', '--quiet', action='store_true',
        help='be more quiet')
    add('-s', '--studio_dir', metavar='VS2022',
        default=MAGIC_PATH,
        help='Where your dumpbin.exe is located')
    add('-t', '--target_dir', metavar='bin-dir',
        required=True,
        help='root path to check (recursively)')
    add('-u', '--unly_one', metavar='dll_under_test.dll',
        help='exports from this exe only')

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
def parse_out_the_exports(the_exe, the_input, options):
    list_of_functions = []
    curr_line = 0
    no_of_lines = len(the_input)

    while curr_line < no_of_lines:
        line = the_input[curr_line]
        # Skip until line after 'ordinal'
        if line.startswith('    ordinal'):
            break
        curr_line += 1

    curr_line = curr_line + 2
    if curr_line >= no_of_lines:
        if options.verbose:
            print(f'Found no exports in {the_exe}')
        return

    while curr_line < no_of_lines:
        line = the_input[curr_line]
        # Read until an empty line
        if len(line) == 0:
            break
        func = line[26:]
#        print(func)
        list_of_functions.append(func)
        curr_line += 1

    return list_of_functions

#-------------------------------------------------------------------------------
def get_exports(path_of_exe, options):
    commando = f'{options.dumpbin} /exports {path_of_exe}'
    if options.verbose:
        print(commando)
    output = run_process(commando, True)
    exported_functions = parse_out_the_exports(path_of_exe, output.splitlines(),
        options)
    return exported_functions

#-------------------------------------------------------------------------------
def get_next_imported_dll(the_input, curr_line, no_of_lines):
    # Eat until we find some char at pos 4
    empty_lines = 0
    while curr_line < no_of_lines:
        line = the_input[curr_line]
        if len(line) == 0:
            empty_lines += 1
            if empty_lines == 2:
                return curr_line + 1
        curr_line += 1
    return curr_line


#-------------------------------------------------------------------------------
def parse_out_the_imports(the_exe, interesting_exes, the_input, options):
    dict_of_imports = {}

    curr_line = 0
    no_of_lines = len(the_input)

    while curr_line < no_of_lines:
        line = the_input[curr_line]
        # Skip until line after 'Section contains'
        if line.startswith('  Section contains'):
            break
        curr_line += 1

    curr_line = curr_line + 2
    if curr_line >= no_of_lines:
        if options.verbose:
            print(f'Found no start of imports in {the_exe}')
        return


    if options.verbose:
        print(the_exe)
    # Now get the name(s) of the DLL(s) that we import from
    while curr_line < no_of_lines:
        line = the_input[curr_line]
        # Have reached the end?
        if line[2:] == 'Summary':
            break
        if line[2:].startswith('Section contains the'):
            break

        # Take the name of the DLL that the_exe is importing from
        imported_dll = line[4:]

        if imported_dll not in interesting_exes:
#            print(f'  Skipping {imported_dll}')
            curr_line = get_next_imported_dll(the_input, curr_line, no_of_lines)
            line = the_input[curr_line]
            if line[2:] == 'Summary':
                break
            continue

        if options.verbose:
            print(f'  Importing from {imported_dll}')
        curr_line += 6

        # Get the functions
        list_of_functions = []
        while curr_line < no_of_lines:
            line = the_input[curr_line]
            if len(line) == 0:
                break
            func = line[29:]
#            print(f'    Function: {func}')
            list_of_functions.append(func)
            curr_line += 1

        dict_of_imports[imported_dll] = list_of_functions

        # Get to the next dll-name
        curr_line += 1
        line = the_input[curr_line]
        if line[2:] == 'Summary':
            break

    return dict_of_imports

#-------------------------------------------------------------------------------
def get_imports(path_of_exe, imports, interesting_exes, options):
    commando = f'"{options.dumpbin}" /imports {path_of_exe}'
    if options.verbose:
        print(commando)
    output = run_process(commando, True)
    imported_from_dlls = parse_out_the_imports(path_of_exe, interesting_exes,
        output.splitlines(), options)
    return imported_from_dlls

#-------------------------------------------------------------------------------
def get_basenames(inputs):
    outputs = []
    for input in inputs:
        outputs.append(os.path.basename(input))

    return outputs

#-------------------------------------------------------------------------------
def store_json_data(file, data):
    with open(file, 'w') as fp:
        json.dump(data, fp, indent=2)

#-------------------------------------------------------------------------------
def main():
    options = parse_arguments()
    root = options.target_dir
    dumpbin = os.path.join(options.studio_dir, 'dumpbin.exe')
    if not os.path.exists(dumpbin):
        print(f'No dumpbin found as {dumpbin}')
        return 3
    options.dumpbin = dumpbin

    exes = list_all_executables(root)
    if len(exes) == 0:
        print(f'No executables found in directory {root}')
        return 3

    exports = {}
    print('Collecting the exports')
    for exe in exes:
        if options.unly_one and os.path.basename(exe) != options.unly_one:
            if options.verbose:
                print(f'Skipping {exe} because of -u {options.unly_one}')
            continue
        if options.verbose:
            print(exe)
        exports[exe] = get_exports(exe, options)

    if not len(exports):
        print(f'Got no exports - giving up')
        return 3
    store_json_data(DEFAULT_EXP_OUTPUT, exports)
    print(f'  Saved as {DEFAULT_EXP_OUTPUT}')

    # The go another round to insert the imports
    imports = {}
    interesting_dll_names = get_basenames(exes)
    print('Collecting the imports')
    for exe in exes:
        if options.verbose:
            print(exe)
        imports_from_dlls = get_imports(exe, imports, interesting_dll_names, options)
        imports[os.path.basename(exe)] = imports_from_dlls

    store_json_data(DEFAULT_IMP_OUTPUT, imports)
    print(f'  Saved as {DEFAULT_IMP_OUTPUT}')
    return 0

#-------------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())

