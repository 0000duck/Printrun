#!/usr/bin/python

# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import os
import math
import stltool
import wx
from wx import glcanvas
import gcoder

import pyglet
pyglet.options['debug_gl'] = True

from pyglet.gl import *
from pyglet import gl
from pyglet.graphics.vertexbuffer import create_buffer

from printrun.libtatlin import actors

class wxGLPanel(wx.Panel):
    '''A simple class for using OpenGL with wxPython.'''

    def __init__(self, parent, id, pos = wx.DefaultPosition,
                 size = wx.DefaultSize, style = 0):
        # Forcing a no full repaint to stop flickering
        style = style | wx.NO_FULL_REPAINT_ON_RESIZE
        super(wxGLPanel, self).__init__(parent, id, pos, size, style)

        self.GLinitialized = False
        attribList = (glcanvas.WX_GL_RGBA,  # RGBA
                      glcanvas.WX_GL_DOUBLEBUFFER,  # Double Buffered
                      glcanvas.WX_GL_DEPTH_SIZE, 24)  # 24 bit

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.canvas = glcanvas.GLCanvas(self, attribList = attribList)
        self.sizer.Add(self.canvas, 1, wx.EXPAND)
        self.SetSizer(self.sizer)
        self.sizer.Fit(self)

        # bind events
        self.canvas.Bind(wx.EVT_ERASE_BACKGROUND, self.processEraseBackgroundEvent)
        self.canvas.Bind(wx.EVT_SIZE, self.processSizeEvent)
        self.canvas.Bind(wx.EVT_PAINT, self.processPaintEvent)

    #==========================================================================
    # Canvas Proxy Methods
    #==========================================================================
    def GetGLExtents(self):
        '''Get the extents of the OpenGL canvas.'''
        return self.canvas.GetClientSize()

    def SwapBuffers(self):
        '''Swap the OpenGL buffers.'''
        self.canvas.SwapBuffers()

    #==========================================================================
    # wxPython Window Handlers
    #==========================================================================
    def processEraseBackgroundEvent(self, event):
        '''Process the erase background event.'''
        pass  # Do nothing, to avoid flashing on MSWin

    def processSizeEvent(self, event):
        '''Process the resize event.'''
        if self.canvas.GetContext():
            # Make sure the frame is shown before calling SetCurrent.
            self.Show()
            self.canvas.SetCurrent()
            size = self.GetGLExtents()
            self.winsize = (size.width, size.height)
            self.width, self.height = size.width, size.height
            self.OnReshape(size.width, size.height)
            self.canvas.Refresh(False)
        event.Skip()
        #wx.CallAfter(self.Refresh)

    def processPaintEvent(self, event):
        '''Process the drawing event.'''
        self.canvas.SetCurrent()
 
        if not self.GLinitialized:
            self.OnInitGL()
            self.GLinitialized = True

        self.OnDraw()
        event.Skip()

    def Destroy(self):
        #clean up the pyglet OpenGL context
        self.pygletcontext.destroy()
        #call the super method
        super(wx.Panel, self).Destroy()

    #==========================================================================
    # GLFrame OpenGL Event Handlers
    #==========================================================================
    def OnInitGL(self):
        '''Initialize OpenGL for use in the window.'''
        #create a pyglet context for this panel
        self.pmat = (GLdouble * 16)()
        self.mvmat = (GLdouble * 16)()
        self.pygletcontext = gl.Context(gl.current_context)
        self.pygletcontext.set_current()
        self.dist = 1000
        self.vpmat = None
        #normal gl init
        glClearColor(0.98, 0.98, 0.78, 1)
        glClearDepth(1.0)                # set depth value to 1
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_COLOR_MATERIAL)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self.OnReshape(*self.GetClientSize())

    def OnReshape(self, width, height):
        '''Reshape the OpenGL viewport based on the dimensions of the window.'''
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(60., width / float(height), .1, 1000.)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        #pyglet stuff
        self.vpmat = (GLint * 4)(0, 0, *list(self.GetClientSize()))
        glGetDoublev(GL_PROJECTION_MATRIX, self.pmat)

        # Wrap text to the width of the window
        if self.GLinitialized:
            self.pygletcontext.set_current()
            self.update_object_resize()

    def OnDraw(self, *args, **kwargs):
        """Draw the window."""
        self.pygletcontext.set_current()
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.draw_objects()
        self.SwapBuffers()

    #==========================================================================
    # To be implemented by a sub class
    #==========================================================================
    def create_objects(self):
        '''create opengl objects when opengl is initialized'''
        pass

    def update_object_resize(self):
        '''called when the window recieves only if opengl is initialized'''
        pass

    def draw_objects(self):
        '''called in the middle of ondraw after the buffer has been cleared'''
        pass

