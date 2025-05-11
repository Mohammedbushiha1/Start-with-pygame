import pygame
import math
import copy
import os # <-- إضافة جديدة لاستخدام مسارات الملفات

# --- (ثوابت وإعدادات Pygame) ---
# --- (Constants and Pygame Setup) ---

SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
SIDEBAR_WIDTH = 150
DRAWING_AREA_WIDTH = SCREEN_WIDTH - SIDEBAR_WIDTH
INITIAL_PIXELS_PER_METER = 50
MIN_PIXELS_PER_METER = 10
MAX_PIXELS_PER_METER = 300
ZOOM_FACTOR_STEP = 1.1

# --- (الألوان) ---
# --- (Colors) ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
BLUE = (0, 0, 255) # سيستخدم لخلفية الأزرار العادية
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
DARK_GRAY = (50, 50, 50)
DOOR_COLOR = (150, 75, 0)
WINDOW_COLOR = (100, 150, 255)
HIGHLIGHT_COLOR = (255, 165, 0) # لون تمييز الزر النشط
INPUT_BOX_COLOR = (230, 230, 230)
INPUT_BOX_ACTIVE_COLOR = (255, 255, 200)
DELETE_COLOR = (200, 0, 0) # لون خلفية زر الحذف
GRID_COLOR = (230, 230, 230)
RULER_COLOR = (0, 150, 150) # لون أداة المسطرة وأيقونتها

# --- (متغيرات التراجع) ---
history = []
MAX_HISTORY_SIZE = 20

# --- (الأدوات وعناصر واجهة المستخدم) ---
TOOLS = ["WALL", "DOOR", "WINDOW", "DELETE", "MEASURE"]
TOOL_RECTS = []
INPUT_RECTS = {}

# --- (قيم افتراضية لحقول الإدخال) ---
DEFAULT_DOOR_WIDTH_M_STR = "0.9"
DEFAULT_WINDOW_WIDTH_M_STR = "1.2"

# --- (تهيئة Pygame) ---
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("MEASURE")
font = pygame.font.Font(None, 24)
small_font = pygame.font.Font(None, 18)
input_font = pygame.font.Font(None, 22)
clock = pygame.time.Clock()

# --- (تحميل الأيقونات) ---                       # <-- قسم جديد
# تأكد من أن ملفات الأيقونات موجودة في نفس مجلد الكود أو وفر المسار الصحيح
# يجب أن تكون الأيقونات بحجم مناسب للأزرار (مثلاً 32x32 أو 48x48 بكسل)
ICON_SIZE = (40, 40) # حجم الأيقونة المرغوب (يمكن تعديله)
icons = {}
try:
    # دالة مساعدة لتحميل وتغيير حجم الأيقونة
    def load_icon(filename):
        try:
            img = pygame.image.load(os.path.join(filename)).convert_alpha() # استخدم convert_alpha للشفافية
            return pygame.transform.scale(img, ICON_SIZE)
        except pygame.error as e:
            print(f"خطأ في تحميل الأيقونة {filename}: {e}")
            # إنشاء سطح فارغ كبديل إذا فشل التحميل
            fallback_surface = pygame.Surface(ICON_SIZE, pygame.SRCALPHA) # سطح شفاف
            fallback_surface.fill((0,0,0,0)) # تعبئة بالشفافية الكاملة
            # يمكنك رسم شيء بسيط هنا للإشارة للخطأ
            pygame.draw.rect(fallback_surface, RED, (0, 0, ICON_SIZE[0], ICON_SIZE[1]), 1)
            pygame.draw.line(fallback_surface, RED, (0,0), ICON_SIZE, 1)
            pygame.draw.line(fallback_surface, RED, (ICON_SIZE[0],0), (0, ICON_SIZE[1]), 1)
            return fallback_surface

    icons["WALL"] = load_icon("wall_icon.png")
    icons["DOOR"] = load_icon("door_icon.png")
    icons["WINDOW"] = load_icon("window_icon.png")
    icons["DELETE"] = load_icon("delete_icon.png")
    icons["MEASURE"] = load_icon("measure_icon.png")

except Exception as e:
    print(f"حدث خطأ عام أثناء تحميل الأيقونات: {e}")
    # يمكنك إيقاف البرنامج هنا إذا كانت الأيقونات ضرورية
    # running = False

