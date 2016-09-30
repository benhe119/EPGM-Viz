#! /usr/bin/env python
# -*- coding: utf-8 -*-

from graph_tool.all import *
from numpy.random import *
from gi.repository import Gtk, Gdk, GdkPixbuf, GObject
import sys, os, os.path
import getopt
import json
import math

# default parameters

# default size of vertices, used when no size property is specified
defaultVertexSize = 230

# font size
# graph-tool scales vertices so that the labels fit, so a big font size could result in vertices of varying sizes
fontSize = 30

# width of the edges
eWidth = 2

# global variable, specifying the last vertex that has been clicked on
previous = None

# command line parsing
arguments = sys.argv[1:]

# boolean value, if True, a vertex are displayed as pie graphs with one pie fraction per graph it is contained in 
drawVerticesAsPies = False

# paths to input files
graphPath = ""
vertexPath = ""
edgePath = ""

# JSON property of the vertices specifying their sizes
sizeProp = ""

# additional properties to be shown in the label
vertexLabelProp = ""
edgeLabelProp = ""

try:
	opts, args = getopt.getopt(arguments, "hpg:v:e:", ["sizeProp=", "vl=", "el="])
except getopt.GetoptError:
	print "usage: python epgmviz.py [options] -g <graphsfile> -v <vertexfile> -e <edgefile>"
	print "Try `python epgmviz.py -h' for more information."
	sys.exit(2)
for opt, arg in opts :
	if opt == "-h" :
		print "usage: python epgmviz.py [options] -g <graphfile> -v <vertexfile> -e <edgefile>"
		print "Options and arguments:"
		print "-h               : print this help message and exit"
		print "-p               : if this flag is set, vertices are displayed as pie graphs"
		print "                   with one pie fraction per graph it is contained in"
		print "-sizeProp <attr> : specified numerical property of the vertices, that"
		print "                   is used to scale the vertices, best results between 1 and 4"
		print "-vl <attr>       : additional attribute to be shown in vertex label"
		print "-el <attr>	: additional attribute to be shown in edge label"
		print "-g <graphfile>   : path to the JSON file containing the graph information"
		print "-v <vertexfile>  : path to the JSON file containing the vertex information"
		print "-e <edgefile>    : path to the JSON file containing the edge information"
		sys.exit()
	if opt == "-p" :
		drawVerticesAsPies = True		
	elif opt == "--sizeProp" :
		sizeProp = arg
	elif opt == "--vl" :
		vertexLabelProp = arg
	elif opt == "--el" :
		edgeLabelProp = arg
	elif opt == "-g" :
		graphPath = arg
	elif opt == "-v" :
		vertexPath = arg
	elif opt == "-e" :
		edgePath = arg
	
if graphPath == "" or vertexPath == "" or edgePath == "" :
	print "Please specify valid file paths."
	print "usage: python epgmviz.py [options] -g <graphfile> -v <vertexfile> -e <edgefile>"
	print "Try `python epgmviz.py -h' for more information."
	sys.exit(2)

# global graph variables 
graph = Graph()
graphLabels = {}
graphList = []
graphColors = {}
graphCount = 0

# global vertex variables
vertexDict = {}
vertexProps = {}
vertexLabels = {}

# default vertex color if drawVerticesAsPies == False
defaultVertexColor = [0.4019607843137255, 0.5941176470588235, 0.7274509803921568, 1.0]

# default pie fraction colors if drawVerticesAsPies == True
defaultPieColors = [
	(0.5529411764705883, 0.8274509803921568, 0.7803921568627451, 1.0),
        (0.7450980392156863, 0.7294117647058823, 0.8549019607843137, 1.0),
        (0.984313725490196, 0.5019607843137255, 0.4470588235294118, 1.0),
        (0.5019607843137255, 0.6941176470588235, 0.8274509803921568, 1.0),
        (0.9921568627450981, 0.7058823529411765, 0.3843137254901961, 1.0),
        (0.7019607843137254, 0.8705882352941177, 0.4117647058823529, 1.0),
        (0.9882352941176471, 0.803921568627451, 0.8980392156862745, 1.0),
        (0.8509803921568627, 0.8509803921568627, 0.8509803921568627, 1.0),
        (0.7372549019607844, 0.5019607843137255, 0.7411764705882353, 1.0),
        (0.8, 0.9215686274509803, 0.7725490196078432, 1.0),
        (1.0, 0.9294117647058824, 0.43529411764705883, 1.0)]