def trackball(p1x, p1y, p2x, p2y, r):
    TRACKBALLSIZE = r
#float a[3]; /* Axis of rotation */
#float phi;  /* how much to rotate about axis */
#float p1[3], p2[3], d[3];
#float t;

    if (p1x == p2x and p1y == p2y):
        return [0.0, 0.0, 0.0, 1.0]

    p1 = [p1x, p1y, project_to_sphere(TRACKBALLSIZE, p1x, p1y)]
    p2 = [p2x, p2y, project_to_sphere(TRACKBALLSIZE, p2x, p2y)]
    a = stltool.cross(p2, p1)

    d = map(lambda x, y: x - y, p1, p2)
    t = math.sqrt(sum(map(lambda x: x * x, d))) / (2.0 * TRACKBALLSIZE)

    if (t > 1.0):
        t = 1.0
    if (t < -1.0):
        t = -1.0
    phi = 2.0 * math.asin(t)

    return axis_to_quat(a, phi)


def vec(*args):
    return (GLfloat * len(args))(*args)


def axis_to_quat(a, phi):
    #print a, phi
    lena = math.sqrt(sum(map(lambda x: x * x, a)))
    q = map(lambda x: x * (1 / lena), a)
    q = map(lambda x: x * math.sin(phi / 2.0), q)
    q.append(math.cos(phi / 2.0))
    return q


def build_rotmatrix(q):
    m = (GLdouble * 16)()
    m[0] = 1.0 - 2.0 * (q[1] * q[1] + q[2] * q[2])
    m[1] = 2.0 * (q[0] * q[1] - q[2] * q[3])
    m[2] = 2.0 * (q[2] * q[0] + q[1] * q[3])
    m[3] = 0.0

    m[4] = 2.0 * (q[0] * q[1] + q[2] * q[3])
    m[5] = 1.0 - 2.0 * (q[2] * q[2] + q[0] * q[0])
    m[6] = 2.0 * (q[1] * q[2] - q[0] * q[3])
    m[7] = 0.0

    m[8] = 2.0 * (q[2] * q[0] - q[1] * q[3])
    m[9] = 2.0 * (q[1] * q[2] + q[0] * q[3])
    m[10] = 1.0 - 2.0 * (q[1] * q[1] + q[0] * q[0])
    m[11] = 0.0

    m[12] = 0.0
    m[13] = 0.0
    m[14] = 0.0
    m[15] = 1.0
    return m


def project_to_sphere(r, x, y):
    d = math.sqrt(x * x + y * y)
    if (d < r * 0.70710678118654752440):
        return math.sqrt(r * r - d * d)
    else:
        t = r / 1.41421356237309504880
        return t * t / d


def mulquat(q1, rq):
    return [q1[3] * rq[0] + q1[0] * rq[3] + q1[1] * rq[2] - q1[2] * rq[1],
                    q1[3] * rq[1] + q1[1] * rq[3] + q1[2] * rq[0] - q1[0] * rq[2],
                    q1[3] * rq[2] + q1[2] * rq[3] + q1[0] * rq[1] - q1[1] * rq[0],
                    q1[3] * rq[3] - q1[0] * rq[0] - q1[1] * rq[1] - q1[2] * rq[2]]