# --- (متغيرات الحالة) ---
running = True
current_tool = None
drawing = False
start_pos_m = None
elements = []

# --- (متغيرات حالة التكبير/التصغير والتحريك) ---
pixels_per_meter = INITIAL_PIXELS_PER_METER
view_offset_x = 0
view_offset_y = 0

# --- (متغيرات حالة حقول الإدخال) ---
active_input = None
input_values = {
    'door': DEFAULT_DOOR_WIDTH_M_STR,
    'window': DEFAULT_WINDOW_WIDTH_M_STR
}

# --- (متغيرات حالة المسطرة) ---
ruler_point1_m = None
ruler_point2_m = None
ruler_snapped_point_m = None

# --- (دوال تحويل الإحداثيات) ---
def world_m_to_screen(world_m_pos):
    screen_x = round(world_m_pos[0] * pixels_per_meter + view_offset_x) + SIDEBAR_WIDTH
    screen_y = round(world_m_pos[1] * pixels_per_meter + view_offset_y)
    return (screen_x, screen_y)

def screen_to_world_m(screen_pos):
    screen_x_adj = screen_pos[0]
    if screen_x_adj >= SIDEBAR_WIDTH:
        screen_x_adj -= SIDEBAR_WIDTH
    else:
        screen_x_adj = 0
    if pixels_per_meter == 0:
        return (0, 0)
    world_mx = (screen_x_adj - view_offset_x) / pixels_per_meter
    world_my = (screen_pos[1] - view_offset_y) / pixels_per_meter
    return (world_mx, world_my)

# --- (دوال مساعدة) ---

# ***** تم تعديل هذه الدالة بشكل كبير *****
def draw_sidebar(selected_tool, current_input_values, active_input_field):
    """ترسم الشريط الجانبي مع الأيقونات وحقول الإدخال."""
    sidebar_area = pygame.Rect(0, 0, SIDEBAR_WIDTH, SCREEN_HEIGHT)
    pygame.draw.rect(screen, GRAY, sidebar_area)

    TOOL_RECTS.clear()
    INPUT_RECTS.clear()

    y_offset = 20
    button_height = 55 # زيادة ارتفاع الزر لاستيعاب الأيقونة والنص (اختياري)
    input_height = 25
    button_padding = 15 # زيادة المسافة بين الأزرار

    # عرض مقياس الرسم وتعليمات التكبير/المسطرة (كما كان)
    scale_text = small_font.render(f"Scale: {pixels_per_meter:.1f} px/m", True, BLACK)
    screen.blit(scale_text, (10, SCREEN_HEIGHT - 60))
    zoom_instr_text = small_font.render("Wheel to zoom.", True, BLACK)
    screen.blit(zoom_instr_text, (10, SCREEN_HEIGHT - 40))
    ruler_instr_text = small_font.render("Select tool above.", True, BLACK) # نص عام
    screen.blit(ruler_instr_text, (10, SCREEN_HEIGHT - 20))


    # رسم أزرار الأدوات باستخدام الأيقونات
    for tool in TOOLS:
        button_rect = pygame.Rect(10, y_offset, SIDEBAR_WIDTH - 20, button_height)
        TOOL_RECTS.append(button_rect)

        # تحديد لون خلفية الزر
        bg_color = BLUE
        if tool == selected_tool:
            bg_color = HIGHLIGHT_COLOR
        elif tool == "DELETE":
            bg_color = DELETE_COLOR
        elif tool == "MEASURE":
             bg_color = RULER_COLOR # استخدام لون المسطرة لخلفية زرها

        pygame.draw.rect(screen, bg_color, button_rect, border_radius=5) # رسم خلفية الزر (مع حواف مستديرة اختيارية)

        # الحصول على الأيقونة الخاصة بهذه الأداة
        icon_surface = icons.get(tool) # احصل على الأيقونة من القاموس

        if icon_surface:
            # حساب موقع لرسم الأيقونة في منتصف الزر
            icon_rect = icon_surface.get_rect(center=button_rect.center)
            screen.blit(icon_surface, icon_rect) # رسم الأيقونة
        else:
            # (احتياطي) إذا لم يتم تحميل الأيقونة، ارسم اسم الأداة كنص
            tool_text = font.render(tool, True, WHITE)
            text_rect = tool_text.get_rect(center=button_rect.center)
            screen.blit(tool_text, text_rect)

        y_offset += button_height + button_padding

        # إضافة حقل إدخال تحت زر الباب والنافذة (كما كان)
        if tool == "DOOR":
            input_rect = pygame.Rect(10, y_offset, SIDEBAR_WIDTH - 20, input_height)
            INPUT_RECTS['door'] = input_rect
            input_bg_color = INPUT_BOX_ACTIVE_COLOR if active_input_field == 'door' else INPUT_BOX_COLOR
            pygame.draw.rect(screen, input_bg_color, input_rect)
            pygame.draw.rect(screen, BLACK, input_rect, 1)
            input_text_surf = input_font.render("W: " + current_input_values['door'] + " m", True, BLACK)
            screen.blit(input_text_surf, (input_rect.x + 5, input_rect.y + 5))
            y_offset += input_height + button_padding

        elif tool == "WINDOW":
            input_rect = pygame.Rect(10, y_offset, SIDEBAR_WIDTH - 20, input_height)
            INPUT_RECTS['window'] = input_rect
            input_bg_color = INPUT_BOX_ACTIVE_COLOR if active_input_field == 'window' else INPUT_BOX_COLOR
            pygame.draw.rect(screen, input_bg_color, input_rect)
            pygame.draw.rect(screen, BLACK, input_rect, 1)
            input_text_surf = input_font.render("W: " + current_input_values['window'] + " m", True, BLACK)
            screen.blit(input_text_surf, (input_rect.x + 5, input_rect.y + 5))
            y_offset += input_height + button_padding
