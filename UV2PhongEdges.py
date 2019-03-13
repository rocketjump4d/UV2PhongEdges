# https://github.com/rocketjump4d/UV2PhongEdges
# author: rocketjump4d

import c4d
import time
from c4d import utils

class UV2PhongEdges:
    def __init__(self, doc):
        self._doc = doc

    def StoreCurrentState(self):
        # Script must works in UVPolygon's mode
        self._currentDocMode = doc.GetMode()
        if (self._currentDocMode != c4d.Muvpolygons):
            doc.SetMode(c4d.Muvpolygons)

    def RestoreState(self):
        doc.SetMode(self._currentDocMode)

    # Get point's indexes for edgeInd
    def EdgeInd2PointsInd(self, edgeInd, obj):
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
    def IsUVBorder(self, edgeInd, obj, nbr, polyS):
        polyS.DeselectAll()
        polyInd1, polyInd2 = nbr.GetEdgePolys(*self.EdgeInd2PointsInd(edgeInd, obj))
        polyS.Select(polyInd1)

        # If polygon's index equals -1 then current edge has only 1 polygon
        # And as a result it's a object's border. I mean, there's nothing else
        # Only pure void. Object is finished.
        if polyInd2 < 0:
            return False
    
        ## The lines below are the core of this script. And, I guess it's a performance's bottle neck
    
        # Grow selection. Must be in UVPolygon Mode and Texture View must be opened at least once
        # And obj must be active
        self._doc.SetActiveObject(obj, c4d.SELECTION_NEW)
    
        # `CallCommand` cause undo issue :(
        c4d.CallCommand(12558, 12558)
    
        # Get all polygon's ids after growing
        grownPolygonIds = []
        sel = polyS.GetAll(obj.GetPolygonCount())
        for index, selected in enumerate(sel):
            if selected:
                grownPolygonIds.append(index)
    
        return polyInd2 not in grownPolygonIds
    
    def BreakPhongEdges(self, obj):
        settings = c4d.BaseContainer()
    
        # First step. Unbreak all edges
        self._doc.AddUndo(c4d.UNDOTYPE_CHANGE_NOCHILDREN, obj)
        utils.SendModelingCommand(c4d.MCOMMAND_UNBREAKPHONG,
                                  [obj],
                                  c4d.MODELINGCOMMANDMODE_ALL,
                                  settings,
                                  self._doc)
    
        # Second. Break Phong shading based on selected edges
        self._doc.AddUndo(c4d.UNDOTYPE_CHANGE_NOCHILDREN, obj)
        utils.SendModelingCommand(c4d.MCOMMAND_BREAKPHONG,
                                  [obj],
                                  c4d.MODELINGCOMMANDMODE_EDGESELECTION,
                                  settings,
                                  self._doc)
    
    # Add/edit Phong tag to represent smooth result
    # Important PHONGTAG_PHONG_USEEDGES must be True
    def SmoothPhongTag(self, obj):
        phongTag = obj.GetTag(c4d.Tphong)
    
        # If Phong ag doesn't exist then create new
        if phongTag is None:
            self._doc.AddUndo(c4d.UNDOTYPE_NEW, obj)
            phongTag = obj.MakeTag(c4d.Tphong)
    
        # Set parameters
        self._doc.AddUndo(c4d.UNDOTYPE_CHANGE_NOCHILDREN, phongTag)
        phongTag[c4d.PHONGTAG_PHONG_ANGLELIMIT] = True
        phongTag[c4d.PHONGTAG_PHONG_ANGLE] = 180
        phongTag[c4d.PHONGTAG_PHONG_USEEDGES] = True
    
    # Just open `Texture View` window
    def OpenTextureView(self):
        c4d.CallCommand(170103) # New Texture View...

    def Do(self, obj):
        if not obj.IsInstanceOf(c4d.Opolygon):
            print "Skip %s. Only PolygonObjects are allowed" % obj.GetName()
            return
    
        if obj.GetTag(c4d.Tuvw) is None:
            print "Skip %s. It hasn't UVW tag" % obj.GetName()
            return
    
        # Save original polygons and edges selection
        polyS = obj.GetPolygonS()
        originPolyS = polyS.GetClone()
        edgeS = obj.GetEdgeS()
        originalEdgeS = edgeS.GetClone()
    
        maxEdgeCount = obj.GetPolygonCount() * 4
    
        # @todo May be show AbortContinue dialog?
        if maxEdgeCount > 4000:
            print "Object `%s` has %s *inner* edges. Script may take some time to work. Be patient :)"\
                  % (obj.GetName(), maxEdgeCount)
    
        UVBorders = set()
        nbr = utils.Neighbor()
        nbr.Init(obj)
        for edgeInd in range(0, maxEdgeCount):
            if self.IsUVBorder(edgeInd, obj, nbr, polyS):
                UVBorders.add(edgeInd)
        nbr.Flush()
    
        edges = obj.GetEdgeS()
        self._doc.AddUndo(c4d.UNDOTYPE_CHANGE_SELECTION, obj)
        edges.DeselectAll()
        for edgeInd in UVBorders:
            edges.Select(edgeInd)
    
        # Phong Break for selected edges
        self.BreakPhongEdges(obj)
    
        # Smooth object with Phong tag
        self.SmoothPhongTag(obj)
    
        # Restore original elements selections
        polyS.SetAll(originPolyS.GetAll(obj.GetPolygonCount()))
        edgeS.SetAll(originalEdgeS.GetAll(maxEdgeCount))

def getChildren(obj, data=None):
    if not data:
        data = list()

    data.append(obj)
    children = obj.GetChildren()
    for child in children:
        getChildren(child, data)

    return data

def main():
    global doc

    activeObjs = doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)

    if len(activeObjs) == 0:
        print "Nothing selected"
        return

    startTime = time.clock()

    ## Preparation ##
    doc.StartUndo()

        # Must be opened at least once per session.
    # @todo Call this func only once, but not each time script is used
    # Find a way to store variable during current session
    uv = UV2PhongEdges(doc)

    uv.StoreCurrentState()
    uv.OpenTextureView()
    
    ## Main loop ##
    for obj in activeObjs:
        map(uv.Do, getChildren(obj))

    ## Finishing ##
    uv.RestoreState()

    # Restore selected object
    for i, obj in enumerate(activeObjs):
        doc.SetActiveObject(obj, c4d.SELECTION_NEW if i == 0 else c4d.SELECTION_ADD)


    doc.EndUndo()
    endTime = time.clock()
    print "UV2PhongEdges. Elapsed Time: %s sec" % (endTime - startTime)
    c4d.EventAdd()

if __name__=='__main__':
    main()
