import sqlite3
import calendar
import os
import urllib.request
from datetime import datetime, date
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp, sp
from kivy.graphics import Color, RoundedRectangle, Rectangle, Line
from kivy.uix.popup import Popup
from kivy.core.window import Window

# PDF Library
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except ImportError:
    pass

# --- PATH SETTINGS ---
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
BG_PATH = os.path.join(CUR_DIR, 'background.jpg')
DB_PATH = os.path.join(CUR_DIR, 'hira_diary.db')

# --- AUTO FONT DOWNLOADER ---
def ensure_fonts_exist():
    gu_font = os.path.join(CUR_DIR, 'NotoSansGujarati-Regular.ttf')
    hi_font = os.path.join(CUR_DIR, 'NotoSansDevanagari-Regular.ttf')
    gu_url = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansGujarati/NotoSansGujarati-Regular.ttf"
    hi_url = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf"
    try:
        if not os.path.exists(gu_font): urllib.request.urlretrieve(gu_url, gu_font)
        if not os.path.exists(hi_font): urllib.request.urlretrieve(hi_url, hi_font)
    except Exception: pass

ensure_fonts_exist()

FONTS = {
    'EN': 'Roboto',  
    'GU': os.path.join(CUR_DIR, 'NotoSansGujarati-Regular.ttf') if os.path.exists(os.path.join(CUR_DIR, 'NotoSansGujarati-Regular.ttf')) else 'Roboto', 
    'HI': os.path.join(CUR_DIR, 'NotoSansDevanagari-Regular.ttf') if os.path.exists(os.path.join(CUR_DIR, 'NotoSansDevanagari-Regular.ttf')) else 'Roboto'
}

NEON_CYAN = (0.0, 0.9, 1.0, 1)           
TEXT_WHITE = (0.95, 0.95, 0.95, 1)       
CARD_BG = (0.08, 0.11, 0.16, 0.9)        
DIAMOND_TYPES = ['A', 'B', 'C', 'D']

TEXTS = {
    'EN': {'btn_add': 'ADD RECORD', 'btn_view': 'VIEW HISTORY', 'btn_rates': 'SET RATES', 'save': 'SAVE', 'pdf': 'DOWNLOAD PDF', 'footer_qty': 'TOTAL : ', 'footer_rs': 'NET ₹ : ', 'delete': 'Delete', 'okay': 'Okay'},
    'GU': {'btn_add': 'નવી એન્ટ્રી લખો', 'btn_view': 'રેકોર્ડ જુવો', 'btn_rates': 'ભાવ સેટિંગ', 'save': 'સેવ', 'pdf': 'PDF ડાઉનલોડ કરો', 'footer_qty': 'કુલ નંગ : ', 'footer_rs': 'કુલ ₹ : ', 'delete': 'કાઢી નાખો', 'okay': 'ઓકે'},
    'HI': {'btn_add': 'नई एंट्री', 'btn_view': 'रिकॉर्ड देखें', 'btn_rates': 'रेट सेटिंग', 'save': 'सेव', 'pdf': 'PDF डाउनलोड', 'footer_qty': 'कुल नंग : ', 'footer_rs': 'कुल ₹ : ', 'delete': 'हटाएं', 'okay': 'ठीक है'}
}

def setup_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS entries (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, type TEXT, quantity INTEGER, rate REAL, total REAL)')
    cursor.execute('CREATE TABLE IF NOT EXISTS rates (type TEXT PRIMARY KEY, rate REAL)')
    cursor.execute("SELECT COUNT(*) FROM rates")
    if cursor.fetchone()[0] == 0:
        for t in DIAMOND_TYPES: cursor.execute("INSERT INTO rates (type, rate) VALUES (?, 0.0)", (t,))
    conn.commit(); conn.close()

# --- CUSTOM UI ---
class NeonButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''; self.background_color = (0, 0, 0, 0); self.color = NEON_CYAN
        with self.canvas.before:
            Color(*CARD_BG); self.bg = RoundedRectangle(radius=[dp(10)])
            Color(*NEON_CYAN); self.outline = Line(width=dp(1.1))
        self.bind(pos=self.update_graphics, size=self.update_graphics)
    def update_graphics(self, *args):
        self.bg.pos = self.pos; self.bg.size = self.size
        self.outline.rounded_rectangle = [self.x, self.y, self.width, self.height, dp(10)]

class CyberInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''; self.background_color = (0.1, 0.1, 0.15, 0.8); self.foreground_color = (1, 1, 1, 1)
        self.cursor_color = NEON_CYAN; self.halign = 'center'; self.multiline = False