# ***** نهاية تعديل draw_sidebar *****


def calculate_distance_m(p1_m, p2_m):
    if p1_m is None or p2_m is None: return 0.0
    return math.sqrt((p2_m[0] - p1_m[0])**2 + (p2_m[1] - p1_m[1])**2)

def point_segment_distance_m(p_m, a_m, b_m):
    ax, ay = a_m
    bx, by = b_m
    px, py = p_m
    segment_len_sq = (bx - ax)**2 + (by - ay)**2
    if segment_len_sq < 1e-12:
        dist_m = calculate_distance_m(p_m, a_m)
        return dist_m, a_m
    u = (((px - ax) * (bx - ax)) + ((py - ay) * (by - ay))) / segment_len_sq
    if u < 0.0:
        closest_point_m = a_m
    elif u > 1.0:
        closest_point_m = b_m
    else:
        ix = ax + u * (bx - ax)
        iy = ay + u * (by - ay)
        closest_point_m = (ix, iy)
    dist_m = calculate_distance_m(p_m, closest_point_m)
    return dist_m, closest_point_m

def find_closest_wall_m(point_m, walls_list):
    closest_wall = None
    min_dist_m = float('inf')
    tolerance_pixels = 10
    tolerance_m = tolerance_pixels / pixels_per_meter if pixels_per_meter > 0 else float('inf')
    for wall in walls_list:
        dist_m, _ = point_segment_distance_m(point_m, wall['start_m'], wall['end_m'])
        if dist_m < min_dist_m and dist_m < tolerance_m:
            min_dist_m = dist_m
            closest_wall = wall
    return closest_wall

def find_closest_endpoint_m(point_m, elements_list, tolerance_m):
    closest_endpoint = None
    min_dist_sq = tolerance_m**2
    for elem in elements_list:
        if elem['type'] == 'wall':
            dist_sq_start = (point_m[0] - elem['start_m'][0])**2 + (point_m[1] - elem['start_m'][1])**2
            if dist_sq_start < min_dist_sq:
                min_dist_sq = dist_sq_start
                closest_endpoint = elem['start_m']
            dist_sq_end = (point_m[0] - elem['end_m'][0])**2 + (point_m[1] - elem['end_m'][1])**2
            if dist_sq_end < min_dist_sq:
                min_dist_sq = dist_sq_end
                closest_endpoint = elem['end_m']
    return closest_endpoint

