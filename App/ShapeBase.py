# ***************************************************************************
# *   Copyright (c) 2021 David Carter <dcarter@davidcarter.ca>              *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this program; if not, write to the Free Software   *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************
"""Base class for rocket components"""

__title__ = "FreeCAD Rocket Components"
__author__ = "David Carter"
__url__ = "https://www.davesrocketshop.com"

import FreeCAD

from PySide.QtCore import QObject, Signal
from App.Utilities import _err

class ShapeBase(QObject):

    edited = Signal()

    def __init__(self, obj):
        super().__init__()
        self.Type = "RocketComponent"
        self.version = '3.0'

        self._obj = obj
        self._parent = None
        obj.Proxy=self
        self._scratch = {} # None persistent property storage, for import properties and similar

    def __getstate__(self):
        return self.Type, self.version

    def __setstate__(self, state):
        if state:
            self.Type = state[0]
            self.version = state[1]

    def setScratch(self, name, value):
        self._scratch[name] = value

    def getScratch(self, name):
        return self._scratch[name]

    def isScratch(self, name):
        return name in self._scratch

    def setEdited(self):
        self.edited.emit()

    def eligibleChild(self, childType):
        return False

    def setParent(self, obj):
        self._parent = obj

    def getParent(self):
        return self._parent

    def getPrevious(self, obj=None):
        "Previous item along the rocket axis"
        if obj is None:
            if self._parent is not None:
                return self._parent.Proxy.getPrevious(self)
            else:
                return None

        if hasattr(self._obj, "Group"):
            for index in range(len(self._obj.Group)):
                if self._obj.Group[index].Proxy == obj:
                    if index > 0:
                        return self._obj.Group[index - 1]
            return self._obj

        if self._parent is not None:
            return self._parent.Proxy.getPrevious(obj)

        return None

    def getNext(self, obj=None):
        "Next item along the rocket axis"
        print("getNext(%s, %s)" % (self, obj))
        if obj is None:
            if self._parent is not None:
                return self._parent.Proxy.getNext(self)
            else:
                return None

        if hasattr(self._obj, "Group"):
            for index in range(len(self._obj.Group)):
                if self._obj.Group[index].Proxy == obj:
                    if index < len(self._obj.Group) - 1:
                        return self._obj.Group[index + 1]
            return self._obj

        if self._parent is not None:
            return self._parent.Proxy.getNext(obj)

        return None

    def getAxialLength(self):
        # Return the length of this component along the central axis
        return 0.0

    def getForeRadius(self):
        # For placing objects on the outer part of the parent
        return 0.0

    def getAftRadius(self):
        # For placing objects on the outer part of the parent
        return self.getForeRadius()

    def getRadius(self):
        return self.getForeRadius()

    def setRadius(self):
        # Calculate any auto radii
        self.getRadius()

    def resetPlacement(self):
        self._obj.Placement = FreeCAD.Placement()

    def setAxialPosition(self, partBase):
        base = self._obj.Placement.Base
        self._obj.Placement = FreeCAD.Placement(FreeCAD.Vector(partBase, base.y, base.z), FreeCAD.Rotation(0,0,0))

        self.positionChildren(partBase)

    def positionChildren(self, partBase):
        # Dynamic placements
        if hasattr(self._obj, "Group"):
            for child in self._obj.Group:
                child.Proxy.positionChild(child, self._obj, partBase, self.getAxialLength(), self.getForeRadius())

    def positionChild(self, obj, parent, parentBase, parentLength, parentRadius):
        pass

    def getOuterRadius(self):
        return 0.0

    def getInnerRadius(self):
        return 0.0

    def setRadialPosition(self, outerRadius, innerRadius):
        pass

    def moveUp(self):
        # Move the part up in the tree
        print("moveUp(%s)" % (self._obj.Label))
        if self._parent is not None:
            print("\tparent %s" % (self._parent))
            self._parent.Proxy._moveChildUp(self._obj)
        else:
            print("No parent")

    def _moveChildUp(self, obj):
        print("\t_moveChildUp(%s,%s)" % (self._obj.Label, obj.Label))
        if hasattr(self._obj, "Group"):
            index = 0
            for child in self._obj.Group:
                print("\t%s,%s" % (child.Proxy, obj.Proxy))
                if child.Proxy == obj.Proxy:
                    if index > 0:
                        if self._obj.Group[index - 1].Proxy.eligibleChild(obj.Proxy.Type):
                            # Append to the end of the previous entry
                            print("Add to previous")
                            self._obj.Group.pop(index)
                            parent = self._obj.Group[index - 1]
                            obj.Proxy.setParent(parent)
                            parent.addObject(obj)
                        else:
                            print("Swap")
                            # Swap with the previous entry
                            group = self._obj.Group
                            temp = group[index - 1]
                            group[index - 1] = obj
                            group[index] = temp
                            self._obj.Group = group
                            return
                    else:
                        # Add to the grandparent ahead of the parent, or add to the next greater parent
                        if self._parent is not None:
                            grandparent = self._parent
                            parent = self
                            index = 0
                            for child in grandparent.Group:
                                if child.Proxy == parent and grandparent.Proxy.eligibleChild(obj.Proxy.Type):
                                    print("Add to grandparent")

                                    self._obj.Group.pop(0)
                                    group = grandparent.Group
                                    group.insert(index, obj)
                                    grandparent.Group = group
                                    return
                                index += 1
                        else:
                            grandparent = None

                        parent = grandparent
                        while parent is not None:
                            if parent.Proxy.eligibleChild(obj.Proxy.Type):
                                self._obj.Group.pop(0)
                                obj.Proxy.setParent(parent)
                                parent.addObject(obj)
                                return
                            parent = parent._parent
                index += 1

        if self._parent is not None:
            self._parent.Proxy._moveChildUp(self._obj)
        return

    def moveDown(self):
        # Move the part up in the tree
        print("moveDown(%s)" % (self._obj.Label))
        if self._parent is not None:
            print("\tparent %s" % (self._parent))
            self._parent.Proxy._moveChildDown(self._obj)
        else:
            print("No parent")

    def _moveChildDown(self, obj):
        print("\_moveChildDown(%s,%s)" % (self._obj.Label, obj.Label))
        if hasattr(self._obj, "Group"):
            index = 0
            last = len(self._obj.Group) - 1
            for child in self._obj.Group:
                print("\t%s,%s" % (child.Proxy, obj.Proxy))
                if child.Proxy == obj.Proxy:
                    if index < last:
                        print("Swap")
                        # Swap with the previous entry
                        group = self._obj.Group
                        temp = group[index + 1]
                        group[index + 1] = obj
                        group[index] = temp
                        self._obj.Group = group
                        return
                    else:
                        parent = self._parent
                        while parent is not None:
                            if parent.Proxy.eligibleChild(obj.Proxy.Type):
                                self._obj.Group.pop(0)
                                obj.Proxy.setParent(parent)
                                parent.addObject(obj)
                                return
                            parent = parent._parent
                index += 1

        if self._parent is not None:
            self._parent.Proxy._moveChildUp(self._obj)
        return

    # This will be implemented in the derived class
    def execute(self, obj):
        _err("No execute method defined for %s" % (self.__class__.__name__))
