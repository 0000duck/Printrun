import wx, os, math
from bufferedcanvas import *

def imagefile(filename):
    return os.path.join(os.path.dirname(__file__), "images", filename)

def sign(n):
    if n < 0: return -1
    elif n > 0: return 1
    else: return 0

class XYButtons(BufferedCanvas):
    keypad_positions = {
        0: (126, 126),
        1: (100, 100),
        2: (78, 78),
        3: (60, 60)
    }
    concentric_circle_radii = [15, 55, 86, 117, 142]
    center = (166, 164)

    def __init__(self, parent, moveCallback=None, homeCallback=None, ID=-1):
        self.bg_bmp = wx.Image(imagefile("control_xy.png"),wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.keypad_bmp = wx.Image(imagefile("arrow_keys.png"),wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.keypad_idx = 0
        self.orderOfMagnitudeIdx = 0
        self.quadrant = None
        self.concentric = None
        self.moveCallback = moveCallback
        self.homeCallback = homeCallback

        BufferedCanvas.__init__(self, parent, ID)

        self.SetSize(wx.Size(335, 328))

        # Set up mouse and keyboard event capture
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDown)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeaveWindow)
        parent.Bind(wx.EVT_CHAR_HOOK, self.onKey)
    
    def onKey(self, evt):
        if evt.GetKeyCode() == wx.WXK_TAB:
            self.setKeypadIndex(self.rotateKeypadIndex())
        elif evt.GetKeyCode() == wx.WXK_UP:
            self.quadrant = 1
        elif evt.GetKeyCode() == wx.WXK_DOWN:
            self.quadrant = 3
        elif evt.GetKeyCode() == wx.WXK_LEFT:
            self.quadrant = 2
        elif evt.GetKeyCode() == wx.WXK_RIGHT:
            self.quadrant = 0
        else:
            evt.Skip()
            return
        if self.moveCallback:
            self.concentric = self.keypad_idx
            x, y = self.getMovement()
            self.moveCallback(x, y)

    
    def rotateKeypadIndex(self):
        idx = self.keypad_idx + 1
        if idx > 2: idx = 0
        return idx
    
    def setKeypadIndex(self, idx):
        self.keypad_idx = idx
        self.update()
        # self.keypad_bmp.Move(XYButtons.keypad_positions[self.keypad_idx])
    
    def getMovement(self):
        xdir = [1, 0, -1, 0][self.quadrant]
        ydir = [0, 1, 0, -1][self.quadrant]
        magnitude = math.pow(10, self.concentric-1)
        return (magnitude * xdir, magnitude * ydir)
    
    def lookupConcentric(self, radius):
        idx = -1
        for r in XYButtons.concentric_circle_radii:
            if radius < r:
                return idx
            idx += 1
        return None

    def getQuadrantConcentricFromPosition(self, pos):
        rel_x = pos[0] - XYButtons.center[0]
        rel_y = pos[1] - XYButtons.center[1]
        radius = math.sqrt(rel_x**2 + rel_y**2)
        if rel_x > rel_y and rel_x > -rel_y:
            quadrant = 0 # Right
        elif rel_x <= rel_y and rel_x > -rel_y:
            quadrant = 3 # Down
        elif rel_x > rel_y and rel_x < -rel_y:
            quadrant = 1 # Up
        else:
            quadrant = 2 # Left
        
        idx = self.lookupConcentric(radius)
        return (quadrant, idx)
    
    def mouseOverKeypad(self, mpos):
        for idx, kpos in XYButtons.keypad_positions.items():
            rect = wx.Rect(kpos[0], kpos[1], 44, 32)
            if rect.Contains(mpos):
                return idx
        return None

    def OnMotion(self, event):
        oldq, oldc = self.quadrant, self.concentric

        mpos = event.GetPosition()
        idx = self.mouseOverKeypad(mpos)
        self.quadrant = None
        self.concentric = None
        if idx == None:
            center = wx.Point(XYButtons.center[0], XYButtons.center[1])
            riseDist = self.distanceToLine(mpos, center.x-1, center.y-1, center.x+1, center.y+1)
            fallDist = self.distanceToLine(mpos, center.x-1, center.y+1, center.x+1, center.y-1)
            if riseDist > 10 and fallDist > 10:
                self.quadrant, self.concentric = self.getQuadrantConcentricFromPosition(mpos)
        
        if oldq != self.quadrant or oldc != self.concentric:
            self.update()

    def OnLeftDown(self, event):
        mpos = event.GetPosition()

        idx = self.mouseOverKeypad(mpos)
        if idx == None:
            self.quadrant, self.concentric = self.getQuadrantConcentricFromPosition(mpos)
            if self.quadrant != None and self.concentric != None:
                x, y = self.getMovement()
                if self.moveCallback:
                    self.moveCallback(x, y)
        else:
            self.setKeypadIndex(idx)
    
    def OnLeaveWindow(self, evt):
        self.quadrant = None
        self.concentric = None
        self.update()
    
    def drawPartialPie(self, dc, center, r1, r2, angle1, angle2):
        parts = 64
        angle_dist = angle2 - angle1
        angle_inc = angle_dist / parts

        p1 = wx.Point(center.x + r1*math.cos(angle1), center.y + r1*math.sin(angle1))
        p2 = wx.Point(center.x + r2*math.cos(angle1), center.y + r2*math.sin(angle1))
        p3 = wx.Point(center.x + r2*math.cos(angle2), center.y + r2*math.sin(angle2))
        p4 = wx.Point(center.x + r1*math.cos(angle2), center.y + r1*math.sin(angle2))

        points = [p1, p2]

        points.extend([wx.Point(
            center.x + r1*math.cos(angle1+i*angle_inc),
            center.y + r1*math.sin(angle1+i*angle_inc)) for i in range(0, parts)])
        
        # points.extend([p3])

        points.extend([wx.Point(
            center.x + r2*math.cos(angle1+i*angle_inc),
            center.y + r2*math.sin(angle1+i*angle_inc)) for i in range(parts, 0, -1)])
        dc.DrawPolygon(points)
    
    def distanceToLine(self, pos, x1, y1, x2, y2):
        xlen = x2 - x1
        ylen = y2 - y1
        pxlen = x1 - pos.x
        pylen = y1 - pos.y
        return abs(xlen*pylen-ylen*pxlen)/math.sqrt(xlen**2+ylen**2)
    
    def highlightQuadrant(self, dc, quadrant, concentric):
        assert(quadrant >= 0 and quadrant <= 3)
        assert(concentric >= 0 and concentric <= 3)

        inner_ring_radius = XYButtons.concentric_circle_radii[0]
        # fudge = math.pi*0.002
        fudge = -0.02
        center = wx.Point(XYButtons.center[0], XYButtons.center[1])
        if quadrant == 0:
            a1, a2 = (-math.pi*0.25, math.pi*0.25)
            center.x += inner_ring_radius
        elif quadrant == 1:
            a1, a2 = (math.pi*1.25, math.pi*1.75)
            center.y -= inner_ring_radius
        elif quadrant == 2:
            a1, a2 = (math.pi*0.75, math.pi*1.25)
            center.x -= inner_ring_radius
        elif quadrant == 3:
            a1, a2 = (math.pi*0.25, math.pi*0.75)
            center.y += inner_ring_radius
        
        r1 = XYButtons.concentric_circle_radii[concentric]
        r2 = XYButtons.concentric_circle_radii[concentric+1]
        self.drawPartialPie(dc, center, r1-inner_ring_radius, r2-inner_ring_radius, a1+fudge, a2-fudge)

    def draw(self, dc):
        center = wx.Point(XYButtons.center[0], XYButtons.center[1])

        dc.SetPen(wx.Pen(wx.Colour(100,100,100,172), 4))
        dc.SetBrush(wx.Brush(wx.Colour(0,0,0,128)))

        dc.DrawBitmap(self.bg_bmp, 0, 0)

        if self.quadrant != None and self.concentric != None:
            self.highlightQuadrant(dc, self.quadrant, self.concentric)

        pos = XYButtons.keypad_positions[self.keypad_idx]
        dc.DrawBitmap(self.keypad_bmp, pos[0], pos[1])
        
        return True