def find_element_at_pos_m(pos_m, elements_list):
    clicked_element = None
    min_dist_m = float('inf')
    tolerance_pixels = 10
    tolerance_m = tolerance_pixels / pixels_per_meter if pixels_per_meter > 0 else float('inf')

    for elem in reversed(elements_list):
        if elem['type'] == 'door' or elem['type'] == 'window':
            width_m = elem['width_m']
            click_thickness_m = tolerance_m * 2
            center_m = elem['pos_m']
            wall = elem.get('wall_ref')
            if wall:
                dx_wall_m = wall['end_m'][0] - wall['start_m'][0]
                dy_wall_m = wall['end_m'][1] - wall['start_m'][1]
                is_horizontal = abs(dx_wall_m) > abs(dy_wall_m)
                if is_horizontal:
                    half_w_m = width_m / 2
                    half_h_m = click_thickness_m / 2
                else:
                    half_w_m = click_thickness_m / 2
                    half_h_m = width_m / 2
                min_x_m = center_m[0] - half_w_m
                max_x_m = center_m[0] + half_w_m
                min_y_m = center_m[1] - half_h_m
                max_y_m = center_m[1] + half_h_m
                if min_x_m <= pos_m[0] <= max_x_m and min_y_m <= pos_m[1] <= max_y_m:
                    dist_m = calculate_distance_m(pos_m, center_m)
                    if dist_m < min_dist_m:
                        min_dist_m = dist_m
                        clicked_element = elem

    if clicked_element is None:
        for elem in elements_list:
            if elem['type'] == 'wall':
                dist_m, _ = point_segment_distance_m(pos_m, elem['start_m'], elem['end_m'])
                if dist_m < tolerance_m and dist_m < min_dist_m:
                     min_dist_m = dist_m
                     clicked_element = elem
    return clicked_element

def draw_elements():
    for elem in elements:
        if elem['type'] == 'wall':
            start_screen = world_m_to_screen(elem['start_m'])
            end_screen = world_m_to_screen(elem['end_m'])
            if not (max(start_screen[0], end_screen[0]) < SIDEBAR_WIDTH or \
                    min(start_screen[0], end_screen[0]) > SCREEN_WIDTH or \
                    max(start_screen[1], end_screen[1]) < 0 or \
                    min(start_screen[1], end_screen[1]) > SCREEN_HEIGHT):
                pygame.draw.line(screen, DARK_GRAY, start_screen, end_screen, 5)
                mid_x_screen = (start_screen[0] + end_screen[0]) // 2
                mid_y_screen = (start_screen[1] + end_screen[1]) // 2
                length_m = elem['length_m']
                dim_text = small_font.render(f"{length_m:.2f}m", True, BLACK)
                dx_screen = end_screen[0] - start_screen[0]
                dy_screen = end_screen[1] - start_screen[1]
                if abs(dx_screen) < 0.01:
                     angle = math.pi / 2 if dy_screen > 0 else -math.pi / 2
                else:
                     angle = math.atan2(dy_screen, dx_screen)
                text_offset = 10
                text_x = mid_x_screen + math.sin(angle) * text_offset
                text_y = mid_y_screen - math.cos(angle) * text_offset
                text_rect = dim_text.get_rect(center=(int(text_x), int(text_y)))
                if text_rect.right > SIDEBAR_WIDTH and text_rect.bottom > 0 and \
                   text_rect.left < SCREEN_WIDTH and text_rect.top < SCREEN_HEIGHT:
                    bg_rect = text_rect.inflate(4, 2)
                    pygame.draw.rect(screen, WHITE, bg_rect)
                    screen.blit(dim_text, text_rect)

        elif elem['type'] == 'door' or elem['type'] == 'window':
            wall = elem.get('wall_ref')
            if not wall or wall not in elements:
                continue

            width_m = elem['width_m']
            center_m = elem['pos_m']
            center_screen = world_m_to_screen(center_m)

            if not (center_screen[0] < SIDEBAR_WIDTH or center_screen[0] > SCREEN_WIDTH or \
                    center_screen[1] < 0 or center_screen[1] > SCREEN_HEIGHT):
                width_px = width_m * pixels_per_meter
                height_px_base = 0.1 * pixels_per_meter
                visual_height_factor = 5
                height_px = max(3, height_px_base * visual_height_factor)

                dx_wall_m = wall['end_m'][0] - wall['start_m'][0]
                dy_wall_m = wall['end_m'][1] - wall['start_m'][1]
                is_horizontal = abs(dx_wall_m) > abs(dy_wall_m)
                if is_horizontal:
                    rect_w = width_px; rect_h = height_px
                else:
                    rect_w = height_px; rect_h = width_px

                item_rect_screen = pygame.Rect(
                    center_screen[0] - rect_w / 2,
                    center_screen[1] - rect_h / 2,
                    rect_w, rect_h)

                color = DOOR_COLOR if elem['type'] == 'door' else WINDOW_COLOR
                pygame.draw.rect(screen, color, item_rect_screen)

                if elem['type'] == 'window':
                     line_thickness = max(1, round(height_px_base / 3))
                     pygame.draw.line(screen, DARK_GRAY, item_rect_screen.midleft, item_rect_screen.midright, line_thickness)
                     pygame.draw.line(screen, DARK_GRAY, (item_rect_screen.centerx, item_rect_screen.top), (item_rect_screen.centerx, item_rect_screen.bottom), line_thickness)

                dim_text = small_font.render(f"{elem['width_m']:.2f}m", True, BLACK)
                text_rect = dim_text.get_rect(center=item_rect_screen.center)
                text_rect.y += item_rect_screen.height // 2 + 5
                if text_rect.right > SIDEBAR_WIDTH and text_rect.bottom > 0 and \
                   text_rect.left < SCREEN_WIDTH and text_rect.top < SCREEN_HEIGHT:
                    bg_rect = text_rect.inflate(4, 2)
                    pygame.draw.rect(screen, WHITE, bg_rect)
                    screen.blit(dim_text, text_rect)

