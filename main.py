import os, sys, re, csv, json, shutil, subprocess, zipfile, urllib.request
from datetime import datetime
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView, QComboBox, QProgressBar, QAbstractItemView,
    QFileDialog, QDialog, QListWidget, QListWidgetItem, QDialogButtonBox, QPlainTextEdit, QMenu)

APP_NAME = 'North Debloater'
IS_WIN = os.name == 'nt'
ADB_NAME = 'adb.exe' if IS_WIN else 'adb'
PT_URL = 'https://dl.google.com/android/repository/platform-tools-latest-%s.zip' % ('windows' if IS_WIN else 'linux')
UAD_URL = 'https://raw.githubusercontent.com/Universal-Debloater-Alliance/universal-android-debloater-next-generation/main/resources/assets/uad_lists.json'

CRITICAL = ('systemui','settings','telephony','phone','permissioncontroller','packageinstaller','providers','inputmethod','launcher','keychain','keystore','framework','connectivity','emergency','storage','media','android')
CAUTION = ('samsung','knox','oneui','google','gms','carrier','wearable','health','bixby','dex','secure','wallet','smartthings')
GREEN, YELLOW, RED, GRAY = '#4ade80', '#fbbf24', '#f87171', '#cbd5e1'
DANGEROUS = {'CAMERA','RECORD_AUDIO','ACCESS_FINE_LOCATION','ACCESS_COARSE_LOCATION','ACCESS_BACKGROUND_LOCATION','READ_CONTACTS','WRITE_CONTACTS','READ_SMS','SEND_SMS','RECEIVE_SMS','READ_CALL_LOG','WRITE_CALL_LOG','READ_PHONE_STATE','CALL_PHONE','READ_CALENDAR','WRITE_CALENDAR','BODY_SENSORS','READ_EXTERNAL_STORAGE','WRITE_EXTERNAL_STORAGE','MANAGE_EXTERNAL_STORAGE','SYSTEM_ALERT_WINDOW','BIND_ACCESSIBILITY_SERVICE','READ_MEDIA_IMAGES','READ_MEDIA_VIDEO','READ_MEDIA_AUDIO'}

MODE_USER, MODE_ALL, MODE_REMOVED = 0, 1, 2
MODES = ['Kullanıcı uygulamaları', 'Tüm paketler (sistem dahil)', 'Kaldırılmış paketler (geri yüklenebilir)']
ST_ACTIVE, ST_DISABLED, ST_REMOVED = 'Aktif', 'Devre dışı', 'Kaldırılmış'


# ---------- yollar / veri ----------
def app_dir():
    return os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))

def data_dir():
    base = os.environ.get('LOCALAPPDATA') or os.path.expanduser('~')
    path = os.path.join(base, 'NorthDebloater'); os.makedirs(path, exist_ok=True); return path

def resource(name):
    c = [os.path.join(getattr(sys, '_MEIPASS', ''), name), os.path.join(app_dir(), name), os.path.join(os.path.dirname(os.path.abspath(__file__)), name)]
    return next((p for p in c if os.path.isfile(p)), None)

def load_json(path):
    try:
        with open(path, encoding='utf-8') as f: return json.load(f)
    except Exception: return {}

BUNDLED = load_json(resource('packages_db.json') or '')
OWN = BUNDLED.get('packages', {}); PROFILES = BUNDLED.get('profiles', {})
COMMUNITY_PATH = os.path.join(data_dir(), 'uad_lists.json')
COMMUNITY = load_json(COMMUNITY_PATH)
COMMUNITY_MAP = {'Recommended': 'safe', 'Advanced': 'caution', 'Expert': 'caution', 'Unsafe': 'critical'}
RISK_VIEW = {'safe': ('DÜŞÜK', GREEN), 'caution': ('DİKKAT', YELLOW), 'critical': ('KRİTİK', RED)}

