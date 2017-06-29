import time
import threading
import wx
from wx.lib.scrolledpanel import ScrolledPanel
from cgroupspy import trees
import subprocess32 as sub32

from numpy import arange
import matplotlib
matplotlib.use('WXAgg')

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.figure import Figure

class ControlWindow(ScrolledPanel):
    def __init__(self, parent, rootPath=""):
        ScrolledPanel.__init__(self, parent=parent)
        self.SetupScrolling()
        self.parent = parent
        self.rootPath = rootPath

        parent.Bind(wx.EVT_CLOSE, self.closeWindow)

        filemenu = wx.Menu()
        
        menuAbout = filemenu.Append(wx.ID_ABOUT, "&About", "Information about this project")
        parent.Bind(wx.EVT_MENU, self.aboutClicked, menuAbout)
        filemenu.AppendSeparator()

        if (rootPath == "") or (rootPath[:8] == "/cpuacct") or (rootPath[:7] == "/memory"):
            menuStopTracking = filemenu.Append(-1, "&Stop tracking")
            parent.Bind(wx.EVT_MENU, self.stopTrackingClicked, menuStopTracking)


        menuExit = filemenu.Append(wx.ID_EXIT, "E&xit", "Terminate the program")
        parent.Bind(wx.EVT_MENU, self.exitClicked, menuExit)

        menuBar = wx.MenuBar()
        menuBar.Append(filemenu, "&Options")
        parent.SetMenuBar(menuBar)

        #logic connected with cgroups

        self.centerSizer = wx.BoxSizer(wx.HORIZONTAL)

        #left sizer -it will show cgroups tree with appropriate intendation
        #   all nodes has buttons - clicking one of them starts tracking cgroup and provide
        #   the right sizer with recorded data (for a chart)

        leftSizer = wx.BoxSizer(wx.VERTICAL)
        ln = wx.StaticLine(self, id=-1)
        leftSizer.Add(ln, 0, wx.EXPAND)


        label = wx.StaticText(self, label="Cgroup tree")
        leftSizer.Add(label)
        leftSizer.AddSpacer(20)

        self.tree = trees.Tree()
        rootNode = self.tree.root
        if rootPath != "":
            rootNode = self.tree.get_node_by_path(rootPath)
        print rootPath
        self.children = rootNode.children
        
        self.childrenLen = len(self.children)
        for i in range(self.childrenLen):
            c = self.children[i]
            childTitleSizer = wx.BoxSizer(wx.HORIZONTAL)
            child = wx.StaticText(self, label="\t" + str(c))
            oneNode = self.tree.get_node_by_path(str(c)[6:-1])
            
            childrenBtn = wx.Button(self, id=i, label="Children")
            paramsBtn = wx.Button(self, id=self.childrenLen+i, label="Params")
            tasksBtn = wx.Button(self, id=self.childrenLen*2 + i, label="Tasks")
            addBtn = wx.Button(self, id = self.childrenLen*3 + i, label="Add cgroup")
            deleteBtn = wx.Button(self, id = self.childrenLen*4 + i, label="Delete cgroup")
            PIDBtn = wx.Button(self, id = self.childrenLen*5 + i, label="Move PID here")
            self.Bind(wx.EVT_BUTTON, self.paramsClicked, paramsBtn)
            self.Bind(wx.EVT_BUTTON, self.childrenClicked, childrenBtn)
            self.Bind(wx.EVT_BUTTON, self.tasksClicked, tasksBtn)
            self.Bind(wx.EVT_BUTTON, self.clickAdd, addBtn)
            self.Bind(wx.EVT_BUTTON, self.clickDelete, deleteBtn)
            self.Bind(wx.EVT_BUTTON, self.clickPID, PIDBtn)


            childTitleSizer.Add(child, 0, wx.CENTER)
            childTitleSizer.AddSpacer(2)
            childTitleSizer.Add(childrenBtn, 0, wx.CENTER)
            childTitleSizer.AddSpacer(2)
            childTitleSizer.Add(paramsBtn, 0, wx.CENTER)
            childTitleSizer.AddSpacer(2)
            childTitleSizer.Add(tasksBtn, 0, wx.CENTER)
            childTitleSizer.AddSpacer(2)
            childTitleSizer.Add(addBtn, 0, wx.CENTER)
            childTitleSizer.AddSpacer(2)
            childTitleSizer.Add(deleteBtn, 0, wx.CENTER)
            childTitleSizer.AddSpacer(2)
            childTitleSizer.Add(PIDBtn, 0, wx.CENTER)
            childTitleSizer.AddSpacer(2)

            leftSizer.AddSpacer(8)
            leftSizer.Add(childTitleSizer)

        rightSizer = wx.BoxSizer(wx.VERTICAL)
        if (rootPath == "") or (rootPath[:8] == "/cpuacct") or (rootPath[:7] == "/memory"):
            ln = wx.StaticLine(self, id=-1)
            rightButtonSizer = wx.BoxSizer(wx.HORIZONTAL)
            
            if (rootPath == ""):# or (rootPath[:8] == "/cpuacct"):
                cpuBtn = wx.Button(self, id = -1, label="Cpu accounting")
                self.Bind(wx.EVT_BUTTON, self.cpuChosen, cpuBtn)
                rightButtonSizer.Add(cpuBtn, 0, wx.CENTER)
                rightButtonSizer.AddSpacer(2)
            #if (rootPath == "") or (rootPath[:7] == "/memory"):
                memoryBtn = wx.Button(self, id = -1, label="Memory")
                self.Bind(wx.EVT_BUTTON, self.memoryChosen, memoryBtn)
                rightButtonSizer.Add(memoryBtn, 0, wx.CENTER)
                rightButtonSizer.AddSpacer(2)

            rightSizer.Add(rightButtonSizer)

            self.figure = Figure()
            self.axes = self.figure.add_subplot(111)
            self.canvas = FigureCanvas(self, -1, self.figure)
            self.x = []
            self.y = []
        
            rightSizer.Add(ln, 0, wx.EXPAND)
            rightSizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)

            ln = wx.StaticLine(self, id=-1)
            rightSizer.Add(ln, 0, wx.EXPAND)
            self.dataInput = wx.StaticText(self, label="")
            rightSizer.Add(self.dataInput, 0, wx.CENTER)

            self.thread = ChartThread()
            self.thread.parent = self
            if (rootPath == ""):
                self.thread.trackID = 0
                self.thread.rootPath = "/cpuacct"
            elif(rootPath[:8] == "/cpuacct"):
                self.thread.trackID = 0
                self.thread.rootPath = rootPath
            else:
                self.thread.trackID = 1
                self.thread.rootPath = rootPath
            self.alive = False
            self.startThread()

        self.centerSizer.Add(leftSizer)
        self.centerSizer.Add(rightSizer)

        self.SetSizer(self.centerSizer)
        self.Show(True)

    def startThread(self):
        self.alive = True
        self.thread.start()
    def stopThread(self):
        self.alive = False
        self.thread.join()

    def cpuChosen(self, event):
        self.stopThread()
        
        self.thread = ChartThread()
        self.thread.parent = self

        self.thread.trackID = 0
        self.thread.rootPath="/cpuacct"
        self.x = []
        self.y = []
        self.startThread()

    def memoryChosen(self, event):
        self.stopThread()

        self.thread = ChartThread()
        self.thread.parent = self

        self.thread.trackID = 1
        self.thread.rootPath = "/memory"
        self.x = []
        self.y = []
        self.startThread()

    def draw(self):
        self.axes.clear()
        if self.nrOfVals <= 50:
            self.axes.set_xlim(0, 50)
            my_xticks = arange(0, 50, 5)
            self.axes.set_xticks(my_xticks)
        else:
            self.axes.set_xlim(self.nrOfVals - 50, self.nrOfVals)
            my_xticks = arange(self.nrOfVals - 50, self.nrOfVals, 5)
            self.axes.set_xticks(my_xticks)
        
        self.axes.plot(self.x, self.y)


    def aboutClicked(self, event):
        dialog = wx.MessageDialog(self, "A small project focusing on cgroups",
                                  "About", wx. OK)
        dialog.ShowModal()
        dialog.Destroy()

    def exitClicked(self, event):
        self.parent.Close(True)

    def stopTrackingClicked(self, event):
        self.stopThread()

    def paramsClicked(self, event):
        nodeStr = self.children[event.GetId() - self.childrenLen]
        node = self.tree.get_node_by_path(str(nodeStr)[6:-1])

        controllersStr = "No params found"
        if node != None:
            nodeControllers = node.controller
            if nodeControllers != None:
                controllersStr = ""
                params = filter(lambda a: not (a.startswith(
                    '__') or a == 'filepath' or a == 'get_property' or a == 'set_property' or a == 'procs' or a == 'node' or a == 'tasks'),
                                dir(nodeControllers))
                for param in params:
                    attributeVal = "UNREACHABLE (PERMISSION DENIED)"
                    try:
                        attributeVal = str(getattr(nodeControllers, str(param)))
                    except Exception:
                        pass
                    paramLabel = "\t\t\t" + str(param) + ":" + attributeVal + "\n"
                    controllersStr += paramLabel
        dialog = ProvideInfoDialog(self, str(nodeStr) + " - params", "", controllersStr)

        dialog.ShowModal()
        dialog.Destroy()

    def childrenClicked(self, event):
        nodeStr = self.children[event.GetId()]
        nodePath = str(nodeStr)[6:-1]
        nodeChildren = self.tree.get_node_by_path(nodePath).children
        if nodeChildren == None or len(nodeChildren) == 0:
            dialog = wx.MessageDialog(self, str("No children found"), str(nodeStr), wx.OK)
            dialog.ShowModal()
            dialog.Destroy()
        else:
            frame = wx.Frame(parent=None, title=nodePath + " - children")
            panel = ControlWindow(frame, rootPath=nodePath)
            frame.Show()

    def tasksClicked(self, event):
        nodeStr = self.children[event.GetId() - 2*self.childrenLen]
        node = self.tree.get_node_by_path(str(nodeStr)[6:-1])

        controllersStr = "No tasks found"
        if node != None:
            nodeControllers = node.controller
            if nodeControllers != None:
                controllersStr = str(nodeControllers.tasks) 
        dialog = ProvideInfoDialog(self, str(nodeStr) + " - tasks", "Tasks:", controllersStr)
        dialog.ShowModal()
        dialog.Destroy()

    def clickPID(self, event):
        nodeStr = self.children[event.GetId() - 5 * self.childrenLen]
        node = self.tree.get_node_by_path(str(nodeStr)[6:-1])
        moveDialog = MovePidDialog(None, node)
        moveDialog.ShowModal()
        moveDialog.Destroy()

    def clickAdd(self, event):
        nodeStr = self.children[event.GetId() - 3 * self.childrenLen]
        node = self.tree.get_node_by_path(str(nodeStr)[6:-1])
        enterDialog = EnterCgroupDialog(None, self.addCgroup, node)
        enterDialog.ShowModal()
        enterDialog.Destroy()

    def clickDelete(self, event):
        nodeStr = self.children[event.GetId() - 4 * self.childrenLen]
        node = self.tree.get_node_by_path(str(nodeStr)[6:-1])
        enterDialog = EnterCgroupDialog(None, self.deleteCgroup, node)
        enterDialog.ShowModal()
        enterDialog.Destroy()

    def addCgroup(self, node, name):
        try:
            node.create_cgroup(name)
        except OSError:
            dialog = wx.MessageDialog(self, "Creating cgroup failed (probably insufficient permissions)",
                                      "Error", wx.ICON_ERROR)
            dialog.ShowModal()
            dialog.Destroy()

    def deleteCgroup(self, node, name):
        try:
            node.delete_cgroup(name)
        except Exception:
            dialog = wx.MessageDialog(self, "Node is not empty - it can't be deleted",
                                      "Error", wx.ICON_ERROR)
            dialog.ShowModal()
            dialog.Destroy()

    def closeWindow(self, event):  
        print "Closing window"
        if (self.rootPath == "") or (self.rootPath[:8] == "/cpuacct") or (self.rootPath[:7] == "/memory"):
            self.stopThread()
        self.parent.Destroy()