# vertex attributes
vLabels = graph.new_vertex_property("string")
vColors = graph.new_vertex_property("vector<double>")
vertexSize = graph.new_vertex_property("int")
vertexHighlightWidth = graph.new_vertex_property("double")
pieFractions = graph.new_vertex_property("vector<double>")

# edge attributes
eLabels = graph.new_edge_property("string")
eColors = graph.new_edge_property("vector<double>")


table = Gtk.Table(1,1,False)

# read graphs

input = open(graphPath, "r")
while(True):
	
	line = input.readline()
	if (line == "") :
		break

	object = json.loads(line)
	id = object["id"]
	label = object["meta"]["label"]
	# TODO: implement pie fraction color legend, mapping colors to graph labels	
	graphLabels[id] = label
	graphList.append(id)	

	graphCount = graphCount + 1 
	
# read vertices

vertexCount = 0
input = open(vertexPath, "r")
while(True): 	
	
	line = input.readline()
	if (line == "") :
		break
	
	object = json.loads(line)
	id = object["id"]
	# label and graph list are special properties
	label = object["meta"]["label"]
	graphs = object["meta"]["graphs"]

	# build a dictionary, mapping vertex id in JSON to internal vertex id 
	vertexDict[id] = vertexCount
	vertexCount = vertexCount + 1
	
	# add a new vertex to the graph
	vertex = graph.add_vertex()
	
	# this is necessary to distinguish between labels of the drawn vertices, and the label property
	# in the first row of the property table
	vertexLabels[vertex] = label	

	vertexSize[vertex] = defaultVertexSize

	# sort the properties by key name
	propKeys = sorted(object["data"].keys())

	# for each vertex, build a property list and insert it into a dictionary
	for prop in propKeys :
		if vertex not in vertexProps :
			vertexProps[vertex] = []
		value = object["data"][prop]
		if isinstance(value, unicode) :
			value = value.encode("utf-8")
		value = str(value)
		vertexProps[vertex].append((prop, value))

	# the area covered by one vertex scales linear with the value of the size property if one is specified
	if sizeProp != "" :
		if "count" in object["data"] :
			vertexSize[vertex] = int(math.sqrt(object["data"][sizeProp])*defaultVertexSize) 
	
	vColors[vertex] = defaultVertexColor
	# by default, the vertex label is defined by the label property
	
	vLabels[vertex] = label 
	if vertexLabelProp != "" :
		vLabels[vertex] = label + " (" + str(object["data"][vertexLabelProp]) + ") "

	# compute the size of the fractions if vertices shall be drawn as pies	
	if drawVerticesAsPies :	 
		fractions = []
		for g in range(graphCount) :
			graphId = graphList[g]
			if graphId in graphs :
				fractions.append(1/len(graphs)-0.1)
			else :
				fractions.append(0)	
		pieFractions[vertex] = fractions
	
	# vertices are not highlighted with a colored aura when the mouse moves over them
	vertexHighlightWidth[vertex] = 0.0



# read edges
input = open(edgePath, "r")
while(True):

	line = input.readline()
	if (line == "" ) :
		break

	object = json.loads(line)
	sourceId = object["source"]
	targetId = object["target"]

	# the label is a special property 
	label = object["meta"]["label"]

	# get source and target vertex from the dictionary
	source = vertexDict[sourceId]
	target = vertexDict[targetId]

	# add a new edge to the graph
	edge = graph.add_edge(source, target)
	eColors[edge] = [0.1, 0.1, 0.1, 1]

	# by default the vertex label is defined by the label property 
	eLabels[edge] = label 
	if edgeLabelProp != "" :
		eLabels[edge] = label + " (" + str(object["data"][edgeLabelProp]) + ") "

# compute the initial layout of the graph
pos1 = sfdp_layout(graph, p=10, C=0.9)

# decide how to draw the graph, then draw it
if drawVerticesAsPies == True :
		graphWidget = GraphWidget(graph, pos1,
				vertex_size = vertexSize,
				vertex_shape = "pie",
				vertex_pie_fractions = pieFractions,
				vertex_text = vLabels,
				vertex_font_size = fontSize,
				vertex_font_family = "georgia",
				vertex_pen_width = vertexHighlightWidth,
				vertex_pie_colors = defaultPieColors,
				edge_text = eLabels,
				edge_font_size = fontSize,
				edge_font_family = "georgia",
				edge_pen_width = eWidth,
				edge_color = eColors,
				edge_text_color = eColors,
				edge_marker_size = 20,
				# the halo and highlight color changes are disabled
				vertex_halo_color = [0, 0, 0, 0],
				highlight_color = [0, 0, 0, 0])
			