def info(pkg, mode=MODE_USER):
    """(uygulama adı, risk etiketi, renk, açıklama, risk anahtarı)"""
    if pkg in OWN:
        e = OWN[pkg]; lab, col = RISK_VIEW[e['risk']]; return e['name'], lab, col, e['desc'], e['risk']
    if pkg in COMMUNITY:
        e = COMMUNITY[pkg]; k = COMMUNITY_MAP.get(e.get('removal'), 'caution'); lab, col = RISK_VIEW[k]
        d = ' '.join(e.get('description', '').split())[:220]
        return '', lab, col, d + ' (topluluk listesi)', k
    p = pkg.lower()
    if any(x in p for x in CRITICAL): return '', 'KRİTİK', RED, 'Sistem işlevleri bozulabilir.', 'critical'
    if any(x in p for x in CAUTION): return '', 'DİKKAT', YELLOW, 'Üretici/servis bağımlılığı olabilir.', 'caution'
    if mode != MODE_USER: return '', 'BİLİNMİYOR', GRAY, 'Sistem paketi olabilir; araştırmadan kaldırma.', 'unknown'
    return '', 'DÜŞÜK', GREEN, 'Üçüncü taraf uygulaması; yine de kontrol et.', 'safe'

def human(n):
    if n is None: return ''
    for u in ('B', 'KB', 'MB', 'GB'):
        if n < 1024 or u == 'GB': return f'{n:.0f} {u}' if u == 'B' else f'{n:.1f} {u}'
        n /= 1024

def log_action(action, dev, pkg, ok, msg):
    try:
        with open(os.path.join(data_dir(), 'islem_gunlugu.txt'), 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}\t{dev}\t{action}\t{pkg}\t{'OK' if ok else 'HATA'}\t{msg}\n")
    except Exception: pass


# ---------- ADB ----------
def adb_path():
    dirs = [os.path.join(app_dir(), 'platform-tools'), os.path.join(data_dir(), 'platform-tools')]
    if getattr(sys, '_MEIPASS', None): dirs.insert(0, os.path.join(sys._MEIPASS, 'platform-tools'))
    cands = [os.path.join(d, ADB_NAME) for d in dirs] + [shutil.which('adb')]
    return next((p for p in cands if p and os.path.isfile(p)), None)

def download(url, dest):
    req = urllib.request.Request(url, headers={'User-Agent': 'NorthDebloater'})
    with urllib.request.urlopen(req, timeout=90) as r, open(dest, 'wb') as f: shutil.copyfileobj(r, f)

def download_adb():
    base = app_dir() if os.access(app_dir(), os.W_OK) else data_dir()
    tmp = os.path.join(base, 'platform-tools.zip'); download(PT_URL, tmp)
    with zipfile.ZipFile(tmp) as z: z.extractall(base)
    os.remove(tmp); exe = os.path.join(base, 'platform-tools', ADB_NAME)
    if not IS_WIN and os.path.isfile(exe): os.chmod(exe, 0o755)
    if not os.path.isfile(exe): raise RuntimeError('İndirilen pakette adb bulunamadı.')
    return exe

def update_community():
    tmp = COMMUNITY_PATH + '.tmp'; download(UAD_URL, tmp)
    data = load_json(tmp)
    if not isinstance(data, dict) or len(data) < 100: raise RuntimeError('Liste beklenen biçimde değil.')
    os.replace(tmp, COMMUNITY_PATH); COMMUNITY.clear(); COMMUNITY.update(data); return len(data)

def adb(args, timeout=30):
    exe = adb_path()
    if not exe: raise RuntimeError('ADB bulunamadı.')
    p = subprocess.run([exe, *args], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout,
                       creationflags=subprocess.CREATE_NO_WINDOW if IS_WIN else 0)
    if p.returncode: raise RuntimeError((p.stderr or p.stdout or 'ADB hatası').strip())
    return p.stdout.strip()

def stop_adb():
    """Kapanışta ADB sunucusunu durdur (yoksa adb.exe açık kalır, klasör silinemez). PATH'teki sistem adb'sine dokunma."""
    exe = adb_path()
    if not exe or exe == shutil.which('adb'): return
    try: subprocess.run([exe, 'kill-server'], capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW if IS_WIN else 0)
    except Exception: pass

