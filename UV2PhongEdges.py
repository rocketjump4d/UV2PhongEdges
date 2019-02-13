# https://github.com/rocketjump4d/UV2PhongEdges
# author: rocketjump4d

import c4d
import time
from c4d import utils

# Get point's indexes for edgeInd
def EdgeInd2PointsInd(edgeInd, obj):
    polyInd = int(edgeInd / 4)
    polyEdgeInd = edgeInd - 4 * polyInd
    polygon = obj.GetPolygon(polyInd)

    if polyEdgeInd == 0:
        return polygon.a, polygon.b
    elif polyEdgeInd == 1:
        return polygon.b, polygon.c
    elif polyEdgeInd == 2:
        return polygon.c, polygon.d
    elif polyEdgeInd == 3:
        return polygon.d, polygon.a

# Is an edge placed on UV border?
def isUVBorder(edgeInd, obj, nbr, polyS, workedPoints):
    p1, p2 = EdgeInd2PointsInd(edgeInd, obj)

    # If these point were worked, then skit them
    if {p1, p2} in workedPoints:
        return False

    workedPoints.append({p1, p2})

    polyS.DeselectAll()
    poly1, poly2 = nbr.GetEdgePolys(*EdgeInd2PointsInd(edgeInd, obj))
    polyS.Select(poly1)

    # Object's border
    if poly2 < 0:
        return False

    ## The lines below are the core of this script. And, I guess it's a performance's bottle neck

    # Grow selection. Must be in UVPolygon Mode and Texture View must be opened at least once
    # And obj must be active
    doc.SetActiveObject(obj, c4d.SELECTION_NEW)

    # `CallCommand` cause undo issue :(
    c4d.CallCommand(12558, 12558)

    # Get all polygon's ids after growing
    grownPolygonIds = []
    sel = polyS.GetAll(obj.GetPolygonCount())
    for index, selected in enumerate(sel):
        if selected:
            grownPolygonIds.append(index)

    return poly2 not in grownPolygonIds

def breakPhongEdges(obj):
    settings = c4d.BaseContainer()

    # First step. Unbreak all edges
    doc.AddUndo(c4d.UNDOTYPE_CHANGE_NOCHILDREN, obj)
    utils.SendModelingCommand(command = c4d.MCOMMAND_UNBREAKPHONG,
                                    list = [obj],
                                    mode = c4d.MODELINGCOMMANDMODE_ALL,
                                    bc = settings,
                                    doc = doc)

    # Second. Break Phong shading based on selected edges
    doc.AddUndo(c4d.UNDOTYPE_CHANGE_NOCHILDREN, obj)
    utils.SendModelingCommand(command = c4d.MCOMMAND_BREAKPHONG,
                                    list = [obj],
                                    mode = c4d.MODELINGCOMMANDMODE_EDGESELECTION,
                                    bc = settings,
                                    doc = doc)

# Add/edit Phong tag to represent smooth result
# Important PHONGTAG_PHONG_USEEDGES must be True
def smoothPhongTag(obj):
    phongTag = obj.GetTag(c4d.Tphong)

    # If Phong ag doesn't exist then create new
    if phongTag is None:
        doc.AddUndo(c4d.UNDOTYPE_NEW, obj)
        phongTag = obj.MakeTag(c4d.Tphong)

    # Set parameters
    doc.AddUndo(c4d.UNDOTYPE_CHANGE_NOCHILDREN, phongTag)
    phongTag[c4d.PHONGTAG_PHONG_ANGLELIMIT] = True
    phongTag[c4d.PHONGTAG_PHONG_ANGLE] = 180
    phongTag[c4d.PHONGTAG_PHONG_USEEDGES] = True

# Just open `Texture View` window
def openTextureView():
    c4d.CallCommand(170103) # New Texture View...

def getChildren(obj, data = None) :
    if not data:
        data = list()

    data.append(obj)
    children = obj.GetChildren()
    for child in children:
        getChildren(child, data)

    return data

def do(obj):
    if not obj.IsInstanceOf(c4d.Opolygon):
        print "Skip %s. Only PolygonObjects are allowed" % obj.GetName()
        return

    maxEdgeCount = obj.GetPolygonCount() * 4

    # @todo May be show AbortContinue dialog?
    if maxEdgeCount > 4000:
        print "Object has %s *inner* edges. Script may take some time to work. Be patient :)" % maxEdgeCount

    UVBorders = set()
    nbr = utils.Neighbor()
    nbr.Init(obj)
    polyS = obj.GetPolygonS()
    # Only for optimization purpose
    workedPoints = []
    for edgeInd in range(0, maxEdgeCount):
        if isUVBorder(edgeInd, obj, nbr, polyS, workedPoints):
            UVBorders.add(edgeInd)
    nbr.Flush()

    edges = obj.GetEdgeS()
    doc.AddUndo(c4d.UNDOTYPE_CHANGE_SELECTION, obj)
    edges.DeselectAll()
    for edgeInd in UVBorders:
        edges.Select(edgeInd)

    # Phong Break for selected edges
    breakPhongEdges(obj)

    # Smooth object with Phong tag
    smoothPhongTag(obj)

def main():
    print 'asd'
    activeObjs = doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)

    if len(activeObjs) == 0:
        print "Nothing selected"
        return

    startTime = time.clock()

    # Must be opened at least once per session.
    # @todo Call this func only once, but not each time script is used
    # Find a way to store variable during current session
    openTextureView()

    ## Preparation ##
    # Script must works in UVPolygon's mode
    currentDocMode = doc.GetMode()
    if (currentDocMode != c4d.Muvpolygons):
        doc.SetMode(c4d.Muvpolygons)
    doc.StartUndo()

    ## Main loop ##
    for obj in activeObjs:
        map(do, getChildren(obj))

    ## Finishing ##
    doc.SetMode(currentDocMode)

    # Select back objects
    for i, obj in enumerate(activeObjs):
        doc.SetActiveObject(obj, c4d.SELECTION_NEW if i == 0 else c4d.SELECTION_ADD)

    doc.EndUndo()
    endTime = time.clock()
    print "UV2PhongEdges. Elapsed Time: %s sec" % (endTime - startTime)
    c4d.EventAdd()

if __name__=='__main__':
    main()
