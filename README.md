# MatchExportsImports
Using **dumpbin.exe** from Visual Studio to get imports and exports from executables and find unused exports

## scripts\get_exports_imports.py:
From the executable files in the --target_dir, take the information from
**dumpbin** **/exports** and **/imports** and gather the data into **exports.json** and **imports.json**

### Examples:
> get_exports_imports.py -t ../data
> get_exports_imports.py -t ../data -u just_this.dll


## scripts\find_unused_exports.py
Take the output from **get_exports_imports.py** (**exports.json** and **imports.json**) and
save unreferenced exported functions as **unreferenced_functions.json**

### Examples:
For just ASpecificDLL.dll
> get_exports_imports.py -t ..\..\refdefs\apps -u ASpecificDLL.dll
> find_unused_exports.py -t .

or for them all
> get_exports_imports.py -t ..\..\refdefs\apps
> find_unused_exports.py -t .