else :
		graphWidget = GraphWidget(graph, pos1,
				vertex_size = vertexSize,
				vertex_text = vLabels,
				vertex_font_size = fontSize,
				vertex_font_family = "arial",
				vertex_font_weight = 1.0,
				vertex_pen_width = 0,
				vertex_fill_color = vColors,
				edge_text = eLabels,
				edge_font_size = fontSize,
				edge_font_family = "arial",
				edge_font_weight = 1.0,
				edge_pen_width = eWidth,
				edge_color = eColors,
				edge_text_color = eColors,
				edge_marker_size = 20,
				# the halo and highlight color changes are disabled
				vertex_halo_color = [0, 0, 0, 0],
				highlight_color = [0, 0, 0, 0])


def update_state():
	# redraw the graph whenever anything changes
	# can be removed if there are performance issues
	graphWidget.regenerate_surface()
	graphWidget.queue_draw()
	return True
	
def update_click(widget, event):
	# defines behaviour when graph widget is being clicked on
	global graph
	global table 
	global previous

	# get the vertex nearest to the position that has been clicked on
	# as far as i know, it is currently not possible to find out if an edge has been clicked
	vertex = widget.picked	

	# this should only be called if the user clicked with the right mouse button
	if vertex is False :
		# reset hue of vertices
		for v in graph.vertices() :
			vColors[v][3] = 1.0
		# hide property table
		table.hide()	
		return
	else:
		# show property table
		table.show()

	# if the vertex has properties, build up the property table
	if vertex in vertexProps :	

		props = vertexProps[vertex]

		# increased by one because the label needs an extra row
		requiredRows = len(props)+1

		# clear the table
		for l in table.get_children() :
			table.remove(l)


		# the first row is always the vertex label
		label0 = Gtk.Label()
		label0.set_markup("<b><span size=\"" + str(fontSize*786) + "\">Label:</span></b>")
		table.attach(label0, 0, 1, 0, 1)

		label1 = Gtk.Label()
		label1.set_markup("<span size=\"" + str(fontSize*786) + "\">" + vertexLabels[vertex] + "</span>")
		table.attach(label1, 1, 2, 0, 1)

		# all other rows are the vertex properties, ordered by key name
		for i in range(1, requiredRows) :
			keyLabel = Gtk.Label()
			keyLabel.set_markup("<b><span size=\"" + str(fontSize*786) + "\">" + props[i-1][0] + ":</span></b>")
			table.attach(keyLabel, 0, 1, i, i+1)	
			
			valueLabel = Gtk.Label()
			valueLabel.set_markup("<span size=\"" + str(fontSize*786) + "\">" + props[i-1][1] + "</span>")
			table.attach(valueLabel, 1, 2, i, i+1)
	
	# show the table and all its child widgets
	table.show_all()

	# reduce the hue of all vertices but the one that was clicked
	vertexHighlightWidth[vertex] = 2
	if previous != None :
		vertexHighlightWidth[previous] = 0
	previous = vertex	
	
	for v in graph.vertices() :
		vColors[v][3] = 0.15

	vColors[vertex][3] = 1.0
		
	

orig_pack_start = Gtk.Box.pack_start
# convenience function for packing in containers 
def pack_start(self, child, expand=True, fill=True, padding=0):
    orig_pack_start(self, child, expand, fill, padding)
Gtk.Box.pack_start = pack_start

cid = GObject.idle_add(update_state)

# build the window
vbox = Gtk.VBox()

hbox = Gtk.HBox()

border = Gtk.Label("   ")

table.set_row_spacings(4)
table.set_col_spacings(4)

backgroundBox = Gtk.EventBox()
backgroundBox.set_visible_window(True)
backgroundBox.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#F0F0F0"))
backgroundBox.add(table)

tableVBox = Gtk.VBox()
tableVBox.pack_start(backgroundBox, False, False)

hbox.pack_start(border, False, False)
hbox.pack_start(tableVBox, False, False)
hbox.pack_start(graphWidget)

graphWidget.connect("button_press_event", update_click)

window = Gtk.Window()
window.set_title("EPGM-Viz")

tableVBox.set_size_request(150,100)

window.add(hbox)

window.resize(1000,800)

window.connect("delete_event", Gtk.main_quit)

window.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#FFFFFF"))

window.show_all()

Gtk.main()
