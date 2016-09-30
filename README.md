## Example visualization of the EPGM data model

To run this, an installation of graph-tool is required. Instructions of how to install the precompiled packages of graph-tool can be found on https://graph-tool.skewed.de/download.

If you want to run an example visualization on the data in the example/screenshot_data/ folder, run

python epgmviz.py -g exampleData/screenshot_data/graphs.json -v exampleData/screenshot_data/vertices.json -e exampleData/screenshot_data/edges.json --vl city --el count

To show help and more options, run

python epgmviz.py -h
