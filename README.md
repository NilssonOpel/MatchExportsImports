# MatchExportsImports
Using **dumpbin.exe** from Visual Studio to get imports and exports from executables and find unused exports

## scripts\get_exports_imports.py:
From the executable files in the --target_dir, take the information from
**dumpbin** **/exports** and **/imports** and gather the data into **exports.json** and **imports.json**

### Examples:
\> get_exports_imports.py -t ../data<br>
\> get_exports_imports.py -t ../data -u just_this.dll<br>


## scripts\find_unused_exports.py
Take the output from **get_exports_imports.py** (**exports.json** and **imports.json**) and
save unreferenced exported functions as **unreferenced_functions.json**

### Examples:
For just ASpecificDLL.dll<br>
\> get_exports_imports.py -t ..\..\refdefs\apps -u ASpecificDLL.dll<br>
\> find_unused_exports.py -t .<br>

or for them all<br>
\> get_exports_imports.py -t ..\..\refdefs\apps<br>
\> find_unused_exports.py -t .<br>