class GcodeViewPanel(wxGLPanel):

    def __init__(self, parent, id = wx.ID_ANY):
        super(GcodeViewPanel, self).__init__(parent, id, wx.DefaultPosition, wx.DefaultSize, 0)
        self.batches = []
        self.rot = 0
        self.canvas.Bind(wx.EVT_MOUSE_EVENTS, self.move)
        self.canvas.Bind(wx.EVT_LEFT_DCLICK, self.double)
        self.initialized = 0
        self.canvas.Bind(wx.EVT_MOUSEWHEEL, self.wheel)
        self.parent = parent
        self.initpos = None
        self.dist = 200
        self.bedsize = [200, 200]
        self.transv = [0, 0, -self.dist]
        self.basequat = [0, 0, 0, 1]
        self.mousepos = [0, 0]

    def create_objects(self):
        '''create opengl objects when opengl is initialized'''
        for obj in self.parent.objects:
            if obj.model and obj.model.loaded and not obj.model.initialized:
                obj.model.init()

    def update_object_resize(self):
        '''called when the window recieves only if opengl is initialized'''
        pass

    def draw_objects(self):
        '''called in the middle of ondraw after the buffer has been cleared'''
        if self.vpmat is None:
            return
        self.create_objects()

        if self.rot == 1:
            glLoadIdentity()
            glMultMatrixd(self.mvmat)
        else:
            glLoadIdentity()
            glTranslatef(*self.transv)
        
        glPushMatrix()
        glTranslatef(-self.parent.platform.width/2, -self.parent.platform.depth/2, 0)

        for obj in self.parent.objects:
            if not obj.model or not obj.model.loaded or not obj.model.initialized:
                continue
            glPushMatrix()
            glTranslatef(*(obj.offsets))
            glRotatef(obj.rot, 0.0, 0.0, 1.0)
            glScalef(*obj.scale)

            obj.model.display()
            glPopMatrix()
        glPopMatrix()

    def double(self, event):
        p = event.GetPositionTuple()
        sz = self.GetClientSize()
        v = map(lambda m, w, b: b * m / w, p, sz, self.bedsize)
        v[1] = self.bedsize[1] - v[1]
        v += [300]
        print "Double-click at "+str(v)+" in "
        print self

    def move(self, event):
        """react to mouse actions:
        no mouse: show red mousedrop
        LMB: rotate viewport
        RMB: move viewport
        """
        if event.Dragging() and event.LeftIsDown():
            if self.initpos == None:
                self.initpos = event.GetPositionTuple()
            else:
                #print self.initpos
                p1 = self.initpos
                self.initpos = None
                p2 = event.GetPositionTuple()
                sz = self.GetClientSize()
                p1x = (float(p1[0]) - sz[0] / 2) / (sz[0] / 2)
                p1y = -(float(p1[1]) - sz[1] / 2) / (sz[1] / 2)
                p2x = (float(p2[0]) - sz[0] / 2) / (sz[0] / 2)
                p2y = -(float(p2[1]) - sz[1] / 2) / (sz[1] / 2)
                #print p1x, p1y, p2x, p2y
                quat = trackball(p1x, p1y, p2x, p2y, -self.transv[2] / 250.0)
                if self.rot:
                    self.basequat = mulquat(self.basequat, quat)
                #else:
                glGetDoublev(GL_MODELVIEW_MATRIX, self.mvmat)
                #self.basequat = quatx
                mat = build_rotmatrix(self.basequat)
                glLoadIdentity()
                glTranslatef(self.transv[0], self.transv[1], 0)
                glTranslatef(0, 0, self.transv[2])
                glMultMatrixd(mat)
                glGetDoublev(GL_MODELVIEW_MATRIX, self.mvmat)
                self.rot = 1

        elif event.ButtonUp(wx.MOUSE_BTN_LEFT):
            if self.initpos is not None:
                self.initpos = None
        elif event.ButtonUp(wx.MOUSE_BTN_RIGHT):
            if self.initpos is not None:
                self.initpos = None

        elif event.Dragging() and event.RightIsDown():
            if self.initpos is None:
                self.initpos = event.GetPositionTuple()
            else:
                p1 = self.initpos
                p2 = event.GetPositionTuple()
                sz = self.GetClientSize()
                p1 = list(p1)
                p2 = list(p2)
                p1[1] *= -1
                p2[1] *= -1

                self.transv = map(lambda x, y, z, c: c - self.dist * (x - y) / z,  list(p1) + [0],  list(p2) + [0],  list(sz) + [1],  self.transv)

                glLoadIdentity()
                glTranslatef(self.transv[0], self.transv[1], 0)
                glTranslatef(0, 0, self.transv[2])
                if self.rot:
                    glMultMatrixd(build_rotmatrix(self.basequat))
                glGetDoublev(GL_MODELVIEW_MATRIX, self.mvmat)
                self.rot = 1
                self.initpos = None
        else:
            return
        wx.CallAfter(self.Refresh)

    def wheel(self, event):
        """react to mouse wheel actions:
            without shift: set max layer
            with shift: zoom viewport
        """
        z = event.GetWheelRotation()
        angle = 10
        if event.ShiftDown():
            if not self.parent.model:
                return
            if z > 0:
                max_layers = self.parent.model.max_layers
                current_layer = self.parent.model.num_layers_to_draw
                new_layer = min(max_layers, current_layer + 1)
                self.parent.model.num_layers_to_draw = new_layer
            else:
                current_layer = self.parent.model.num_layers_to_draw
                new_layer = max(1, current_layer - 1)
                self.parent.model.num_layers_to_draw = new_layer
            wx.CallAfter(self.Refresh)
            return
        if z > 0:
            self.transv[2] += angle
        else:
            self.transv[2] -= angle

        glLoadIdentity()
        glTranslatef(*self.transv)
        if self.rot:
            glMultMatrixd(build_rotmatrix(self.basequat))
        glGetDoublev(GL_MODELVIEW_MATRIX, self.mvmat)
        self.rot = 1
        wx.CallAfter(self.Refresh)

    def keypress(self, event):
        """gets keypress events and moves/rotates acive shape"""
        keycode = event.GetKeyCode()
        print keycode
        step = 5
        angle = 18
        if event.ControlDown():
            step = 1
            angle = 1
        #h
        if keycode == 72:
            self.move_shape((-step, 0))
        #l
        if keycode == 76:
            self.move_shape((step, 0))
        #j
        if keycode == 75:
            self.move_shape((0, step))
        #k
        if keycode == 74:
            self.move_shape((0, -step))
        #[
        if keycode == 91:
            self.rotate_shape(-angle)
        #]
        if keycode == 93:
            self.rotate_shape(angle)
        event.Skip()
        wx.CallAfter(self.Refresh)