def draw_grid():
    spacing_m = 1.0
    line_spacing_pixels = spacing_m * pixels_per_meter
    if line_spacing_pixels < 5: return

    world_top_left_m = screen_to_world_m((SIDEBAR_WIDTH, 0))
    world_bottom_right_m = screen_to_world_m((SCREEN_WIDTH, SCREEN_HEIGHT))

    start_mx = math.floor(world_top_left_m[0] / spacing_m) * spacing_m
    end_mx = math.ceil(world_bottom_right_m[0] / spacing_m) * spacing_m
    m_x = start_mx
    while m_x <= end_mx:
         screen_x, _ = world_m_to_screen((m_x, world_top_left_m[1]))
         if screen_x >= SIDEBAR_WIDTH:
             pygame.draw.line(screen, GRID_COLOR, (screen_x, 0), (screen_x, SCREEN_HEIGHT))
         m_x += spacing_m

    start_my = math.floor(world_top_left_m[1] / spacing_m) * spacing_m
    end_my = math.ceil(world_bottom_right_m[1] / spacing_m) * spacing_m
    m_y = start_my
    while m_y <= end_my:
        _, screen_y = world_m_to_screen((world_top_left_m[0], m_y))
        pygame.draw.line(screen, GRID_COLOR, (SIDEBAR_WIDTH, screen_y), (SCREEN_WIDTH, screen_y))
        m_y += spacing_m

def snap_to_orthogonal_m(start_point_m, current_point_m):
    dx_m = current_point_m[0] - start_point_m[0]
    dy_m = current_point_m[1] - start_point_m[1]
    if abs(dx_m) > abs(dy_m):
        snapped_point_m = (current_point_m[0], start_point_m[1])
    else:
        snapped_point_m = (start_point_m[0], current_point_m[1])
    return snapped_point_m

def draw_ruler(screen, p1_m, p2_m, current_mouse_m, snapped_indicator_m):
    if p1_m is None:
        if snapped_indicator_m:
            snap_screen = world_m_to_screen(snapped_indicator_m)
            pygame.draw.circle(screen, RULER_COLOR, snap_screen, 5, 1)
        return

    end_point_m = p2_m if p2_m is not None else snapped_indicator_m if snapped_indicator_m is not None else current_mouse_m
    if end_point_m is None: return

    p1_screen = world_m_to_screen(p1_m)
    p2_screen = world_m_to_screen(end_point_m)

    pygame.draw.line(screen, RULER_COLOR, p1_screen, p2_screen, 2)
    pygame.draw.circle(screen, RULER_COLOR, p1_screen, 5, 2)
    pygame.draw.circle(screen, RULER_COLOR, p2_screen, 5, 2)

    distance_m = calculate_distance_m(p1_m, end_point_m)
    dist_text = small_font.render(f"{distance_m:.3f}m", True, BLACK)
    mid_x = (p1_screen[0] + p2_screen[0]) // 2
    mid_y = (p1_screen[1] + p2_screen[1]) // 2
    text_rect = dist_text.get_rect(center=(mid_x, mid_y - 15))
    bg_rect = text_rect.inflate(4, 2)
    pygame.draw.rect(screen, WHITE, bg_rect)
    screen.blit(dist_text, text_rect)

    if p2_m is None and snapped_indicator_m:
         snap_screen = world_m_to_screen(snapped_indicator_m)
         pygame.draw.circle(screen, RULER_COLOR, snap_screen, 5, 1)