class ChartThread(threading.Thread):
    def run(self):
        myObject = self.parent
        myObject.nrOfVals = 0

        node = myObject.tree.get_node_by_path(self.rootPath)
        trackedParam = "usage"
        if self.trackID == 1:
            #node = myObject.tree.get_node_by_path("/memory")
            trackedParam = "usage_in_bytes"
        while myObject.alive:
            usage = getattr(node.controller, str(trackedParam))
            
            print usage
            myObject.x.append(myObject.nrOfVals)
            myObject.y.append(usage)
            if len(myObject.x)>50 or len(myObject.y)>50:
                myObject.x = myObject.x[-50:]
                print "x len = " + str(len(myObject.x))
                myObject.y = myObject.y[-50:]
            wx.CallAfter(myObject.draw)
            wx.CallAfter(myObject.dataInput.SetLabel,str(usage))
            print "x lim = " + str (myObject.axes.get_xlim())
            wx.CallAfter(myObject.centerSizer.Layout)
            time.sleep(1)
            myObject.nrOfVals+=1


class ProvideInfoDialog (wx.Dialog): 
    def __init__(self, parent, title, subtitle, information):
        super(ProvideInfoDialog, self).__init__(parent, title=title, size=wx.Size(500,300))

        centerSizer = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self, label=subtitle)
        information = wx.TextCtrl(parent=self, id=-1, value=information, style=wx.TE_MULTILINE | wx.TE_READONLY, size=wx.Size(300,200))

        okButton = wx.Button(self, label='OK')
        self.Bind(wx.EVT_BUTTON, self.onClose, okButton)

        centerSizer.Add(label, 0, wx.CENTER)
        centerSizer.Add(information, 0, wx.CENTER)
        centerSizer.Add(okButton, 0, wx.CENTER)

        self.SetSizer(centerSizer)

    def onClose(self, event):
        self.Destroy()