class GCObject(object):

    def __init__(self, model):
        self.offsets = [0, 0, 0]
        self.rot = 0
        self.curlayer = 0.0
        self.scale = [1.0, 1.0, 1.0]
        self.batch = pyglet.graphics.Batch()
        self.model = model

class GcodeViewFrame(wx.Frame):
    '''A simple class for using OpenGL with wxPython.'''

    def __init__(self, parent, ID, title, build_dimensions, pos = wx.DefaultPosition,
            size = wx.DefaultSize, style = wx.DEFAULT_FRAME_STYLE):
        super(GcodeViewFrame, self).__init__(parent, ID, title, pos, size, style)
        self.refresh_timer = wx.CallLater(100, self.Refresh)
        self.p = self # Hack for backwards compatibility with gviz API
        self.platform = actors.Platform(build_dimensions)
        self.model = None
        self.objects = [GCObject(self.platform), GCObject(None)]
        self.glpanel = GcodeViewPanel(self)

    def set_current_gline(self, gline):
        if gline.is_move and self.model and self.model.loaded:
            self.model.printed_until = gline.gcview_end_vertex
            if not self.refresh_timer.IsRunning():
                self.refresh_timer.Start()

    def addfile(self, gcode = None):
        self.model = actors.GcodeModel()
        if gcode:
            self.model.load_data(gcode)
        self.objects[-1].model = self.model
        wx.CallAfter(self.Refresh)

    def clear(self):
        self.model = None
        self.objects[-1].model = None
        wx.CallAfter(self.Refresh)

    def Show(self, arg = True):
        wx.Frame.Show(self, arg)
        self.SetClientSize((self.GetClientSize()[0], self.GetClientSize()[1] + 1))
        self.SetClientSize((self.GetClientSize()[0], self.GetClientSize()[1] - 1))
        self.Refresh()

    def setlayerindex(self, z):
        model = self.objects[-1].model
        if not model:
            return
        mlk = sorted(m.gc.layers.keys())
        if z > 0 and self.modelindex < len(mlk) - 1:
            self.modelindex += 1
        if z < 0 and self.modelindex > 0:
            self.modelindex -= 1
        m.curlayer = mlk[self.modelindex]
        wx.CallAfter(self.SetTitle, "Gcode view, shift to move. Layer %d, Z = %f" % (self.modelindex, m.curlayer))

if __name__ == "__main__":
    import sys
    app = wx.App(redirect = False)
    build_dimensions = [200, 200, 100, 0, 0, 0]
    frame = GcodeViewFrame(None, wx.ID_ANY, 'Gcode view, shift to move view, mousewheel to set layer', size = (400, 400), build_dimensions = build_dimensions)
    gcode = gcoder.GCode(open(sys.argv[1]))
    frame.addfile(gcode)

    first_move = None
    for i in range(len(gcode.lines)):
        if gcode.lines[i].is_move:
            first_move = gcode.lines[i]
            break
    last_move = None
    for i in range(len(gcode.lines)-1,-1,-1):
        if gcode.lines[i].is_move:
            last_move = gcode.lines[i]
            break
    nsteps = 20
    steptime = 500
    lines = [first_move] + [gcode.lines[int(float(i)*(len(gcode.lines)-1)/nsteps)] for i in range(1, nsteps)] + [last_move]
    current_line = 0
    def setLine():
        global current_line
        frame.set_current_gline(lines[current_line])
        current_line = (current_line + 1) % len(lines)
        timer.Start()
    timer = wx.CallLater(steptime, setLine)
    timer.Start()

    frame.Show(True)
    app.MainLoop()
    app.Destroy()
