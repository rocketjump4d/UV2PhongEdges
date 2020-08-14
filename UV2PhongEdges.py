# coding=utf-8
# https://github.com/rocketjump4d/UV2PhongEdges
# author: rocketjump4d

import c4d
from c4d import utils


class UV2PhongShading:
    _abcd = tuple("abcd")

    @classmethod
    def SelectUVBorders(cls, obj):
        tuvw = obj.GetTag(c4d.Tuvw)
        nbr = utils.Neighbor()
        nbr.Init(obj)

        # Create empty set for `edgesVV`
        # In this case `edgeVV` means `Edge between Vertex0 and Vertex1 (edgeVertexVertex)`
        # edgeVV is just a tuple(v0, v1), where v0 is index of the first vertex
        # and v1 is the second one
        allEdgesVV = set()

        for i in xrange(obj.GetPointCount()):
            # Find neighbor vertex for this one
            neighborIndexes = nbr.GetPointOneRingPoints(i)

            for ni in neighborIndexes:
                edgeTuple = (i, ni)
                allEdgesVV.add(edgeTuple)

        # At this point I've got a set of all `edgesVV` of the object
        # Something like this:
        # (0, 3)
        # (0, 5)
        # (5, 1)

        doc.AddUndo(c4d.UNDOTYPE_CHANGE_SELECTION, obj)
        obj.GetEdgeS().DeselectAll()

        for edgeVV in allEdgesVV:
            # Find neighbour polygons for this edge
            # I called them polyA and polyB
            polyAIndex, polyBIndex = nbr.GetEdgePolys(edgeVV[0], edgeVV[1])
            polyA = obj.GetPolygon(polyAIndex)

            if polyBIndex is c4d.NOTOK:
                # There is no polyB. It means that this edge is border of the object

                # eiA stands for `Edge Index in polyA for current edgeVV`
                eiA = polyAIndex * 4 + polyA.FindEdge(edgeVV[0], edgeVV[1])
                doc.AddUndo(c4d.UNDOTYPE_CHANGE_SELECTION, obj)
                # Maybe, it'll be better to replace all Select() with SelectAll() after the loop
                obj.GetEdgeS().Select(eiA)
                continue

            polyB = obj.GetPolygon(polyBIndex)

            # piA0 stands for `Point Index in polyA for vertex edgeVV[0]`
            # the same for others
            piA0 = polyA.Find(edgeVV[0])
            piA1 = polyA.Find(edgeVV[1])
            piB0 = polyB.Find(edgeVV[0])
            piB1 = polyB.Find(edgeVV[1])

            # Replace "d" (3) to "c" (2) if polygon is triangle
            if polyA.IsTriangle() and piA0 == 3:
                piA0 = 2
            if polyA.IsTriangle() and piA1 == 3:
                piA1 = 2
            if polyB.IsTriangle() and piB0 == 3:
                piB0 = 2
            if polyB.IsTriangle() and piB1 == 3:
                piB1 = 2

            # Get UV coordinates for each point in each polygon
            uvCoordA0 = tuvw.GetSlow(polyAIndex)[cls._abcd[piA0]]
            uvCoordA1 = tuvw.GetSlow(polyAIndex)[cls._abcd[piA1]]
            uvCoordB0 = tuvw.GetSlow(polyBIndex)[cls._abcd[piB0]]
            uvCoordB1 = tuvw.GetSlow(polyBIndex)[cls._abcd[piB1]]

            if uvCoordA0 != uvCoordB0 or uvCoordA1 != uvCoordB1:
                eiA = polyAIndex * 4 + polyA.FindEdge(edgeVV[0], edgeVV[1])
                eiB = polyBIndex * 4 + polyB.FindEdge(edgeVV[0], edgeVV[1])
                doc.AddUndo(c4d.UNDOTYPE_CHANGE_SELECTION, obj)
                doc.AddUndo(c4d.UNDOTYPE_CHANGE_SELECTION, obj)
                # Maybe, it'll be better to replace all Select() with SelectAll() after the loop
                obj.GetEdgeS().Select(eiA)
                obj.GetEdgeS().Select(eiB)

    @classmethod
    def BreakShading(cls, obj):
        # Save original selected edges
        originalEdgeS = obj.GetEdgeS().GetClone()

        # Smooth (unbreak) all edges
        settings = c4d.BaseContainer()
        doc.AddUndo(c4d.UNDOTYPE_CHANGE_NOCHILDREN, obj)
        utils.SendModelingCommand(c4d.MCOMMAND_UNBREAKPHONG,
                                  [obj],
                                  c4d.MODELINGCOMMANDMODE_ALL,
                                  settings,
                                  doc)

        cls.SelectUVBorders(obj)

        doc.AddUndo(c4d.UNDOTYPE_CHANGE_NOCHILDREN, obj)
        utils.SendModelingCommand(c4d.MCOMMAND_BREAKPHONG,
                                  [obj],
                                  c4d.MODELINGCOMMANDMODE_EDGESELECTION,
                                  settings,
                                  doc)

        doc.AddUndo(c4d.UNDOTYPE_CHANGE_SELECTION, obj)

        # Restore original selected edges
        originalEdgeS.CopyTo(obj.GetEdgeS())


def main():
    objs = doc.GetActiveObjects(0)
    if not objs:
        print("UV2PhongShading: Nothing selected")
        return

    doc.StartUndo()
    for obj in objs:
        if not obj.IsInstanceOf(c4d.Opolygon):
            print("UV2PhongShading: `%s` is not an instance of c4d.PolygonObject" % obj.GetName())
            continue

        if obj.GetTag(c4d.Tuvw) is None:
            print("UV2PhongShading: `%s` hasn't UVW tag" % obj.GetName())
            continue

        UV2PhongShading().BreakShading(obj)

    doc.EndUndo()
    c4d.EventAdd()

if __name__=='__main__':
    main()