def device_id():
    rows = [x.split() for x in adb(['devices']).splitlines()[1:] if x.strip()]
    ok = [x[0] for x in rows if len(x) > 1 and x[1] == 'device']
    if ok: return ok[0]
    if any(len(x) > 1 and x[1] == 'unauthorized' for x in rows): raise RuntimeError('Telefon ekranındaki USB hata ayıklama iznini onayla.')
    if any(len(x) > 1 and x[1] == 'offline' for x in rows): raise RuntimeError('Cihaz çevrimdışı görünüyor. Kabloyu çıkarıp tak, gerekirse USB hata ayıklamayı kapat/aç.')
    raise RuntimeError('Telefon bulunamadı. USB hata ayıklamayı aç, veri kablosu kullan ve izin penceresini onayla.')

def pkg_set(dev, *flags):
    out = adb(['-s', dev, 'shell', 'pm', 'list', 'packages', *flags])
    return {x.removeprefix('package:').strip() for x in out.splitlines() if x.startswith('package:')}

def getprop(dev, key):
    try: return adb(['-s', dev, 'shell', 'getprop', key])
    except Exception: return ''

def disk_sizes(dev):
    """Uygulama + veri boyutu (bayt). Cihaz desteklemezse boş döner."""
    try:
        out = adb(['-s', dev, 'shell', 'dumpsys', 'diskstats'], timeout=45)
        def arr(label):
            m = re.search(r'^\s*' + label + r':\s*(\[.*\])', out, re.M); return json.loads(m.group(1)) if m else None
        names, app, data = arr('Package Names'), arr('App Sizes'), arr('App Data Sizes')
        if not names or not app: return {}
        return {n: a + (data[i] if data and i < len(data) else 0) for i, (n, a) in enumerate(zip(names, app))}
    except Exception: return {}

def scan(mode):
    dev = device_id(); model = getprop(dev, 'ro.product.model'); brand = getprop(dev, 'ro.product.manufacturer')
    installed = pkg_set(dev); disabled = pkg_set(dev, '-d') & installed; removed = set()
    if mode == MODE_REMOVED: removed = pkg_set(dev, '-u') - installed; pk = removed
    elif mode == MODE_USER: pk = pkg_set(dev, '-3')
    else: pk = installed
    sizes = disk_sizes(dev) if mode != MODE_REMOVED else {}
    rows = [(p, ST_REMOVED if p in removed else ST_DISABLED if p in disabled else ST_ACTIVE, sizes.get(p)) for p in sorted(pk)]
    return {'dev': dev, 'model': model, 'brand': brand, 'rows': rows}

def package_details(dev, pkg):
    out = adb(['-s', dev, 'shell', 'dumpsys', 'package', pkg], timeout=40)
    g = lambda k: (re.search(k + r'=(.+)', out) or [None, ''])[1].strip()
    granted = {}
    for m in re.finditer(r'^\s+([A-Za-z0-9_.]+): granted=(true|false)', out, re.M): granted[m.group(1)] = m.group(2) == 'true'
    req = []
    m = re.search(r'requested permissions:\n((?:\s{4,}[A-Za-z0-9_.]+(?:: [^\n]*)?\n)+)', out)
    if m: req = [x.strip().split(':')[0] for x in m.group(1).splitlines()]
    path = ''
    try: path = adb(['-s', dev, 'shell', 'pm', 'path', pkg]).splitlines()[0].removeprefix('package:')
    except Exception: pass
    return {'version': g('versionName'), 'installed': g('firstInstallTime'), 'updated': g('lastUpdateTime'), 'installer': g('installerPackageName'),
            'path': path, 'granted': granted, 'requested': req}

def short_perm(p): return p.rsplit('.', 1)[-1]


class SizeItem(QTableWidgetItem):
    def __init__(self, n): super().__init__(human(n)); self.n = n or -1
    def __lt__(self, o): return self.n < getattr(o, 'n', -1)


class Worker(QThread):
    done = Signal(object, str)
    def __init__(self, fn): super().__init__(); self.fn = fn
    def run(self):
        try: self.done.emit(self.fn(), '')
        except Exception as e: self.done.emit(None, str(e))


