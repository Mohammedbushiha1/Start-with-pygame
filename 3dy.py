from direct.showbase.ShowBase import ShowBase
from panda3d.core import LineSegs, Vec3, Point3, CollisionTraverser, CollisionNode, CollisionRay, CollisionHandlerQueue
from direct.gui.DirectGui import DirectButton

class WallEditor3D(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        # إعداد الكاميرا
        self.disableMouse()
        self.camera.setPos(0, -20, 10)
        self.camera.lookAt(0, 0, 0)

        # متغيرات الحالة
        self.drawing_wall = False
        self.wall_start = None
        self.walls = []

        # إعداد الأرضية كشبكة
        self.create_grid()

        # إعداد التقاط النقرات
        self.accept("mouse1", self.on_click)

        # زر بسيط لاختبار واجهة المستخدم
        self.button = DirectButton(text="رسم جدار", scale=0.05, pos=(-1.2, 0, 0.9), command=self.start_wall)

    def create_grid(self):
        lines = LineSegs()
        lines.setColor(0.8, 0.8, 0.8, 1)
        size = 20
        step = 1
        for i in range(-size, size + 1):
            lines.moveTo(i, -size, 0)
            lines.drawTo(i, size, 0)
            lines.moveTo(-size, i, 0)
            lines.drawTo(size, i, 0)
        node = lines.create()
        self.render.attachNewNode(node)

    def get_mouse_point(self):
        if not self.mouseWatcherNode.hasMouse():
            return None
        mpos = self.mouseWatcherNode.getMouse()

        # Raycasting لإيجاد تقاطع مع المستوى الأرضي Z=0
        ray = CollisionRay()
        ray.setFromLens(self.camNode, mpos.getX(), mpos.getY())

        coll_node = CollisionNode('mouseRay')
        coll_node.addSolid(ray)
        coll_np = self.camera.attachNewNode(coll_node)
        handler = CollisionHandlerQueue()
        traverser = CollisionTraverser()
        traverser.addCollider(coll_np, handler)

        plane_node = self.render.attachNewNode("ground")
        plane_node.setPos(0, 0, 0)

        # للأسف لا توجد طريقة مباشرة، لذا نستخدم حساب يدوي للتقاطع
        near_point = Point3()
        far_point = Point3()
        self.camLens.extrude(mpos, near_point, far_point)

        if far_point.getZ() == near_point.getZ():
            return None

        t = -near_point.getZ() / (far_point.getZ() - near_point.getZ())
        x = near_point.getX() + t * (far_point.getX() - near_point.getX())
        y = near_point.getY() + t * (far_point.getY() - near_point.getY())
        return Point3(x, y, 0)

    def start_wall(self):
        self.drawing_wall = True
        self.wall_start = None

    def on_click(self):
        if not self.drawing_wall:
            return

        point = self.get_mouse_point()
        if point is None:
            return

        if self.wall_start is None:
            self.wall_start = point
        else:
            self.create_wall(self.wall_start, point)
            self.wall_start = None
            self.drawing_wall = False

    def create_wall(self, start, end):
        line = LineSegs()
        line.setThickness(4)
        line.setColor(0.2, 0.2, 0.2, 1)
        line.moveTo(start)
        line.drawTo(end)
        node = line.create()
        self.render.attachNewNode(node)
        self.walls.append((start, end))


app = WallEditor3D()
app.run()