# --- (حلقة اللعبة الرئيسية) ---
while running:
    mouse_pos = pygame.mouse.get_pos()
    mouse_pos_m = screen_to_world_m(mouse_pos)

    # --- (معالجة الأحداث) ---
    ruler_snapped_point_m = None
    if current_tool == "MEASURE":
        snap_tolerance_pixels = 10
        snap_tolerance_m = snap_tolerance_pixels / pixels_per_meter if pixels_per_meter > 0 else 0.1
        ruler_snapped_point_m = find_closest_endpoint_m(mouse_pos_m, elements, snap_tolerance_m)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEWHEEL:
             if mouse_pos[0] >= SIDEBAR_WIDTH:
                world_mx_before, world_my_before = mouse_pos_m
                old_ppm = pixels_per_meter
                if event.y > 0: pixels_per_meter *= ZOOM_FACTOR_STEP
                elif event.y < 0: pixels_per_meter /= ZOOM_FACTOR_STEP
                pixels_per_meter = max(MIN_PIXELS_PER_METER, min(MAX_PIXELS_PER_METER, pixels_per_meter))
                new_ppm = pixels_per_meter
                if old_ppm == 0: continue
                screen_mouse_x_drawing = mouse_pos[0] - SIDEBAR_WIDTH
                screen_mouse_y = mouse_pos[1]
                view_offset_x = screen_mouse_x_drawing - world_mx_before * new_ppm
                view_offset_y = screen_mouse_y - world_my_before * new_ppm

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                clicked_sidebar = False
                if mouse_pos[0] < SIDEBAR_WIDTH:
                    clicked_sidebar = True
                    clicked_on_input = False
                    for input_type, rect in INPUT_RECTS.items():
                        if rect.collidepoint(mouse_pos):
                            active_input = input_type
                            clicked_on_input = True
                            break
                    if not clicked_on_input:
                        if active_input is not None: active_input = None
                        old_tool = current_tool
                        for i, rect in enumerate(TOOL_RECTS):
                            if rect.collidepoint(mouse_pos):
                                current_tool = TOOLS[i]
                                drawing = False
                                start_pos_m = None
                                if old_tool == "MEASURE" and current_tool != "MEASURE":
                                    ruler_point1_m = None
                                    ruler_point2_m = None
                                break
                else: # النقرة في منطقة الرسم
                     if active_input is not None: active_input = None

                if not clicked_sidebar:
                    if current_tool == "WALL":
                        drawing = True
                        start_pos_m = mouse_pos_m

                    elif current_tool == "DOOR" or current_tool == "WINDOW":
                        width_m = 0.1 # قيمة افتراضية صغيرة في حالة الخطأ
                        input_key = 'door' if current_tool == "DOOR" else 'window'
                        try:
                            width_m_input = float(input_values[input_key])
                            if width_m_input > 0: width_m = width_m_input
                            else: print(f"تحذير: العرض يجب أن يكون موجبًا. استخدام {width_m} متر.")
                        except ValueError: print(f"تحذير: رقم غير صالح. استخدام {width_m} متر.")

                        walls_only = [elem for elem in elements if elem['type'] == 'wall']
                        target_wall = find_closest_wall_m(mouse_pos_m, walls_only)

                        if target_wall:
                            current_state_copy = copy.deepcopy(elements)
                            history.append(current_state_copy)
                            if len(history) > MAX_HISTORY_SIZE: history.pop(0)

                            _, insert_pos_m = point_segment_distance_m(mouse_pos_m, target_wall['start_m'], target_wall['end_m'])
                            elem_type = 'door' if current_tool == "DOOR" else 'window'
                            elements.append({
                                'type': elem_type, 'pos_m': insert_pos_m,
                                'width_m': width_m, 'wall_ref': target_wall
                            })
                        else: print("خطأ: يجب وضع الباب/النافذة على جدار موجود!")

                    elif current_tool == "DELETE":
                        element_to_delete = find_element_at_pos_m(mouse_pos_m, elements)
                        if element_to_delete:
                            current_state_copy = copy.deepcopy(elements)
                            history.append(current_state_copy)
                            if len(history) > MAX_HISTORY_SIZE: history.pop(0)

                            if element_to_delete['type'] == 'wall':
                                elements_to_remove = [element_to_delete]
                                elements_copy = list(elements)
                                for other_elem in elements_copy:
                                    if other_elem.get('wall_ref') == element_to_delete:
                                        if other_elem not in elements_to_remove:
                                            elements_to_remove.append(other_elem)
                                num_attached = len(elements_to_remove) - 1
                                for item in elements_to_remove:
                                    if item in elements: elements.remove(item)
                                print(f"تم حذف الجدار و {num_attached} عنصر مرتبط به.")
                            else:
                                if element_to_delete in elements:
                                    elements.remove(element_to_delete)
                                    print(f"تم حذف {element_to_delete['type']}.")
                        else: print("لم يتم العثور على عنصر للحذف في هذا الموقع.")

                    elif current_tool == "MEASURE":
                        click_pos_m = ruler_snapped_point_m if ruler_snapped_point_m else mouse_pos_m
                        if ruler_point1_m is None:
                            ruler_point1_m = click_pos_m
                            ruler_point2_m = None
                        else:
                            ruler_point2_m = click_pos_m

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                if drawing and current_tool == "WALL" and start_pos_m:
                    snapped_end_pos_m = snap_to_orthogonal_m(start_pos_m, mouse_pos_m)
                    length_m = calculate_distance_m(start_pos_m, snapped_end_pos_m)
                    min_length_pixels = 5
                    min_length_m = min_length_pixels / pixels_per_meter if pixels_per_meter > 0 else 0.01

                    if length_m > min_length_m:
                        current_state_copy = copy.deepcopy(elements)
                        history.append(current_state_copy)
                        if len(history) > MAX_HISTORY_SIZE: history.pop(0)
                        elements.append({
                            'type': 'wall', 'start_m': start_pos_m,
                            'end_m': snapped_end_pos_m, 'length_m': length_m
                        })
                    else: print("الجدار قصير جدًا، لم يتم إضافته.")
                    drawing = False
                    start_pos_m = None

        elif event.type == pygame.KEYDOWN:
            if active_input:
                current_string = input_values[active_input]
                if event.key == pygame.K_BACKSPACE:
                    input_values[active_input] = current_string[:-1]
                elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                    try:
                       val = float(input_values[active_input])
                       if val <= 0: print("تحذير: القيمة يجب أن تكون موجبة.")
                    except ValueError: print("تحذير: صيغة الرقم غير صالحة.")
                    active_input = None
                elif event.unicode.isdigit() or (event.unicode == '.' and '.' not in current_string):
                    input_values[active_input] += event.unicode

            elif event.key == pygame.K_z:
                if history:
                    elements = history.pop()
                    print("تم التراجع عن الإجراء الأخير.")
                else: print("لا يوجد شيء للتراجع عنه.")

    # --- (دورة الرسم) ---
    screen.fill(WHITE)
    drawing_area_rect = pygame.Rect(SIDEBAR_WIDTH, 0, DRAWING_AREA_WIDTH, SCREEN_HEIGHT)
    screen.set_clip(drawing_area_rect)

    draw_grid()
    draw_elements()

    if drawing and current_tool == "WALL" and start_pos_m:
        snapped_mouse_pos_m = snap_to_orthogonal_m(start_pos_m, mouse_pos_m)
        start_screen = world_m_to_screen(start_pos_m)
        snapped_end_screen = world_m_to_screen(snapped_mouse_pos_m)
        pygame.draw.line(screen, RED, start_screen, snapped_end_screen, 2)
        current_dist_m = calculate_distance_m(start_pos_m, snapped_mouse_pos_m)
        temp_dim_text = small_font.render(f"{current_dist_m:.2f}m", True, RED)
        screen.blit(temp_dim_text, (snapped_end_screen[0] + 10, snapped_end_screen[1]))

    if current_tool == "MEASURE":
        draw_ruler(screen, ruler_point1_m, ruler_point2_m, mouse_pos_m, ruler_snapped_point_m)

    screen.set_clip(None)
    draw_sidebar(current_tool, input_values, active_input) # استدعاء دالة الشريط الجانبي المعدلة

    pygame.display.flip()
    clock.tick(60)

# --- (إنهاء Pygame) ---
pygame.quit()