class CyberCard(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'; self.size_hint_y = None; self.height = dp(65); self.padding = [dp(15), dp(5)]
        with self.canvas.before:
            Color(1, 1, 1, 0.3) 
            self.bg = RoundedRectangle(radius=[dp(10)])
        self.bind(pos=self.update_graphics, size=self.update_graphics)
    def update_graphics(self, *args):
        self.bg.pos = self.pos; self.bg.size = self.size

class CalendarPopup(Popup):
    def __init__(self, callback, font, **kwargs):
        super().__init__(**kwargs)
        self.title = "Select Date"; self.size_hint = (0.9, 0.7); self.callback = callback
        self.year, self.month = date.today().year, date.today().month
        layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(5))
        header = BoxLayout(size_hint_y=None, height=dp(50))
        header.add_widget(Button(text="<", on_press=self.prev_m))
        self.month_lbl = Label(text="", bold=True, font_name=font); header.add_widget(self.month_lbl)
        header.add_widget(Button(text=">", on_press=self.next_m))
        layout.add_widget(header)
        self.grid = GridLayout(cols=7, spacing=dp(2)); layout.add_widget(self.grid)
        self.content = layout; self.update_cal()
    def prev_m(self, *a):
        self.month -= 1
        if self.month < 1: self.month = 12; self.year -= 1
        self.update_cal()
    def next_m(self, *a):
        self.month += 1
        if self.month > 12: self.month = 1; self.year += 1
        self.update_cal()
    def update_cal(self):
        self.grid.clear_widgets(); self.month_lbl.text = f"{calendar.month_name[self.month]} {self.year}"
        cal = calendar.monthcalendar(self.year, self.month)
        for week in cal:
            for day in week:
                if day == 0: self.grid.add_widget(Label())
                else:
                    btn = Button(text=str(day), on_press=lambda x, d=day: self.pick(d))
                    self.grid.add_widget(btn)
    def pick(self, d):
        self.callback(f"{d:02d}/{self.month:02d}/{self.year}"); self.dismiss()

class FuturisticHeader(BoxLayout):
    def __init__(self, screen_obj, **kwargs):
        super().__init__(**kwargs)
        self.screen_obj = screen_obj; self.orientation = 'horizontal'; self.size_hint_y = None; self.height = dp(50)
        with self.canvas.before:
            Color(0, 0, 0, 0); self.bg = Rectangle()
            Color(*NEON_CYAN); self.line = Line(width=dp(1))
        self.bind(pos=self.update_graphics, size=self.update_graphics)
        self.back_btn = Button(text="<", bold=True, size_hint_x=None, width=dp(50), background_color=(0,0,0,0), color=NEON_CYAN)
        self.back_btn.bind(on_press=self.go_back)
        self.title_label = Label(text="", bold=True, color=(0, 0, 0, 1), font_size=sp(16))
        self.add_widget(self.back_btn); self.add_widget(self.title_label); self.add_widget(Label(size_hint_x=None, width=dp(50)))
    def update_graphics(self, *args):
        self.bg.pos = self.pos; self.bg.size = self.size
        self.line.points = [self.x, self.y, self.right, self.y]
    def go_back(self, instance):
        if self.screen_obj.name == 'add': self.screen_obj.save_entry(None)
        elif self.screen_obj.name == 'rates': self.screen_obj.save_rates(None)
        self.screen_obj.manager.transition = SlideTransition(direction='right'); self.screen_obj.manager.current = 'home'

# --- SCREENS ---
class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(1, 1, 1, 1); self.bg = Rectangle(source=BG_PATH)
        self.bind(pos=self.update_bg, size=self.update_bg)
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(12))
        top = AnchorLayout(anchor_x='right', size_hint_y=None, height=dp(40))
        self.lang_btn = NeonButton(size_hint=(None, None), size=(dp(90), dp(35)), font_size=sp(12))
        self.lang_btn.bind(on_press=self.toggle_lang); top.add_widget(self.lang_btn); layout.add_widget(top)
        layout.add_widget(Label(size_hint_y=0.4)) 
        for s in ['add', 'view', 'rates']:
            btn = NeonButton(size_hint_y=None, height=dp(55))
            btn.bind(on_press=lambda x, target=s: self.go(target))
            setattr(self, f'btn_{s}', btn); layout.add_widget(btn)
        self.add_widget(layout)
    def update_bg(self, *args): self.bg.pos, self.bg.size = self.pos, self.size
    def toggle_lang(self, i):
        a = App.get_running_app(); l = ['EN', 'GU', 'HI']
        a.lang = l[(l.index(a.lang)+1)%3]; a.update_all_screens()
    def go(self, s):
        self.manager.transition = SlideTransition(direction='left'); self.manager.current = s
        if hasattr(self.manager.get_screen(s), 'load_data'): self.manager.get_screen(s).load_data()
    def update_ui(self, l, f):
        t = TEXTS[l]; self.lang_btn.text = f"LANG: {l}"; self.lang_btn.font_name = f
        self.btn_add.text = t['btn_add']; self.btn_view.text = t['btn_view']; self.btn_rates.text = t['btn_rates']
        self.btn_add.font_name = f; self.btn_view.font_name = f; self.btn_rates.font_name = f

class ViewRecordsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(1, 1, 1, 1); self.bg = Rectangle(source=BG_PATH)
        self.bind(pos=self.update_bg, size=self.update_bg)
        self.layout = BoxLayout(orientation='vertical')
        self.header = FuturisticHeader(self); self.layout.add_widget(self.header)
        self.scroll = ScrollView(); self.list = BoxLayout(orientation='vertical', size_hint_y=None, padding=dp(8), spacing=dp(8))
        self.list.bind(minimum_height=self.list.setter('height')); self.scroll.add_widget(self.list)
        self.layout.add_widget(self.scroll)
        
        self.footer = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(100), padding=dp(5))
        label_card = BoxLayout(size_hint_y=None, height=dp(40), padding=[dp(10), 0])
        with label_card.canvas.before:
            Color(1, 1, 1, 0.4) 
            self.footer_bg = RoundedRectangle(radius=[dp(10)])
        label_card.bind(pos=self.update_footer_bg, size=self.update_footer_bg)
        
        self.f_qty = Label(bold=True, font_size=sp(13), color=(0, 0, 0, 1)) 
        self.f_rs = Label(bold=True, color=(0, 0, 0, 1), font_size=sp(13)) 
        label_box = BoxLayout(); label_box.add_widget(self.f_qty); label_box.add_widget(self.f_rs)
        label_card.add_widget(label_box)
        
        self.footer.add_widget(label_card)
        self.pdf_btn = NeonButton(size_hint_y=None, height=dp(45))
        self.pdf_btn.bind(on_press=self.generate_pdf)
        self.footer.add_widget(self.pdf_btn)
        
        self.layout.add_widget(self.footer); self.add_widget(self.layout)

    def update_bg(self, *args): self.bg.pos, self.bg.size = self.pos, self.size
    def update_footer_bg(self, instance, value):
        self.footer_bg.pos = instance.pos; self.footer_bg.size = instance.size

    def update_ui(self, l, f):
        t = TEXTS[l]; self.header.title_label.text = t['btn_view']; self.header.title_label.font_name = f
        self.pdf_btn.text = t['pdf']; self.pdf_btn.font_name = f
        self.f_qty.font_name = f; self.f_rs.font_name = f; self.load_data()

    def load_data(self):
        self.list.clear_widgets()
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute("SELECT date, SUM(total) FROM entries GROUP BY date ORDER BY date DESC")
        data = cur.fetchall(); l = App.get_running_app().lang; f = FONTS[l]
        for d_str, tot_rs in data:
            card = CyberCard(); row = BoxLayout()
            row.add_widget(Label(text=f"// {d_str}", bold=True, color=(0, 0, 0, 1), font_name=f, halign='left', size_hint_x=0.5))
            row.add_widget(Label(text=f"₹ {tot_rs:.2f}", bold=True, color=(0, 0, 0, 1), font_name=f, halign='right', size_hint_x=0.4))
            i_btn = Button(text="(i)", size_hint_x=None, width=dp(35), background_color=(0,0,0,0), color=(0,0,0,1), bold=True)
            i_btn.bind(on_press=lambda x, dt=d_str: self.show_detail(dt))
            row.add_widget(i_btn); card.add_widget(row); self.list.add_widget(card)
        cur.execute("SELECT SUM(quantity), SUM(total) FROM entries")
        res = cur.fetchone(); self.f_qty.text = f"{TEXTS[l]['footer_qty']}{res[0] if res[0] else 0}"
        self.f_rs.text = f"{TEXTS[l]['footer_rs']}{res[1] if res[1] else 0:.2f}"; conn.close()

    def show_detail(self, date_str):
        l = App.get_running_app().lang; f, t = FONTS[l], TEXTS[l]
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute("SELECT type, quantity, rate, total FROM entries WHERE date=?", (date_str,))
        rows = cur.fetchall(); conn.close()
        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(8))
        content.add_widget(Label(text=f"DATE: {date_str}", bold=True, font_name=f, font_size=sp(18), color=(0,0,0,1)))
        grand_tot = 0
        for r in rows:
            line = f"{r[0]} : {r[1]} * {r[2]} = {r[3]:.2f}"; content.add_widget(Label(text=line, font_name=f, font_size=sp(14), color=(0,0,0,1)))
            grand_tot += r[3]
        content.add_widget(Label(text=f"TOTAL = {grand_tot:.2f}", bold=True, color=(0, 0, 0, 1), font_name=f, font_size=sp(16)))
        btns = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(8))
        d_btn = Button(text=TEXTS[l]['delete'] if 'delete' in TEXTS[l] else "Del", background_color=(1, 0.2, 0.2, 1)); d_btn.bind(on_press=lambda x: self.confirm_delete(date_str, p))
        o_btn = Button(text=TEXTS[l]['okay'] if 'okay' in TEXTS[l] else "Ok", background_color=(0, 0.8, 0.6, 1)); o_btn.bind(on_press=lambda x: p.dismiss())
        btns.add_widget(d_btn); btns.add_widget(o_btn); content.add_widget(btns)
        p = Popup(title="", content=content, size_hint=(0.8, 0.6), background_color=(1,1,1,0.9)); p.open()

    def confirm_delete(self, date_str, popup):
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute("DELETE FROM entries WHERE date=?", (date_str,)); conn.commit(); conn.close()
        popup.dismiss(); self.load_data()
    
    def generate_pdf(self, instance):
        try:
            filename = "/storage/emulated/0/Download/GemTrack_Report.pdf"
            c = canvas.Canvas(filename, pagesize=letter)
            c.setFont("Helvetica-Bold", 16); c.drawString(200, 750, "GEMTRACK REPORT")
            c.setFont("Helvetica-Bold", 12); c.drawString(50, 710, "Date"); c.drawString(150, 710, "Type"); c.drawString(250, 710, "Qty"); c.drawString(450, 710, "Total")
            c.line(50, 705, 550, 705)
            conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
            cur.execute("SELECT date, type, quantity, total FROM entries ORDER BY date DESC")
            records = cur.fetchall(); grand_qty = 0; grand_total = 0; y = 685
            for r in records:
                c.setFont("Helvetica", 10); c.drawString(50, y, str(r[0])); c.drawString(150, y, str(r[1])); c.drawString(250, y, str(r[2])); c.drawString(450, y, str(r[3]))
                grand_qty += int(r[2]); grand_total += float(r[3]); y -= 20
                if y < 100: c.showPage(); y = 750
            c.line(50, y, 550, y); y -= 25; c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, f"GRAND TOTAL QUANTITY: {grand_qty}"); y -= 20
            c.drawString(50, y, f"GRAND NET AMOUNT: Rs. {grand_total:.2f}")
            c.save(); conn.close()
            Popup(title="Success", content=Label(text=f"PDF Saved in Downloads!"), size_hint=(0.9, 0.3)).open()
        except Exception as e:
            filename = os.path.join(CUR_DIR, "GemTrack_Report.pdf")
            c = canvas.Canvas(filename, pagesize=letter)
            c.save()
            Popup(title="Error", content=Label(text=f"Check Permission\nSaved in: {filename}"), size_hint=(0.9, 0.3)).open()

class RatesScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(1, 1, 1, 1); self.bg = Rectangle(source=BG_PATH)
        self.bind(pos=self.update_bg, size=self.update_bg)
        layout = BoxLayout(orientation='vertical'); layout.add_widget(FuturisticHeader(self))
        self.inputs = {}
        grid = GridLayout(cols=2, padding=dp(20), spacing=dp(10), row_default_height=dp(40), row_force_default=True)
        for t in DIAMOND_TYPES:
            grid.add_widget(Label(text=f"[{t}]", color=NEON_CYAN, bold=True))
            inp = TextInput(input_filter='float', multiline=False, halign='center'); self.inputs[t] = inp; grid.add_widget(inp)
        layout.add_widget(grid); self.save_btn = NeonButton(size_hint_y=None, height=dp(50))
        self.save_btn.bind(on_press=self.save_rates); layout.add_widget(self.save_btn); self.add_widget(layout)
    def update_bg(self, *args): self.bg.pos, self.bg.size = self.pos, self.size
    def update_ui(self, l, f):
        t = TEXTS[l]; self.save_btn.text = t['save']; self.save_btn.font_name = f
    def load_data(self):
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor(); cur.execute("SELECT type, rate FROM rates")
        for r in cur.fetchall():
            if r[0] in self.inputs: self.inputs[r[0]].text = str(r[1])
        conn.close()
    def save_rates(self, i):
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        for t, inp in self.inputs.items():
            rate_val = inp.text.strip()
            if rate_val: cur.execute("UPDATE rates SET rate=? WHERE type=?", (float(rate_val), t))
        conn.commit(); conn.close()
        if i is not None: self.manager.current = 'home'

class AddEntryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(1, 1, 1, 1); self.bg = Rectangle(source=BG_PATH)
        self.bind(pos=self.update_bg, size=self.update_bg)
        layout = BoxLayout(orientation='vertical'); layout.add_widget(FuturisticHeader(self))
        self.date_btn = Button(
            text=date.today().strftime("%d/%m/%Y"), 
            size_hint_y=None, height=dp(45), background_normal='', background_color=(0,0,0,0), color=(0, 0, 0, 1), bold=True
        )
        self.date_btn.bind(on_press=self.open_cal); layout.add_widget(self.date_btn)
        self.rows = {}
        grid = GridLayout(cols=3, padding=dp(10), spacing=dp(8), row_default_height=dp(38), row_force_default=True)
        for t in DIAMOND_TYPES:
            grid.add_widget(Label(text=t, bold=True, color=NEON_CYAN))
            qty = CyberInput(input_filter='int'); grid.add_widget(qty)
            rate = Label(text="0.0", color=(0, 0, 0, 1), bold=True); grid.add_widget(rate); self.rows[t] = (qty, rate)
        layout.add_widget(grid)
        self.save_btn = NeonButton(size_hint_y=None, height=dp(55))
        self.save_btn.bind(on_press=self.save_entry); layout.add_widget(self.save_btn); self.add_widget(layout)
    def update_bg(self, *args): self.bg.pos, self.bg.size = self.pos, self.size
    def open_cal(self, *a):
        f = FONTS[App.get_running_app().lang]
        CalendarPopup(callback=self.set_dt, font=f).open()
    def set_dt(self, dt): self.date_btn.text = dt
    def update_ui(self, l, f):
        t = TEXTS[l]; self.save_btn.text = t['save']; self.save_btn.font_name = f
    def load_data(self):
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor(); cur.execute("SELECT type, rate FROM rates")
        for r in cur.fetchall():
            if r[0] in self.rows: self.rows[r[0]][1].text = str(r[1])
        conn.close()
    def save_entry(self, i):
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor(); dt = self.date_btn.text
        for t, (qty_in, rate_lbl) in self.rows.items():
            q_text = qty_in.text.strip()
            if q_text:
                q = int(q_text); r = float(rate_lbl.text)
                if q > 0: cur.execute("INSERT INTO entries (date, type, quantity, rate, total) VALUES (?,?,?,?,?)", (dt, t, q, r, q*r))
        conn.commit(); conn.close()
        for q_in, r_l in self.rows.values(): q_in.text = ""
        if i is not None: self.manager.current = 'home'

class MainApp(App):
    def __init__(self, **kwargs): 
        super().__init__(**kwargs)
        # Savthi pela English language rakhva mate
        self.lang = 'EN' 
    def build(self):
        setup_database(); self.sm = ScreenManager()
        self.sm.add_widget(HomeScreen(name='home'))
        self.sm.add_widget(RatesScreen(name='rates'))
        self.sm.add_widget(AddEntryScreen(name='add'))
        self.sm.add_widget(ViewRecordsScreen(name='view'))
        Window.bind(on_keyboard=self.on_back_button)
        self.update_all_screens(); return self.sm
    def on_back_button(self, window, key, *args):
        if key == 27:
            if self.sm.current != 'home':
                curr = self.sm.get_screen(self.sm.current)
                if self.sm.current == 'add': curr.save_entry(None)
                elif self.sm.current == 'rates': curr.save_rates(None)
                self.sm.transition.direction = 'right'; self.sm.current = 'home'
                return True
        return False
    def update_all_screens(self, *args):
        f = FONTS[self.lang]
        for s in self.sm.screens:
            if hasattr(s, 'update_ui'): s.update_ui(self.lang, f)

if __name__ == '__main__': MainApp().run()