class ChecklistDialog(QDialog):
    """Paket listesi (işaretli) + işlem seçimi."""
    def __init__(self, parent, title, intro, items, actions):
        super().__init__(parent); self.setWindowTitle(title); self.resize(620, 560)
        lay = QVBoxLayout(self); lab = QLabel(intro); lab.setWordWrap(True); lay.addWidget(lab)
        self.list = QListWidget(); lay.addWidget(self.list, 1)
        for pkg, label, checked in items:
            it = QListWidgetItem(label); it.setData(Qt.ItemDataRole.UserRole, pkg)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable); it.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked); self.list.addItem(it)
        self.action = QComboBox(); self.action.addItems(actions); lay.addWidget(self.action)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); lay.addWidget(bb)
    def result_items(self):
        return [self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count()) if self.list.item(i).checkState() == Qt.CheckState.Checked], self.action.currentIndex()


class Window(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle(APP_NAME); self.resize(1180, 740)
        self.dev = None; self.brand = ''; self.rows = []; self.worker = None
        root = QWidget(); lay = QVBoxLayout(root); lay.setContentsMargins(22, 20, 22, 20); lay.setSpacing(13)
        head = QHBoxLayout(); labels = QVBoxLayout()
        title = QLabel("NORTH <span style='color:#60a5fa'>DEBLOATER</span>"); title.setObjectName('title')
        sub = QLabel('Android paket yöneticisi • ADB'); sub.setObjectName('muted'); labels.addWidget(title); labels.addWidget(sub); head.addLayout(labels); head.addStretch()
        self.status = QLabel('Cihaz kontrol ediliyor…'); self.status.setObjectName('status'); head.addWidget(self.status); lay.addLayout(head)

        controls = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText('Paket veya uygulama adına göre ara…'); self.search.textChanged.connect(self.render); controls.addWidget(self.search, 1)
        self.mode = QComboBox(); self.mode.addItems(MODES); self.mode.currentIndexChanged.connect(lambda _: self.load()); controls.addWidget(self.mode)
        self.scan = QPushButton('Tara / Yenile'); self.scan.clicked.connect(self.load); controls.addWidget(self.scan); lay.addLayout(controls)

        self.table = QTableWidget(0, 6); self.table.setHorizontalHeaderLabels(['Uygulama', 'Paket adı', 'Durum', 'Risk', 'Boyut', 'Açıklama'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.table.verticalHeader().setVisible(False); self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True); self.table.cellDoubleClicked.connect(lambda *_: self.show_details())
        h = self.table.horizontalHeader(); R = QHeaderView.ResizeMode
        h.setSectionResizeMode(0, R.Interactive); h.setSectionResizeMode(1, R.Stretch); h.setSectionResizeMode(2, R.ResizeToContents); h.setSectionResizeMode(3, R.ResizeToContents); h.setSectionResizeMode(4, R.ResizeToContents); h.setSectionResizeMode(5, R.Stretch)
        self.table.setColumnWidth(0, 190); lay.addWidget(self.table, 1)

        foot = QHBoxLayout(); self.count = QLabel('Henüz taranmadı'); self.count.setObjectName('muted'); foot.addWidget(self.count); foot.addStretch()
        self.tools = QPushButton('Araçlar ▾'); menu = QMenu(self)
        for text, fn in (('Ayrıntılar / izinler (çift tık)', self.show_details), ('Marka profili uygula…', self.apply_profile), ('Yedek kaydet…', self.save_backup), ('Yedekten uygula / geri al…', self.load_backup),
                         ('Listeyi dışa aktar (CSV)', self.export_csv), ('Topluluk listesini güncelle (UAD-NG)', self.update_list)):
            menu.addAction(text, fn)
        self.tools.setMenu(menu); foot.addWidget(self.tools)
        self.undo = QPushButton('Geri al'); self.undo.setToolTip('Kaldırılmışı geri yükler, devre dışı olanı etkinleştirir'); self.undo.clicked.connect(self.undo_selected); foot.addWidget(self.undo)
        self.disable = QPushButton('Devre dışı bırak'); self.disable.setObjectName('primary'); self.disable.clicked.connect(lambda: self.act_selected('disable')); foot.addWidget(self.disable)
        self.remove = QPushButton('Kaldır'); self.remove.setObjectName('danger'); self.remove.clicked.connect(lambda: self.act_selected('remove')); foot.addWidget(self.remove); lay.addLayout(foot)
        self.progress = QProgressBar(); self.progress.setTextVisible(False); self.progress.setFixedHeight(5); lay.addWidget(self.progress)
        note = QLabel('Önce "Devre dışı bırak"ı dene: tamamen geri alınabilir ve daha az risklidir. Risk etiketleri garanti değildir.'); note.setObjectName('muted'); lay.addWidget(note)
        self.setCentralWidget(root)
        self.setStyleSheet('QMainWindow,QWidget,QDialog{background:#0b1120;color:#e5e7eb;font-size:13px} QLabel#title{font-size:25px;font-weight:800} QLabel#muted{color:#94a3b8} QLabel#status{background:#172033;border:1px solid #334155;border-radius:8px;padding:9px} QLineEdit,QComboBox,QPlainTextEdit,QListWidget{background:#111b2e;border:1px solid #334155;border-radius:8px;padding:8px;color:#fff} QComboBox QAbstractItemView{background:#111b2e;color:#fff;selection-background-color:#1d4ed8} QPushButton{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:10px 14px;color:#f8fafc} QPushButton:hover{background:#29364c} QPushButton:disabled{color:#64748b} QPushButton#primary{background:#1d4ed8;font-weight:700} QPushButton#danger{background:#7f1d1d;font-weight:700} QMenu{background:#111b2e;color:#fff;border:1px solid #334155} QMenu::item:selected{background:#1d4ed8} QTableWidget{background:#0f172a;alternate-background-color:#111c30;border:1px solid #253149;gridline-color:#253149;selection-background-color:#1d4ed8} QHeaderView::section{background:#172033;color:#cbd5e1;padding:10px;border:none} QProgressBar{background:#111827;border:none} QProgressBar::chunk{background:#60a5fa}')
        QTimer.singleShot(0, self.load)

    # ---- ortak ----
    def busy(self, b):
        self.progress.setRange(0, 0 if b else 1)
        for w in (self.scan, self.remove, self.disable, self.undo, self.tools, self.mode): w.setEnabled(not b)
        if not b: self.update_buttons()

    def update_buttons(self):
        removed_view = self.mode.currentIndex() == MODE_REMOVED
        self.remove.setEnabled(not removed_view); self.disable.setEnabled(not removed_view)

    def run(self, fn, cb):
        if self.worker and self.worker.isRunning(): return
        self.busy(True); self.worker = Worker(fn); self.worker.done.connect(lambda result, err: self.finished(result, err, cb)); self.worker.start()

    def finished(self, result, err, cb):
        self.busy(False)
        if err: self.status.setText('Hata'); QMessageBox.warning(self, 'İşlem başarısız', err)
        else: cb(result)

    def need_device(self):
        if not self.dev: QMessageBox.information(self, 'Cihaz yok', 'Önce telefonu bağlayıp tarama yap.'); return False
        return True

    # ---- tarama / görünüm ----
    def load(self):
        if not adb_path():
            a = QMessageBox.question(self, 'ADB bulunamadı', 'Android Platform-Tools (ADB) bu bilgisayarda yok.\nGoogle’ın resmi sunucusundan şimdi indirilsin mi? (~10 MB, internet gerekir)')
            if a != QMessageBox.StandardButton.Yes: self.status.setText('ADB yok'); return
            self.status.setText('ADB indiriliyor…'); self.run(download_adb, lambda _: self.load()); return
        self.status.setText('Taranıyor… (boyutlar için birkaç saniye sürebilir)'); mode = self.mode.currentIndex(); self.run(lambda: scan(mode), self.loaded)

    def loaded(self, r):
        self.dev, self.brand, self.rows = r['dev'], r['brand'], r['rows']
        self.status.setText('Bağlı: ' + (r['model'] + ' · ' if r['model'] else '') + self.dev); self.render()

    def render(self):
        mode = self.mode.currentIndex(); q = self.search.text().lower().strip()
        self.table.setSortingEnabled(False); self.table.setRowCount(0); shown = 0
        for p, state, size in self.rows:
            name, lab, col, desc, _ = info(p, mode)
            if q and q not in p.lower() and q not in name.lower(): continue
            row = self.table.rowCount(); self.table.insertRow(row); shown += 1
            cells = [QTableWidgetItem(name or '—'), QTableWidgetItem(p), QTableWidgetItem(state), QTableWidgetItem(lab), SizeItem(size), QTableWidgetItem(desc)]
            cells[3].setForeground(QColor(col)); cells[2].setForeground(QColor({ST_ACTIVE: GREEN, ST_DISABLED: YELLOW, ST_REMOVED: RED}[state])); cells[5].setToolTip(desc)
            for c, it in enumerate(cells): self.table.setItem(row, c, it)
        self.table.setSortingEnabled(True); self.count.setText(f'{shown} / {len(self.rows)} paket gösteriliyor'); self.update_buttons()

    def selected(self):
        return [self.table.item(i, 1).text() for i in sorted({x.row() for x in self.table.selectionModel().selectedRows()})]

    def state_of(self, p): return next((s for q, s, _ in self.rows if q == p), ST_ACTIVE)

    # ---- işlemler ----
    def batch(self, op, pkgs):
        """op: remove | disable | restore | enable  → [(pkg, mesaj, ok)]"""
        dev = self.dev
        cmds = {'remove': (['shell', 'pm', 'uninstall', '--user', '0'], 'success', 'KALDIR'),
                'disable': (['shell', 'pm', 'disable-user', '--user', '0'], 'disabled', 'DEVRE_DISI'),
                'restore': (['shell', 'cmd', 'package', 'install-existing', '--user', '0'], 'installed', 'GERI_YUKLE'),
                'enable': (['shell', 'pm', 'enable', '--user', '0'], 'enabled', 'ETKINLESTIR')}
        args, needle, tag = cmds[op]
        def work():
            res = []
            for p in pkgs:
                try: out = adb(['-s', dev, *args, p]); ok = needle in out.lower(); m = out or 'Tamamlandı'
                except Exception as e: ok, m = False, str(e)
                log_action(tag, dev, p, ok, m); res.append((p, m, ok))
            return res
        return work

    def confirm(self, title, text, pkgs):
        crit = [p for p in pkgs if info(p, MODE_ALL)[4] == 'critical']
        if crit:
            text += f'\n\n⚠ {len(crit)} paket KRİTİK olarak işaretli (ör. {crit[0]}). Telefon açılmayabilir veya temel işlevler bozulabilir.'
        return QMessageBox.warning(self, title, text + '\n\nDevam edilsin mi?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes

    def act_selected(self, op, pkgs=None):
        pkgs = pkgs if pkgs is not None else self.selected()
        if not pkgs: QMessageBox.information(self, 'Seçim gerekli', 'Önce listeden paket seç.'); return
        if not self.need_device(): return
        if op == 'remove': ok = self.confirm('Kaldırmayı onayla', f'{len(pkgs)} paket mevcut Android kullanıcısından kaldırılacak. "Kaldırılmış paketler" görünümünden geri yüklenebilir.', pkgs)
        else: ok = self.confirm('Devre dışı bırakmayı onayla', f'{len(pkgs)} paket devre dışı bırakılacak (silinmez, "Geri al" ile açılır). Bazı sistem paketleri bunu reddedebilir.', pkgs)
        if ok: self.run(self.batch(op, pkgs), self.report)

    def undo_selected(self):
        pkgs = self.selected()
        if not pkgs: QMessageBox.information(self, 'Seçim gerekli', 'Geri almak için paket seç.'); return
        if not self.need_device(): return
        states = {p: self.state_of(p) for p in pkgs}
        todo = [p for p, s in states.items() if s != ST_ACTIVE]
        if not todo: QMessageBox.information(self, 'Gerek yok', 'Seçilen paketler zaten aktif.'); return
        if QMessageBox.question(self, 'Geri al', f'{len(todo)} paket geri alınacak (kaldırılmışlar geri yüklenir, devre dışılar etkinleştirilir). Devam?') != QMessageBox.StandardButton.Yes: return
        dev = self.dev; w1 = self.batch('restore', [p for p in todo if states[p] == ST_REMOVED]); w2 = self.batch('enable', [p for p in todo if states[p] == ST_DISABLED])
        self.run(lambda: w1() + w2(), self.report)

    def report(self, results):
        ok = sum(x[2] for x in results); detail = '\n'.join(('OK' if good else 'HATA') + ' — ' + p + ': ' + m for p, m, good in results)
        QMessageBox.information(self, 'Sonuç', f'{ok}/{len(results)} başarılı.\n\n{detail}\n\nİşlem günlüğü: {os.path.join(data_dir(), "islem_gunlugu.txt")}'); self.load()

    # ---- ayrıntılar / izinler ----
    def show_details(self):
        ps = self.selected()
        if len(ps) != 1: QMessageBox.information(self, 'Tek paket seç', 'Ayrıntı için listeden tek paket seç.'); return
        if not self.need_device(): return
        p, dev = ps[0], self.dev; name, lab, _, desc, _ = info(p, self.mode.currentIndex())
        size = next((s for q, _, s in self.rows if q == p), None)
        def done(d):
            lines = [f'{name or p}  [{lab}]', p, '', desc, '', f'Sürüm: {d["version"] or "?"}', f'İlk kurulum: {d["installed"] or "?"}', f'Son güncelleme: {d["updated"] or "?"}', f'Kuran: {d["installer"] or "?"}', f'APK yolu: {d["path"] or "?"}', f'Boyut (uygulama+veri): {human(size) or "bilinmiyor"}', '']
            perms = d['granted'] or {}; req = d['requested']
            dang = sorted(k for k in set(perms) | set(req) if short_perm(k) in DANGEROUS)
            lines.append(f'İstenen izin: {len(set(req) | set(perms))}  ·  verilmiş: {sum(perms.values())}')
            lines.append('Hassas izinler:' + ('' if dang else ' yok'))
            for k in dang: lines.append(f'  {"✔ verildi " if perms.get(k) else "✘ verilmedi"}  {short_perm(k)}')
            others = sorted(k for k in set(req) | set(perms) if k not in dang)
            if others: lines += ['', 'Diğer izinler:'] + [f'  {"✔" if perms.get(k) else "·"} {short_perm(k)}' for k in others]
            dlg = QDialog(self); dlg.setWindowTitle('Paket ayrıntıları'); dlg.resize(640, 620); l = QVBoxLayout(dlg)
            t = QPlainTextEdit('\n'.join(lines)); t.setReadOnly(True); l.addWidget(t); bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close); bb.rejected.connect(dlg.reject); l.addWidget(bb); dlg.exec()
        self.run(lambda: package_details(dev, p), done)

    # ---- marka profilleri ----
    def apply_profile(self):
        if not self.need_device(): return
        if not PROFILES: QMessageBox.information(self, 'Profil yok', 'packages_db.json bulunamadı.'); return
        names = list(PROFILES); b = (self.brand or '').lower()
        guess = next((i for i, n in enumerate(names) if PROFILES[n].get('brand') and PROFILES[n]['brand'] in b), 0)
        dlg = QDialog(self); dlg.setWindowTitle('Marka profili'); l = QVBoxLayout(dlg); l.addWidget(QLabel('Profil seç (telefon markasına göre öneri yapıldı):'))
        cb = QComboBox(); cb.addItems(names); cb.setCurrentIndex(guess); l.addWidget(cb)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel); bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); l.addWidget(bb)
        if not dlg.exec(): return
        prof = PROFILES[cb.currentText()]; dev = self.dev
        def preview(installed):
            items = [(p, f'{OWN[p]["name"]} — {OWN[p]["desc"]}', True) for p in prof['packages'] if p in installed and p in OWN]
            if not items: QMessageBox.information(self, 'Profil', 'Bu profildeki paketlerin hiçbiri bu telefonda aktif görünmüyor.'); return
            d = ChecklistDialog(self, cb.currentText(), f'{len(items)} paket bu telefonda bulundu. İstemediklerinin işaretini kaldır.\nÖneri: önce "Devre dışı bırak".', items, ['Devre dışı bırak (önerilen, geri alınabilir)', 'Kaldır'])
            if d.exec():
                chosen, idx = d.result_items()
                if chosen: self.act_selected('disable' if idx == 0 else 'remove', chosen)
        self.run(lambda: pkg_set(dev) - pkg_set(dev, '-d'), preview)

    # ---- yedek ----
    def save_backup(self):
        if not self.need_device(): return
        path, _ = QFileDialog.getSaveFileName(self, 'Yedeği kaydet', f'north-yedek-{datetime.now():%Y%m%d}.json', 'JSON (*.json)')
        if not path: return
        dev = self.dev
        def work():
            installed = pkg_set(dev); data = {'app': 'NorthDebloater', 'version': 1, 'created': datetime.now().isoformat(timespec='seconds'), 'model': getprop(dev, 'ro.product.model'),
                'brand': getprop(dev, 'ro.product.manufacturer'), 'android': getprop(dev, 'ro.build.version.release'),
                'removed': sorted(pkg_set(dev, '-u') - installed), 'disabled': sorted(pkg_set(dev, '-d') & installed)}
            with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=1)
            return data
        self.run(work, lambda d: QMessageBox.information(self, 'Yedek kaydedildi', f'{len(d["removed"])} kaldırılmış, {len(d["disabled"])} devre dışı paket kaydedildi.\n{path}'))

    def load_backup(self):
        if not self.need_device(): return
        path, _ = QFileDialog.getOpenFileName(self, 'Yedek dosyası seç', '', 'JSON (*.json)')
        if not path: return
        data = load_json(path)
        if data.get('app') != 'NorthDebloater': QMessageBox.warning(self, 'Geçersiz dosya', 'Bu bir North Debloater yedeği değil.'); return
        dev = self.dev
        def preview(state):
            installed, disabled, uninstalled = state
            items = []
            for p in data.get('removed', []):
                if p in installed or p in uninstalled: items.append((p, f'KALDIRILMIŞTI — {info(p, MODE_ALL)[0] or p}', True))
            for p in data.get('disabled', []):
                if p in installed: items.append((p, f'DEVRE DIŞIYDI — {info(p, MODE_ALL)[0] or p}', True))
            if not items: QMessageBox.information(self, 'Yedek', 'Yedekteki paketler bu telefonda bulunamadı.'); return
            d = ChecklistDialog(self, 'Yedekten uygula', f'Yedek: {data.get("model","?")} ({data.get("created","?")}). Bu telefonda karşılığı bulunan {len(items)} paket:', items,
                                ['Yedekteki durumu bu telefona uygula (kaldır / devre dışı bırak)', 'Yedekteki paketleri geri yükle / etkinleştir (geri al)'])
            if not d.exec(): return
            chosen, idx = d.result_items()
            if not chosen: return
            rem = [p for p in chosen if p in set(data.get('removed', []))]; dis = [p for p in chosen if p in set(data.get('disabled', [])) and p not in rem]
            if idx == 0:
                if not self.confirm('Yedeği uygula', f'{len(rem)} paket kaldırılacak, {len(dis)} paket devre dışı bırakılacak.', chosen): return
                w1 = self.batch('remove', [p for p in rem if p in installed]); w2 = self.batch('disable', [p for p in dis if p in installed and p not in disabled])
            else:
                w1 = self.batch('restore', [p for p in rem if p in uninstalled]); w2 = self.batch('enable', [p for p in chosen if p in disabled])
            self.run(lambda: w1() + w2(), self.report)
        self.run(lambda: (pkg_set(dev), pkg_set(dev, '-d'), pkg_set(dev, '-u') - pkg_set(dev)), preview)

    # ---- diğer ----
    def update_list(self):
        self.run(update_community, lambda n: (QMessageBox.information(self, 'Güncellendi', f'Topluluk listesi indirildi: {n} paket.\nKaynak: Universal Android Debloater Next Generation (GPL-3.0).'), self.render()))

    def export_csv(self):
        if not self.rows: QMessageBox.information(self, 'Liste boş', 'Önce tarama yap.'); return
        path, _ = QFileDialog.getSaveFileName(self, 'Listeyi kaydet', 'paketler.csv', 'CSV (*.csv)')
        if not path: return
        mode = self.mode.currentIndex()
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f); w.writerow(['uygulama', 'paket', 'durum', 'risk', 'boyut_bayt', 'aciklama'])
            for p, st, sz in self.rows: n, lab, _, d, _ = info(p, mode); w.writerow([n, p, st, lab, sz if sz is not None else '', d])
        QMessageBox.information(self, 'Kaydedildi', path)


if __name__ == '__main__':
    app = QApplication(sys.argv); app.aboutToQuit.connect(stop_adb); w = Window(); w.show(); sys.exit(app.exec())