class EnterCgroupDialog (wx.Dialog):
    def __init__(self, parent, funToExecute, node):
        super(EnterCgroupDialog, self).__init__(parent, title="Enter Cgroup name")

        self.funToExecute = funToExecute
        self.node = node
        centerSizer = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self, label="Cgroup name:")
        self.myInput = wx.TextCtrl(parent=self, id=-1)

        okButton = wx.Button(self, label='OK')
        cancelButton = wx.Button(self, label='Cancel')

        self.Bind(wx.EVT_BUTTON, self.onClose, cancelButton)
        self.Bind(wx.EVT_BUTTON, self.onSave, okButton)
        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        btnSizer.Add(okButton)
        btnSizer.AddSpacer(3)
        btnSizer.Add(cancelButton)

        centerSizer.Add(label)
        centerSizer.Add(self.myInput)
        centerSizer.Add(btnSizer)

        self.SetSizer(centerSizer)

    def onSave(self, event):
        cgroupName = self.myInput.GetLineText(0)
        print "cgroup name to be created/deleted: " + str(cgroupName)
        self.funToExecute(self.node, cgroupName)
        self.Destroy()

    def onClose(self, event):
        self.Destroy()

class MovePidDialog (wx.Dialog):
    def __init__(self, parent, node):
        super(MovePidDialog, self).__init__(parent, title="Enter PID")

        self.node = node
        centerSizer = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self, label="PID:")
        self.myInput = wx.TextCtrl(parent=self, id=-1)

        okButton = wx.Button(self, label='OK')
        cancelButton = wx.Button(self, label='Cancel')

        self.Bind(wx.EVT_BUTTON, self.onClose, cancelButton)
        self.Bind(wx.EVT_BUTTON, self.onSave, okButton)
        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        btnSizer.Add(okButton)
        btnSizer.AddSpacer(3)
        btnSizer.Add(cancelButton)

        centerSizer.Add(label)
        centerSizer.Add(self.myInput)
        centerSizer.Add(btnSizer)

        self.SetSizer(centerSizer)

    def onSave(self, event):
        pid = self.myInput.GetLineText(0)
        print "pid to be moved: " + str(pid)
        self.movePid(pid)
        self.Destroy()

    def onClose(self, event):
        self.Destroy()

    def movePid(self, pid):
        try:
            pidNr = int(pid)
        except ValueError:
            dialog = wx.MessageDialog(self, "Entered PID is not correct",
                                      "Error", wx.ICON_ERROR)
            dialog.ShowModal()
            dialog.Destroy()
            return
        if isinstance(pidNr, (int, long)):
            result = sub32.call(["ps", "-p", str(pidNr), "-o","comm="])
            if result == 0:
                path  = "/sys/fs/cgroup" + str(self.node.path) + "/tasks"
                #hope it is secure enough...
                print sub32.call("echo " + str(pidNr) + " > " + path, shell=True)
                print self.node.path
            else:
                dialog = wx.MessageDialog(self, "Moving PID has failed",
                                      "Error", wx.ICON_ERROR)
                dialog.ShowModal()
                dialog.Destroy()
        else:
            print "pid is not a number!"


app = wx.App(False)
frame = wx.Frame(parent=None, title="Cgroups")
panel = ControlWindow(frame)
frame.Show()
app.MainLoop()