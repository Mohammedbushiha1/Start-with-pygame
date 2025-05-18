from direct.showbase.ShowBase import ShowBase
from panda3d.core import Filename, loadPrcFileData, NodePath
from panda3d.core import CollisionTraverser, CollisionHandlerQueue, CollisionRay, CollisionNode
from panda3d.core import GeomNode, BitMask32
from panda3d.core import VBase4, Point3, Vec3
from direct.task import Task
import os
import math

loadPrcFileData('', 'win-size 1024 768')
loadPrcFileData('', 'window-title عارض OBJ مع كاميرا تتبع الكائن')

class InteractiveObjViewer(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        self.disableMouse()
        self.camera_initial_pos = Point3(0, -70, 20)
        self.camera.setPos(self.camera_initial_pos)
        self.camera.lookAt(0, 0, 0)

        self.setup_lights()

        self.obj_folder_path = "models/"
        if not os.path.exists(self.obj_folder_path):
            os.makedirs(self.obj_folder_path)
            print(f"تم إنشاء المجلد: {self.obj_folder_path}")
            print(f"يرجى وضع ملفات .obj الخاصة بك في هذا المجلد ثم إعادة تشغيل البرنامج.")

        self.model_nodes = []
        self.load_all_obj_files()

        self.selected_object = None
        self.object_move_sensitivity = 50.0
        self.object_rotate_sensitivity = 90.0

        self.picker_traverser = CollisionTraverser('pickerTraverser')
        self.picker_handler = CollisionHandlerQueue()
        self.picker_ray = CollisionRay()
        picker_node = CollisionNode('mouseRay')
        picker_node.addSolid(self.picker_ray)
        picker_node.setFromCollideMask(GeomNode.getDefaultCollideMask())
        picker_node.setIntoCollideMask(BitMask32.allOff())
        self.picker_ray_node_path = self.camera.attachNewNode(picker_node)
        self.picker_traverser.addCollider(self.picker_ray_node_path, self.picker_handler)

        # متغيرات التحكم بالفأرة (مشتركة للكاميرا والكائن)
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.mouse_btn_down = [False, False, False] # [Left, Middle, Right]

        # إعدادات الكاميرا
        self.default_cam_target = Point3(0, 0, 0) # الهدف الافتراضي للكاميرا
        self.cam_target = Point3(self.default_cam_target) # الهدف الحالي للكاميرا

        # تهيئة معلمات الكاميرا الأولية بالنسبة للهدف الأولي
        initial_cam_vec_to_target = self.camera.getPos(self.render) - self.cam_target
        self.cam_distance = initial_cam_vec_to_target.length()
        if self.cam_distance < 1.0: self.cam_distance = 1.0
        self.cam_pitch = math.degrees(math.asin(initial_cam_vec_to_target.getZ() / self.cam_distance))
        # حساب heading بشكل صحيح لـ Panda3D (حيث Y هو العمق)
        # vec_target_to_cam.getX() = dist * sin(H) * cos(P)
        # vec_target_to_cam.getY() = -dist * cos(H) * cos(P)
        # atan2(sin_component, cos_component)
        # sin_component is related to X, cos_component is related to -Y
        self.cam_heading = math.degrees(math.atan2(initial_cam_vec_to_target.getX(), -initial_cam_vec_to_target.getY()))

        self.enable_interactive_controls()

        print("مرحباً بك في عارض ملفات OBJ التفاعلي!")
        print(f"يتم تحميل النماذج من المجلد: {os.path.abspath(self.obj_folder_path)}")
        print("- انقر بزر الفأرة الأيسر لاختيار كائن. ستصبح الكاميرا متمحورة حوله.")
        print("- اسحب بزر الفأرة الأيسر لتحريك الكائن المختار (على المستوى X-Y).")
        print("- اسحب بزر الفأرة الأيمن لتدوير الكائن المختار (H و P).")
        print("- استخدم عجلة الفأرة للتقريب والتبعيد (الكاميرا بالنسبة للهدف).")
        print("- اضغط مع الاستمرار على زر الفأرة الأوسط وحرك الفأرة لتدوير المشهد (الكاميرا بالنسبة للهدف).")

    def setup_lights(self):
        from panda3d.core import AmbientLight, DirectionalLight
        ambient_light = AmbientLight("ambient_light")
        ambient_light.setColor(VBase4(0.3, 0.3, 0.3, 1))
        self.ambient_light_node = self.render.attachNewNode(ambient_light)
        self.render.setLight(self.ambient_light_node)

        directional_light = DirectionalLight("directional_light")
        directional_light.setColor(VBase4(0.9, 0.9, 0.8, 1))
        directional_light.setDirection(Vec3(-1, -1, -1))
        self.directional_light_node = self.render.attachNewNode(directional_light)
        self.render.setLight(self.directional_light_node)

        directional_light2 = DirectionalLight("directional_light2")
        directional_light2.setColor(VBase4(0.5, 0.6, 0.7, 1))
        directional_light2.setDirection(Vec3(1, 2, -1))
        self.directional_light_node2 = self.render.attachNewNode(directional_light2)
        self.render.setLight(self.directional_light_node2)

    def load_obj_file(self, filepath_fn):
        try:
            model = self.loader.loadModel(filepath_fn)
            if model and not model.isEmpty():
                model.reparentTo(self.render)
                model.setPos(len(self.model_nodes) * 15 - (len(self.model_nodes) // 2 * 30) , 0, 0) # زيادة التباعد
                model.setScale(1)
                model.setTag('pickable', 'true')
                model.setName(filepath_fn.getBasenameWoExtension())
                self.model_nodes.append(model)
                print(f"تم تحميل النموذج: {filepath_fn.getFullpath()}")
            else:
                print(f"فشل تحميل النموذج أو أن النموذج فارغ: {filepath_fn.getFullpath()}")
        except Exception as e:
            print(f"حدث خطأ أثناء تحميل النموذج {filepath_fn.getFullpath()}: {e}")

    def load_all_obj_files(self):
        if not os.path.exists(self.obj_folder_path):
            print(f"المجلد {self.obj_folder_path} غير موجود.")
            return
        for filename_str in os.listdir(self.obj_folder_path):
            if filename_str.lower().endswith(".obj"):
                filepath = os.path.join(self.obj_folder_path, filename_str)
                self.load_obj_file(Filename.fromOsSpecific(filepath))

    def pick_object_at_mouse(self, mouse_pos):
        self.picker_ray.setFromLens(self.camNode, mouse_pos.getX(), mouse_pos.getY())
        self.picker_traverser.traverse(self.render)
        if self.picker_handler.getNumEntries() > 0:
            self.picker_handler.sortEntries()
            picked_entry = self.picker_handler.getEntry(0).getIntoNodePath()
            parent = picked_entry
            while parent != self.render and not parent.isEmpty():
                if parent.hasNetTag('pickable') and parent.getTag('pickable') == 'true':
                    return parent
                if parent.hasParent():
                    parent = parent.getParent()
                else:
                    break
        return None

    def update_camera_parameters_for_new_target(self, new_target_pos):
        """
        يحافظ على موقع الكاميرا الحالي واتجاهها، ولكنه يعيد حساب
        cam_distance, cam_heading, cam_pitch بالنسبة للهدف الجديد.
        """
        current_cam_pos_world = self.camera.getPos(self.render)
        vec_target_to_cam_world = current_cam_pos_world - new_target_pos

        self.cam_target = Point3(new_target_pos) # تحديث هدف الكاميرا
        self.cam_distance = vec_target_to_cam_world.length()
        if self.cam_distance < 0.1: # مسافة دنيا لتجنب المشاكل
            self.cam_distance = 0.1
            # إذا كانت الكاميرا قريبة جدًا أو داخل الهدف، قد نحتاج إلى دفعها للخارج قليلاً
            # على طول متجه النظر السابق أو متجه افتراضي
            # current_cam_pos_world = new_target_pos + (vec_target_to_cam_world.normalized() * 0.1)
            # self.camera.setPos(current_cam_pos_world)


        # إعادة حساب pitch
        # vec_target_to_cam_world.getZ() = cam_distance * sin(pitch)
        if self.cam_distance == 0: # تجنب القسمة على صفر
             self.cam_pitch = 0 # أو قيمة افتراضية أخرى
        else:
            val_for_asin = vec_target_to_cam_world.getZ() / self.cam_distance
            self.cam_pitch = math.degrees(math.asin(max(-1.0, min(1.0, val_for_asin)))) # تقييد القيمة بين -1 و 1

        # إعادة حساب heading
        # vec_target_to_cam_world.getX() = cam_distance * sin(heading) * cos(pitch)
        # vec_target_to_cam_world.getY() = -cam_distance * cos(heading) * cos(pitch)
        cos_rad_pitch = math.cos(math.radians(self.cam_pitch))
        if abs(cos_rad_pitch) < 0.001 or self.cam_distance == 0: # إذا كانت الزاوية قائمة أو المسافة صفر
            # يمكن أن يكون Heading غير محدد جيدًا، استخدم القيمة السابقة أو قيمة افتراضية
            # self.cam_heading يبقى كما هو أو يُعين إلى 0
            # في حالة النظر مباشرة للأعلى أو الأسفل، x و y للكاميرا بالنسبة للهدف سيكونان صغيرين جدًا.
            # إذا كانت الكاميرا مباشرة فوق الهدف، heading لا يهم كثيرًا.
            # لتبسيط الأمر، إذا كان cos_rad_pitch قريبًا من الصفر، فإننا لا نغير heading بشكل كبير.
             pass # self.cam_heading = math.degrees(math.atan2(vec_target_to_cam_world.getX(), -vec_target_to_cam_world.getY()))
        else:
            # نحتاج إلى x_comp و y_comp للمتجه في مستوى XY الخاص بالهدف، ومقسومًا على cos_rad_pitch
            x_comp_for_atan = vec_target_to_cam_world.getX() / (self.cam_distance * cos_rad_pitch)
            y_comp_for_atan = vec_target_to_cam_world.getY() / (self.cam_distance * cos_rad_pitch)
            self.cam_heading = math.degrees(math.atan2(x_comp_for_atan, -y_comp_for_atan))

        # self.update_camera_pos() # استدعاء لتطبيق التغييرات فورًا (اختياري هنا، حيث أن المهمة ستفعل ذلك)


    def enable_interactive_controls(self):
        self.mouseWatcherNode.setDisplayRegion(self.win.getDisplayRegion(0))
        self.camLens.setFov(60)
        self.accept("mouse1", self.handle_mouse_1_press)
        self.accept("mouse1-up", self.handle_mouse_1_release)
        self.accept("mouse3", self.handle_mouse_3_press)
        self.accept("mouse3-up", self.handle_mouse_3_release)
        self.accept("mouse2", self.on_orbit_mouse_down)
        self.accept("mouse2-up", self.on_orbit_mouse_up)
        self.accept("wheel_up", self.on_wheel_up)
        self.accept("wheel_down", self.on_wheel_down)
        self.taskMgr.add(self.mouse_control_task, "MouseControlTask")

    def handle_mouse_1_press(self):
        self.mouse_btn_down[0] = True
        if self.mouseWatcherNode.hasMouse():
            mpos = self.mouseWatcherNode.getMouse()
            self.last_mouse_x = mpos.getX()
            self.last_mouse_y = mpos.getY()

            newly_picked_object = self.pick_object_at_mouse(mpos)

            if self.selected_object and self.selected_object != newly_picked_object:
                self.selected_object.clearColorScale() # إلغاء تمييز القديم

            if newly_picked_object:
                self.selected_object = newly_picked_object
                self.selected_object.setColorScale(0.7, 0.7, 1.0, 1.0)
                print(f"تم اختيار: {self.selected_object.getName()}. الكاميرا تستهدفه الآن.")
                self.update_camera_parameters_for_new_target(self.selected_object.getPos(self.render))
            elif self.selected_object: # تم النقر على مساحة فارغة وكان هناك كائن مختار
                self.selected_object.clearColorScale()
                self.selected_object = None
                print("تم إلغاء الاختيار. الكاميرا تستهدف نقطة الأصل.")
                self.update_camera_parameters_for_new_target(self.default_cam_target)
            # self.update_camera_pos() # لضمان تحديث فوري لموضع الكاميرا إذا لزم الأمر

    def handle_mouse_1_release(self):
        self.mouse_btn_down[0] = False

    def handle_mouse_3_press(self):
        self.mouse_btn_down[2] = True
        if self.mouseWatcherNode.hasMouse():
            mpos = self.mouseWatcherNode.getMouse()
            self.last_mouse_x = mpos.getX()
            self.last_mouse_y = mpos.getY()

    def handle_mouse_3_release(self):
        self.mouse_btn_down[2] = False

    def on_orbit_mouse_down(self):
        self.mouse_btn_down[1] = True
        if self.mouseWatcherNode.hasMouse():
            mpos = self.mouseWatcherNode.getMouse()
            self.last_mouse_x = mpos.getX()
            self.last_mouse_y = mpos.getY()

    def on_orbit_mouse_up(self):
        self.mouse_btn_down[1] = False

    def on_wheel_up(self):
        self.cam_distance = max(0.1, self.cam_distance - 5) # تقريب مع مسافة دنيا أكبر من الصفر
        self.update_camera_pos()

    def on_wheel_down(self):
        self.cam_distance += 5
        self.update_camera_pos()

    def mouse_control_task(self, task):
        if not self.mouseWatcherNode.hasMouse():
            return Task.cont

        mx = self.mouseWatcherNode.getMouseX()
        my = self.mouseWatcherNode.getMouseY()
        delta_x = mx - self.last_mouse_x
        delta_y = my - self.last_mouse_y

        object_manipulated_this_frame = False

        if self.selected_object:
            # تحريك الكائن المختار (زر الفأرة الأيسر)
            if self.mouse_btn_down[0]:
                current_pos = self.selected_object.getPos()
                new_x = current_pos.getX() + delta_x * self.object_move_sensitivity
                new_y = current_pos.getY() - delta_y * self.object_move_sensitivity
                self.selected_object.setPos(new_x, new_y, current_pos.getZ())
                self.cam_target = self.selected_object.getPos(self.render) # تحديث هدف الكاميرا
                object_manipulated_this_frame = True

            # تدوير الكائن المختار (زر الفأرة الأيمن)
            elif self.mouse_btn_down[2]:
                current_hpr = self.selected_object.getHpr()
                new_h = current_hpr.getX() - delta_x * self.object_rotate_sensitivity
                new_p = current_hpr.getY() - delta_y * self.object_rotate_sensitivity
                self.selected_object.setHpr(new_h, new_p, current_hpr.getZ())
                object_manipulated_this_frame = True # الدوران لا يغير الهدف، لكنه تلاعب

        # التحكم بكاميرا المدار (زر الفأرة الأوسط)
        if self.mouse_btn_down[1]:
            self.cam_heading -= delta_x * 100
            self.cam_pitch = max(-89.9, min(89.9, self.cam_pitch + delta_y * 100)) # تجنب 90 درجة تمامًا
            self.update_camera_pos()
        elif object_manipulated_this_frame and self.selected_object:
            # إذا تم تحريك الكائن (وليس تدوير الكاميرا بالزر الأوسط)،
            # يجب أن تحافظ الكاميرا على توجهها النسبي للهدف الجديد.
            # دالة update_camera_parameters_for_new_target تقوم بذلك.
            # ومع ذلك، بما أن cam_target تم تحديثه بالفعل، فإن update_camera_pos()
            # يجب أن تحافظ على المسافة والزوايا الحالية للهدف الجديد.
            self.update_camera_pos()


        self.last_mouse_x = mx
        self.last_mouse_y = my
        return Task.cont

    def update_camera_pos(self):
        """تحديث موضع واتجاه الكاميرا بناءً على الهدف والمسافة والزوايا."""
        rad_pitch = math.radians(self.cam_pitch)
        rad_heading = math.radians(self.cam_heading)

        # حساب موضع الكاميرا بالنسبة للهدف
        cam_x_rel = self.cam_distance * math.sin(rad_heading) * math.cos(rad_pitch)
        cam_y_rel = -self.cam_distance * math.cos(rad_heading) * math.cos(rad_pitch) # سالب Y لأن Panda3D Y للداخل
        cam_z_rel = self.cam_distance * math.sin(rad_pitch)

        # إضافة موضع الهدف للحصول على الموضع العالمي للكاميرا
        self.camera.setPos(self.cam_target.getX() + cam_x_rel,
                           self.cam_target.getY() + cam_y_rel,
                           self.cam_target.getZ() + cam_z_rel)
        self.camera.lookAt(self.cam_target) # اجعل الكاميرا تنظر دائمًا إلى الهدف


app = InteractiveObjViewer()
app.run()