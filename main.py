import os, sys, re, csv, json, time, shutil, subprocess, zipfile, urllib.request
from datetime import datetime
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView, QComboBox, QProgressBar, QAbstractItemView,
    QFileDialog, QDialog, QListWidget, QListWidgetItem, QDialogButtonBox, QPlainTextEdit, QMenu)

APP_NAME = 'North Debloater'
IS_WIN = os.name == 'nt'
ADB_NAME = 'adb.exe' if IS_WIN else 'adb'
NOWIN = subprocess.CREATE_NO_WINDOW if IS_WIN else 0
PT_URL = 'https://dl.google.com/android/repository/platform-tools-latest-%s.zip' % ('windows' if IS_WIN else 'linux')
UAD_URL = 'https://raw.githubusercontent.com/Universal-Debloater-Alliance/universal-android-debloater-next-generation/main/resources/assets/uad_lists.json'
KEEP_AUTO_BACKUPS = 30

CRITICAL = ('systemui','settings','telephony','phone','permissioncontroller','packageinstaller','providers','inputmethod','launcher','keychain','keystore','framework','connectivity','emergency','storage','media','android')
CAUTION = ('samsung','knox','oneui','google','gms','carrier','wearable','health','bixby','dex','secure','wallet','smartthings')
GREEN, YELLOW, RED, GRAY = '#4ade80', '#fbbf24', '#f87171', '#cbd5e1'
RISK_COLOR = {'safe': GREEN, 'caution': YELLOW, 'critical': RED, 'unknown': GRAY}
DANGEROUS = {'CAMERA','RECORD_AUDIO','ACCESS_FINE_LOCATION','ACCESS_COARSE_LOCATION','ACCESS_BACKGROUND_LOCATION','READ_CONTACTS','WRITE_CONTACTS','READ_SMS','SEND_SMS','RECEIVE_SMS','READ_CALL_LOG','WRITE_CALL_LOG','READ_PHONE_STATE','CALL_PHONE','READ_CALENDAR','WRITE_CALENDAR','BODY_SENSORS','READ_EXTERNAL_STORAGE','WRITE_EXTERNAL_STORAGE','MANAGE_EXTERNAL_STORAGE','SYSTEM_ALERT_WINDOW','BIND_ACCESSIBILITY_SERVICE','READ_MEDIA_IMAGES','READ_MEDIA_VIDEO','READ_MEDIA_AUDIO'}
# marka filtresi: paket adında geçen ipuçları (veritabanında markası yazmayan paketler için)
BRAND_HINTS = {'samsung': ('samsung', 'knox', 'com.sec.'), 'xiaomi': ('xiaomi', 'miui'),
               'oppo': ('oppo', 'heytap', 'coloros', 'realme', 'oneplus', 'nearme', 'opos'),
               'google': ('com.google.', 'com.android.vending'),
               'thirdparty': ('facebook', 'netflix', 'amazon', 'spotify', 'linkedin', 'microsoft', 'touchtype')}

MODE_USER, MODE_ALL, MODE_REMOVED = 0, 1, 2
ST_ACTIVE, ST_DISABLED, ST_REMOVED = 'active', 'disabled', 'removed'   # dil bağımsız kodlar; görünen metin t('st_...')

# ---------- diller (TR / EN) ----------
STR = {
 'app_sub': ('Android paket yöneticisi • ADB', 'Android package manager • ADB'),
 'checking': ('Cihaz kontrol ediliyor…', 'Checking device…'),
 'search_ph': ('Paket veya uygulama adına göre ara…', 'Search by package or app name…'),
 'mode0': ('Kullanıcı uygulamaları', 'User apps'),
 'mode1': ('Tüm paketler (sistem dahil)', 'All packages (including system)'),
 'mode2': ('Kaldırılmış paketler (geri yüklenebilir)', 'Removed packages (restorable)'),
 'scan_btn': ('Tara / Yenile', 'Scan / Refresh'),
 'cols': (['Uygulama', 'Paket adı', 'Durum', 'Risk', 'Boyut', 'Açıklama'], ['App', 'Package', 'Status', 'Risk', 'Size', 'Description']),
 'st_active': ('Aktif', 'Active'), 'st_disabled': ('Devre dışı', 'Disabled'), 'st_removed': ('Kaldırılmış', 'Removed'),
 'risk_safe': ('DÜŞÜK', 'LOW'), 'risk_caution': ('DİKKAT', 'CAUTION'), 'risk_critical': ('KRİTİK', 'CRITICAL'), 'risk_unknown': ('BİLİNMİYOR', 'UNKNOWN'),
 'f_state_all': ('Tüm durumlar', 'All states'), 'f_risk_all': ('Tüm riskler', 'All risks'),
 'f_list_all': ('Tüm paketler', 'All packages'), 'f_known': ('Sadece bilinenler (veritabanı)', 'Known only (database)'), 'f_unknown': ('Sadece bilinmeyenler', 'Unknown only'),
 'b_samsung': ('Samsung', 'Samsung'), 'b_xiaomi': ('Xiaomi', 'Xiaomi'), 'b_oppo': ('Oppo / Realme / OnePlus', 'Oppo / Realme / OnePlus'),
 'b_google': ('Google', 'Google'), 'b_thirdparty': ('Üçüncü taraf ön yüklüler', 'Third-party preinstalled'),
 'sel_all': ('Görünenlerin hepsini seç', 'Select all shown'), 'sel_none': ('Seçimi temizle', 'Clear selection'),
 'sel_count': ('{0} seçili', '{0} selected'),
 'not_scanned': ('Henüz taranmadı', 'Not scanned yet'),
 'count': ('{0} / {1} paket gösteriliyor', 'Showing {0} / {1} packages'),
 'tools': ('Araçlar ▾', 'Tools ▾'),
 'm_details': ('Ayrıntılar / izinler (çift tık)', 'Details / permissions (double-click)'),
 'm_profile': ('Marka profili uygula…', 'Apply brand profile…'),
 'm_save': ('Yedek kaydet…', 'Save backup…'),
 'm_load': ('Yedekten uygula / geri al…', 'Apply / undo from backup…'),
 'm_last_auto': ('Son otomatik yedekten geri al…', 'Undo from latest automatic backup…'),
 'm_open_auto': ('Otomatik yedek klasörünü aç', 'Open automatic backup folder'),
 'm_wifi': ('Kablosuz ADB (Wi-Fi)…', 'Wireless ADB (Wi-Fi)…'),
 'm_csv': ('Listeyi dışa aktar (CSV)', 'Export list (CSV)'),
 'm_update': ('Topluluk listesini güncelle (UAD-NG)', 'Update community list (UAD-NG)'),
 'm_lang': ('Dil / Language', 'Dil / Language'),
 'undo': ('Geri al', 'Undo'), 'undo_tip': ('Kaldırılmışı geri yükler, devre dışı olanı etkinleştirir', 'Restores removed apps and re-enables disabled ones'),
 'disable': ('Devre dışı bırak', 'Disable'), 'remove': ('Kaldır', 'Remove'),
 'note': ('Önce "Devre dışı bırak"ı dene: tamamen geri alınabilir ve daha az risklidir. Kaldır/Devre dışı işlemlerinden önce otomatik yedek alınır. Risk etiketleri garanti değildir.',
          'Try "Disable" first: it is fully reversible and less risky. An automatic backup is taken before every Remove/Disable. Risk labels are not guarantees.'),
 'dev_tip': ('Bağlı cihaz (birden fazla varsa buradan seç)', 'Connected device (choose here if there are several)'),
 'connected': ('Bağlı: ', 'Connected: '),
 'scanning': ('Taranıyor… (boyutlar için birkaç saniye sürebilir)', 'Scanning… (sizes may take a few seconds)'),
 'error': ('Hata', 'Error'), 'failed_title': ('İşlem başarısız', 'Operation failed'),
 'no_device_t': ('Cihaz yok', 'No device'), 'no_device': ('Önce telefonu bağlayıp tarama yap.', 'Connect the phone and scan first.'),
 'adb_missing_t': ('ADB bulunamadı', 'ADB not found'),
 'adb_missing': ('Android Platform-Tools (ADB) bu bilgisayarda yok.\nGoogle’ın resmi sunucusundan şimdi indirilsin mi? (~10 MB, internet gerekir)',
                 'Android Platform-Tools (ADB) is not on this computer.\nDownload it now from Google’s official server? (~10 MB, internet required)'),
 'adb_none': ('ADB yok', 'No ADB'), 'adb_downloading': ('ADB indiriliyor…', 'Downloading ADB…'),
 'adb_not_in_pkg': ('İndirilen pakette adb bulunamadı.', 'adb was not found in the downloaded package.'),
 'adb_not_found': ('ADB bulunamadı.', 'ADB not found.'), 'adb_error': ('ADB hatası', 'ADB error'),
 'err_unauth': ('Telefon ekranındaki USB hata ayıklama iznini onayla.', 'Accept the USB debugging prompt on the phone screen.'),
 'err_offline': ('Cihaz çevrimdışı görünüyor. Kabloyu çıkarıp tak, gerekirse USB hata ayıklamayı kapat/aç.', 'The device appears offline. Re-plug the cable; if needed toggle USB debugging off/on.'),
 'err_nodev': ('Telefon bulunamadı. USB hata ayıklamayı aç, veri kablosu kullan ve izin penceresini onayla. Kablosuz için Araçlar > Kablosuz ADB.',
               'No phone found. Enable USB debugging, use a data cable and accept the prompt. For wireless use Tools > Wireless ADB.'),
 'list_bad': ('Liste beklenen biçimde değil.', 'The list is not in the expected format.'),
 'select_first_t': ('Seçim gerekli', 'Selection required'), 'select_first': ('Önce listeden paket seç.', 'Select packages from the list first.'),
 'select_one_t': ('Tek paket seç', 'Select one package'), 'select_one': ('Ayrıntı için listeden tek paket seç.', 'Select a single package for details.'),
 'select_undo': ('Geri almak için paket seç.', 'Select packages to undo.'),
 'confirm_remove_t': ('Kaldırmayı onayla', 'Confirm removal'),
 'confirm_remove': ('{0} paket mevcut Android kullanıcısından kaldırılacak. "Kaldırılmış paketler" görünümünden geri yüklenebilir.\nİşlemden önce otomatik yedek alınır.',
                    '{0} package(s) will be removed for the current Android user. They can be restored from the "Removed packages" view.\nAn automatic backup is taken first.'),
 'confirm_disable_t': ('Devre dışı bırakmayı onayla', 'Confirm disable'),
 'confirm_disable': ('{0} paket devre dışı bırakılacak (silinmez, "Geri al" ile açılır). Bazı sistem paketleri bunu reddedebilir.\nİşlemden önce otomatik yedek alınır.',
                     '{0} package(s) will be disabled (not deleted; "Undo" re-enables them). Some system packages may refuse this.\nAn automatic backup is taken first.'),
 'crit_warn': ('⚠ {0} paket KRİTİK olarak işaretli (ör. {1}). Telefon açılmayabilir veya temel işlevler bozulabilir.',
               '⚠ {0} package(s) are marked CRITICAL (e.g. {1}). The phone may not boot or basic functions may break.'),
 'continue_q': ('Devam edilsin mi?', 'Continue?'),
 'undo_t': ('Geri al', 'Undo'), 'undo_already_t': ('Gerek yok', 'Nothing to do'), 'undo_already': ('Seçilen paketler zaten aktif.', 'The selected packages are already active.'),
 'undo_confirm': ('{0} paket geri alınacak (kaldırılmışlar geri yüklenir, devre dışılar etkinleştirilir). Devam?', '{0} package(s) will be undone (removed ones restored, disabled ones re-enabled). Continue?'),
 'result_t': ('Sonuç', 'Result'),
 'result': ('{0}/{1} başarılı.', '{0}/{1} succeeded.'),
 'result_backup': ('Otomatik yedek: {0}', 'Automatic backup: {0}'),
 'result_log': ('İşlem günlüğü: {0}', 'Operation log: {0}'),
 'progress': ('İşleniyor {0}/{1}: {2}', 'Processing {0}/{1}: {2}'),
 'done_msg': ('Tamamlandı', 'Done'),
 'backup_fail': ('Otomatik yedek alınamadı, işlem iptal edildi: {0}', 'Automatic backup failed, operation cancelled: {0}'),
 'nothing': ('Yapılacak bir işlem yok.', 'Nothing to do.'),
 'det_title': ('Paket ayrıntıları', 'Package details'),
 'det_version': ('Sürüm', 'Version'), 'det_first': ('İlk kurulum', 'First install'), 'det_updated': ('Son güncelleme', 'Last update'),
 'det_installer': ('Kuran', 'Installer'), 'det_path': ('APK yolu', 'APK path'), 'det_size': ('Boyut (uygulama+veri)', 'Size (app+data)'), 'det_unknown': ('bilinmiyor', 'unknown'),
 'det_perms': ('İstenen izin: {0}  ·  verilmiş: {1}', 'Requested permissions: {0}  ·  granted: {1}'),
 'det_sensitive': ('Hassas izinler:', 'Sensitive permissions:'), 'det_none': (' yok', ' none'),
 'det_granted': ('✔ verildi ', '✔ granted  '), 'det_denied': ('✘ verilmedi', '✘ denied   '), 'det_others': ('Diğer izinler:', 'Other permissions:'),
 'prof_none_t': ('Profil yok', 'No profile'), 'prof_none': ('packages_db.json bulunamadı.', 'packages_db.json not found.'),
 'prof_t': ('Marka profili', 'Brand profile'), 'prof_pick': ('Profil seç (telefon markasına göre öneri yapıldı):', 'Choose a profile (suggested from the phone brand):'),
 'prof_empty': ('Bu profildeki paketlerin hiçbiri bu telefonda aktif görünmüyor.', 'None of this profile’s packages appear active on this phone.'),
 'prof_intro': ('{0} paket bu telefonda bulundu. İstemediklerinin işaretini kaldır.\nÖneri: önce "Devre dışı bırak".', '{0} package(s) found on this phone. Uncheck the ones you want to keep.\nTip: try "Disable" first.'),
 'prof_a0': ('Devre dışı bırak (önerilen, geri alınabilir)', 'Disable (recommended, reversible)'), 'prof_a1': ('Kaldır', 'Remove'),
 'bk_save_t': ('Yedeği kaydet', 'Save backup'), 'bk_saved_t': ('Yedek kaydedildi', 'Backup saved'),
 'bk_saved': ('{0} kaldırılmış, {1} devre dışı paket kaydedildi.\n{2}', '{0} removed and {1} disabled package(s) saved.\n{2}'),
 'bk_open_t': ('Yedek dosyası seç', 'Select backup file'),
 'bk_bad_t': ('Geçersiz dosya', 'Invalid file'), 'bk_bad': ('Bu bir North Debloater yedeği değil.', 'This is not a North Debloater backup.'),
 'bk_t': ('Yedek', 'Backup'), 'bk_none': ('Yedekteki paketler bu telefonda bulunamadı.', 'The packages in the backup were not found on this phone.'),
 'bk_dlg': ('Yedekten uygula', 'Apply from backup'),
 'bk_intro': ('Yedek: {0} ({1}). Bu telefonda karşılığı bulunan {2} paket:', 'Backup: {0} ({1}). {2} package(s) found on this phone:'),
 'bk_intro_auto': ('Otomatik yedek: {0} ({1}). Bu işlemde değişen paketler işaretli geliyor; geri almak için "geri yükle / etkinleştir" seçili:',
                   'Automatic backup: {0} ({1}). Packages changed by that operation are pre-checked; "restore / re-enable" is preselected to undo it:'),
 'bk_was_removed': ('KALDIRILMIŞTI', 'WAS REMOVED'), 'bk_was_disabled': ('DEVRE DIŞIYDI', 'WAS DISABLED'),
 'bk_a0': ('Yedekteki durumu bu telefona uygula (kaldır / devre dışı bırak)', 'Apply the backup state to this phone (remove / disable)'),
 'bk_a1': ('Yedekteki paketleri geri yükle / etkinleştir (geri al)', 'Restore / re-enable the packages in the backup (undo)'),
 'bk_apply_t': ('Yedeği uygula', 'Apply backup'), 'bk_apply': ('{0} paket kaldırılacak, {1} paket devre dışı bırakılacak.', '{0} package(s) will be removed, {1} will be disabled.'),
 'bk_no_auto': ('Henüz otomatik yedek yok. Kaldır veya Devre dışı bırak işleminden önce otomatik oluşturulur.', 'No automatic backup yet. One is created automatically before every Remove or Disable.'),
 'upd_t': ('Güncellendi', 'Updated'),
 'upd': ('Topluluk listesi indirildi: {0} paket.\nKaynak: Universal Android Debloater Next Generation (GPL-3.0).', 'Community list downloaded: {0} packages.\nSource: Universal Android Debloater Next Generation (GPL-3.0).'),
 'csv_empty_t': ('Liste boş', 'List is empty'), 'csv_empty': ('Önce tarama yap.', 'Scan first.'),
 'csv_t': ('Listeyi kaydet', 'Save list'), 'csv_saved_t': ('Kaydedildi', 'Saved'),
 'csv_cols': (['uygulama', 'paket', 'durum', 'risk', 'boyut_bayt', 'aciklama'], ['app', 'package', 'status', 'risk', 'size_bytes', 'description']),
 'lang_busy': ('Dili değiştirmek için çalışan işlemin bitmesini bekle.', 'Wait for the running operation to finish before changing the language.'),
 'community_suffix': ('(topluluk listesi)', '(community list)'),
 'heur_critical': ('Sistem işlevleri bozulabilir.', 'System functions may break.'),
 'heur_caution': ('Üretici/servis bağımlılığı olabilir.', 'May be a vendor/service dependency.'),
 'heur_unknown': ('Sistem paketi olabilir; araştırmadan kaldırma.', 'Could be a system package; research before removing.'),
 'heur_user': ('Üçüncü taraf uygulaması; yine de kontrol et.', 'Third-party app; still double-check.'),
 # kablosuz ADB
 'wifi_title': ('Kablosuz ADB (Wi-Fi)', 'Wireless ADB (Wi-Fi)'),
 'wifi_intro': ('Telefon ve bilgisayar aynı Wi-Fi ağında olmalı.\n\nAndroid 11+: Ayarlar > Geliştirici seçenekleri > Kablosuz hata ayıklama > "Eşleştirme koduyla eşleştir". Görünen IP:port ve kodu aşağıya yaz, Eşleştir\'e bas; sonra ana ekrandaki (farklı) IP:port ile Bağlan.\n\nAndroid 10 ve altı: Telefonu USB ile bağla, "USB\'den Wi-Fi\'ye geç" düğmesine bas.',
                'Phone and computer must be on the same Wi-Fi network.\n\nAndroid 11+: Settings > Developer options > Wireless debugging > "Pair device with pairing code". Enter the shown IP:port and code below and press Pair; then Connect using the (different) IP:port from the main screen.\n\nAndroid 10 and below: connect the phone by USB and press "Switch USB to Wi-Fi".'),
 'wifi_pair_h': ('1) Eşleştir (yalnızca ilk seferde, Android 11+)', '1) Pair (first time only, Android 11+)'),
 'wifi_pair_addr': ('Eşleştirme IP:port (ör. 192.168.1.20:37215)', 'Pairing IP:port (e.g. 192.168.1.20:37215)'),
 'wifi_code': ('6 haneli kod', '6-digit code'), 'wifi_pair_btn': ('Eşleştir', 'Pair'),
 'wifi_conn_h': ('2) Bağlan', '2) Connect'), 'wifi_conn_addr': ('Bağlantı IP:port (ör. 192.168.1.20:5555)', 'Connection IP:port (e.g. 192.168.1.20:5555)'),
 'wifi_conn_btn': ('Bağlan', 'Connect'), 'wifi_disc_btn': ('Bağlantıyı kes', 'Disconnect'),
 'wifi_usb_btn': ('USB\'den Wi-Fi\'ye geç', 'Switch USB to Wi-Fi'),
 'wifi_need_pair': ('Eşleştirme adresi ve kodu gerekli.', 'Pairing address and code are required.'),
 'wifi_need_conn': ('Bağlantı adresi gerekli.', 'Connection address is required.'),
 'wifi_fail': ('İşlem başarısız.', 'Operation failed.'),
 'wifi_paired_next': ('Şimdi 2) Bağlan bölümünü kullan.', 'Now use step 2) Connect.'),
 'wifi_no_usb': ('USB ile bağlı, yetkili bir cihaz bulunamadı.', 'No authorized USB-connected device found.'),
 'wifi_no_ip': ('Telefonun Wi-Fi IP adresi okunamadı. Telefon Wi-Fi\'ye bağlı mı?', 'Could not read the phone’s Wi-Fi IP. Is it connected to Wi-Fi?'),
 'wifi_disc_ok': ('Bağlantı kesildi.', 'Disconnected.'),
}
LANG = 'tr'

def t(key, *a):
    v = STR[key][0 if LANG == 'tr' else 1]
    return v.format(*a) if a else v

def loc(e, key):
    """Kayıttan seçili dile uygun alanı al (name/desc; İngilizce yoksa Türkçeye döner)."""
    return (e.get(key + '_en') if LANG == 'en' else None) or e.get(key, '')


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

SETTINGS_PATH = os.path.join(data_dir(), 'settings.json')
SETTINGS = load_json(SETTINGS_PATH)
if not isinstance(SETTINGS, dict): SETTINGS = {}
if SETTINGS.get('lang') in ('tr', 'en'): LANG = SETTINGS['lang']

def save_settings():
    try:
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as f: json.dump(SETTINGS, f, ensure_ascii=False, indent=1)
    except Exception: pass

BUNDLED = load_json(resource('packages_db.json') or '')
OWN = BUNDLED.get('packages', {}); PROFILES = BUNDLED.get('profiles', {})
COMMUNITY_PATH = os.path.join(data_dir(), 'uad_lists.json')
COMMUNITY = load_json(COMMUNITY_PATH)
COMMUNITY_MAP = {'Recommended': 'safe', 'Advanced': 'caution', 'Expert': 'caution', 'Unsafe': 'critical'}

def info(pkg, mode=MODE_USER):
    """(uygulama adı, risk etiketi, renk, açıklama, risk anahtarı)"""
    if pkg in OWN:
        e = OWN[pkg]; k = e['risk']; return loc(e, 'name'), t('risk_' + k), RISK_COLOR[k], loc(e, 'desc'), k
    if pkg in COMMUNITY:
        e = COMMUNITY[pkg]; k = COMMUNITY_MAP.get(e.get('removal'), 'caution')
        d = ' '.join(e.get('description', '').split())[:220]
        return '', t('risk_' + k), RISK_COLOR[k], d + ' ' + t('community_suffix'), k
    p = pkg.lower()
    if any(x in p for x in CRITICAL): return '', t('risk_critical'), RED, t('heur_critical'), 'critical'
    if any(x in p for x in CAUTION): return '', t('risk_caution'), YELLOW, t('heur_caution'), 'caution'
    if mode != MODE_USER: return '', t('risk_unknown'), GRAY, t('heur_unknown'), 'unknown'
    return '', t('risk_safe'), GREEN, t('heur_user'), 'safe'

def is_known(pkg): return pkg in OWN or pkg in COMMUNITY

def brand_of(pkg):
    if pkg in OWN and OWN[pkg].get('brand'): return OWN[pkg]['brand']
    p = pkg.lower()
    return next((k for k, hints in BRAND_HINTS.items() if any(h in p for h in hints)), '')

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
    if not os.path.isfile(exe): raise RuntimeError(t('adb_not_in_pkg'))
    return exe

def update_community():
    tmp = COMMUNITY_PATH + '.tmp'; download(UAD_URL, tmp)
    data = load_json(tmp)
    if not isinstance(data, dict) or len(data) < 100: raise RuntimeError(t('list_bad'))
    os.replace(tmp, COMMUNITY_PATH); COMMUNITY.clear(); COMMUNITY.update(data); return len(data)

def adb(args, timeout=30):
    exe = adb_path()
    if not exe: raise RuntimeError(t('adb_not_found'))
    p = subprocess.run([exe, *args], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout, creationflags=NOWIN)
    if p.returncode: raise RuntimeError((p.stderr or p.stdout or t('adb_error')).strip())
    return p.stdout.strip()

def stop_adb():
    """Kapanışta ADB sunucusunu durdur (yoksa adb.exe açık kalır, klasör silinemez). PATH'teki sistem adb'sine dokunma."""
    exe = adb_path()
    if not exe or exe == shutil.which('adb'): return
    try: subprocess.run([exe, 'kill-server'], capture_output=True, timeout=10, creationflags=NOWIN)
    except Exception: pass

def list_devices():
    """[(seri no, durum, model)] — durum: device | unauthorized | offline …"""
    res = []
    for line in adb(['devices', '-l']).splitlines():
        line = line.strip()
        if not line or line.startswith('*') or line.startswith('List of devices'): continue
        parts = line.split()
        if len(parts) < 2: continue
        m = re.search(r'model:(\S+)', line)
        res.append((parts[0], parts[1], m.group(1).replace('_', ' ') if m else ''))
    return res

def state_error(state):
    return t('err_unauth') if state == 'unauthorized' else t('err_offline')

def pick_device(devs, preferred=None):
    ready = [d[0] for d in devs if d[1] == 'device']
    for ser, st, _ in devs:
        if ser == preferred and st != 'device': raise RuntimeError(state_error(st))
    if preferred in ready: return preferred
    if ready: return ready[0]
    if any(d[1] == 'unauthorized' for d in devs): raise RuntimeError(t('err_unauth'))
    if any(d[1] == 'offline' for d in devs): raise RuntimeError(t('err_offline'))
    raise RuntimeError(t('err_nodev'))

def device_ip(dev):
    for cmd in (['ip', '-f', 'inet', 'addr', 'show', 'wlan0'], ['ip', 'route']):
        try: out = adb(['-s', dev, 'shell', *cmd])
        except Exception: continue
        m = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', out) or re.search(r'src (\d+\.\d+\.\d+\.\d+)', out)
        if m: return m.group(1)
    return ''

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

def scan(mode, preferred=None):
    devs = list_devices(); dev = pick_device(devs, preferred)
    model = getprop(dev, 'ro.product.model'); brand = getprop(dev, 'ro.product.manufacturer')
    installed = pkg_set(dev); disabled = pkg_set(dev, '-d') & installed; removed = set()
    if mode == MODE_REMOVED: removed = pkg_set(dev, '-u') - installed; pk = removed
    elif mode == MODE_USER: pk = pkg_set(dev, '-3')
    else: pk = installed
    sizes = disk_sizes(dev) if mode != MODE_REMOVED else {}
    rows = [(p, ST_REMOVED if p in removed else ST_DISABLED if p in disabled else ST_ACTIVE, sizes.get(p)) for p in sorted(pk)]
    return {'dev': dev, 'model': model, 'brand': brand, 'rows': rows, 'devices': devs}

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


# ---------- yedekler ----------
def snapshot(dev):
    installed = pkg_set(dev)
    return {'app': 'NorthDebloater', 'version': 1, 'created': datetime.now().isoformat(timespec='seconds'), 'serial': dev,
            'model': getprop(dev, 'ro.product.model'), 'brand': getprop(dev, 'ro.product.manufacturer'), 'android': getprop(dev, 'ro.build.version.release'),
            'removed': sorted(pkg_set(dev, '-u') - installed), 'disabled': sorted(pkg_set(dev, '-d') & installed)}

def auto_backup_dir():
    path = os.path.join(data_dir(), 'otomatik_yedekler'); os.makedirs(path, exist_ok=True); return path

def list_auto_backups():
    d = auto_backup_dir()
    return sorted(os.path.join(d, f) for f in os.listdir(d) if f.startswith('north-oto-') and f.endswith('.json'))

def write_auto_backup(dev, tasks):
    """İşlemden ÖNCE çağrılır. Dosya, işlemden SONRAki durumu (mevcut + planlanan) tutar; böylece
    'Yedekten uygula / geri al > geri yükle' bu işlemi geri alır. 'before' = işlem öncesi gerçek durum, 'changes' = bu işlemde değişecekler."""
    d = snapshot(dev)
    ch = {'remove': [p for o, p in tasks if o == 'remove'], 'disable': [p for o, p in tasks if o == 'disable']}
    rem = set(d['removed']) | set(ch['remove']); dis = (set(d['disabled']) | set(ch['disable'])) - rem
    d.update(auto=True, changes=ch, before={'removed': d['removed'], 'disabled': d['disabled']}, removed=sorted(rem), disabled=sorted(dis))
    now = datetime.now(); safe = re.sub(r'[^A-Za-z0-9._-]', '_', dev); n = 0
    while True:    # aynı milisaniyede ikinci yedek ilkinin üstüne yazılmasın
        path = os.path.join(auto_backup_dir(), f"north-oto-{now:%Y%m%d-%H%M%S}-{now.microsecond // 1000:03d}{'' if not n else '-' + str(n)}-{safe}.json")
        if not os.path.exists(path): break
        n += 1
    with open(path, 'w', encoding='utf-8') as f: json.dump(d, f, ensure_ascii=False, indent=1)
    for old in list_auto_backups()[:-KEEP_AUTO_BACKUPS]:
        try: os.remove(old)
        except Exception: pass
    return path


class SizeItem(QTableWidgetItem):
    def __init__(self, n): super().__init__(human(n)); self.n = n or -1
    def __lt__(self, o): return self.n < getattr(o, 'n', -1)


class Worker(QThread):
    done = Signal(object, str)
    progress = Signal(int, int, str)
    def __init__(self, fn, progress=False): super().__init__(); self.fn = fn; self.wants = progress
    def run(self):
        try: self.done.emit(self.fn(self.progress.emit) if self.wants else self.fn(), '')
        except Exception as e: self.done.emit(None, str(e))


class ChecklistDialog(QDialog):
    """Paket listesi (işaretli) + işlem seçimi."""
    def __init__(self, parent, title, intro, items, actions, default_action=0):
        super().__init__(parent); self.setWindowTitle(title); self.resize(620, 560)
        lay = QVBoxLayout(self); lab = QLabel(intro); lab.setWordWrap(True); lay.addWidget(lab)
        self.list = QListWidget(); lay.addWidget(self.list, 1)
        for pkg, label, checked in items:
            it = QListWidgetItem(label); it.setData(Qt.ItemDataRole.UserRole, pkg)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable); it.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked); self.list.addItem(it)
        self.action = QComboBox(); self.action.addItems(actions); self.action.setCurrentIndex(default_action); lay.addWidget(self.action)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); lay.addWidget(bb)
    def result_items(self):
        return [self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count()) if self.list.item(i).checkState() == Qt.CheckState.Checked], self.action.currentIndex()


class WifiDialog(QDialog):
    """Kablosuz ADB: eşleştir (Android 11+), bağlan, bağlantıyı kes, USB'den Wi-Fi'ye geç (Android 10 ve altı)."""
    def __init__(self, win):
        super().__init__(win); self.win = win; self.w = None; self.busy = False
        self.setWindowTitle(t('wifi_title')); self.resize(600, 600)
        lay = QVBoxLayout(self)
        intro = QLabel(t('wifi_intro')); intro.setWordWrap(True); intro.setObjectName('muted'); lay.addWidget(intro)

        lay.addWidget(QLabel('<b>' + t('wifi_pair_h') + '</b>'))
        r = QHBoxLayout(); self.pair_addr = QLineEdit(); self.pair_addr.setPlaceholderText(t('wifi_pair_addr'))
        self.pair_code = QLineEdit(); self.pair_code.setPlaceholderText(t('wifi_code')); self.pair_code.setMaxLength(10); self.pair_code.setFixedWidth(130)
        self.b_pair = QPushButton(t('wifi_pair_btn')); self.b_pair.clicked.connect(self.pair)
        r.addWidget(self.pair_addr, 1); r.addWidget(self.pair_code); r.addWidget(self.b_pair); lay.addLayout(r)

        lay.addWidget(QLabel('<b>' + t('wifi_conn_h') + '</b>'))
        r = QHBoxLayout(); self.conn_addr = QLineEdit(SETTINGS.get('wifi_last', '')); self.conn_addr.setPlaceholderText(t('wifi_conn_addr'))
        self.b_conn = QPushButton(t('wifi_conn_btn')); self.b_conn.setObjectName('primary'); self.b_conn.clicked.connect(self.connect_)
        self.b_disc = QPushButton(t('wifi_disc_btn')); self.b_disc.clicked.connect(self.disconnect_)
        r.addWidget(self.conn_addr, 1); r.addWidget(self.b_conn); r.addWidget(self.b_disc); lay.addLayout(r)

        self.b_usb = QPushButton(t('wifi_usb_btn')); self.b_usb.clicked.connect(self.usb_to_wifi); lay.addWidget(self.b_usb)
        self.out = QPlainTextEdit(); self.out.setReadOnly(True); lay.addWidget(self.out, 1)
        self.btns = [self.b_pair, self.b_conn, self.b_disc, self.b_usb]

    def log(self, s): self.out.appendPlainText(s)

    def go(self, fn, ok=None):
        if self.busy: return
        self.busy = True
        for b in self.btns: b.setEnabled(False)
        if self.w: self.w.wait()
        self.w = Worker(fn); self.w.done.connect(lambda res, err: self.finish(res, err, ok)); self.w.start()

    def finish(self, res, err, ok):
        self.busy = False
        for b in self.btns: b.setEnabled(True)
        if err: self.log('✘ ' + err); return
        if res: self.log('✔ ' + res)
        if ok: ok(res)

    def done(self, code):
        if self.busy: return          # çalışan işlem bitmeden kapatma
        if self.w: self.w.wait()
        super().done(code)

    @staticmethod
    def check_connect(out):
        low = out.lower()
        if 'connected to' not in low or 'cannot' in low or 'failed' in low: raise RuntimeError(out or t('wifi_fail'))

    def pair(self):
        a, c = self.pair_addr.text().strip(), self.pair_code.text().strip()
        if not a or not c: self.log(t('wifi_need_pair')); return
        def work():
            out = adb(['pair', a, c], timeout=40)
            if 'success' not in out.lower(): raise RuntimeError(out or t('wifi_fail'))
            return out
        self.go(work, lambda _: self.log(t('wifi_paired_next')))

    def connect_(self):
        a = self.conn_addr.text().strip()
        if not a: self.log(t('wifi_need_conn')); return
        def work():
            out = adb(['connect', a], timeout=30); self.check_connect(out)
            SETTINGS['wifi_last'] = a; save_settings(); return out
        self.go(work, lambda _: self.connected(a))

    def disconnect_(self):
        a = self.conn_addr.text().strip()
        def work():
            adb(['disconnect', a] if a else ['disconnect'], timeout=20); return t('wifi_disc_ok')
        self.go(work, lambda _: self.win.load())

    def usb_to_wifi(self):
        def work():
            usb = [d for d in list_devices() if d[1] == 'device' and ':' not in d[0] and not d[0].startswith('adb-')]
            if not usb: raise RuntimeError(t('wifi_no_usb'))
            ser = usb[0][0]; ip = device_ip(ser)
            if not ip: raise RuntimeError(t('wifi_no_ip'))
            adb(['-s', ser, 'tcpip', '5555'], timeout=20); time.sleep(2.5)
            addr = ip + ':5555'; out = adb(['connect', addr], timeout=30); self.check_connect(out)
            SETTINGS['wifi_last'] = addr; save_settings(); return addr
        def ok(addr): self.conn_addr.setText(addr); self.connected(addr)
        self.go(work, ok)

    def connected(self, addr):
        self.win.pref = addr; self.win.load(); self.accept()


class Window(QMainWindow):
    def __init__(self, pref=None, geometry=None):
        super().__init__(); self.setWindowTitle(APP_NAME); self.resize(1180, 760)
        self.dev = None; self.pref = pref; self.brand = ''; self.rows = []; self.worker = None; self.working = False
        root = QWidget(); lay = QVBoxLayout(root); lay.setContentsMargins(22, 20, 22, 20); lay.setSpacing(13)
        head = QHBoxLayout(); labels = QVBoxLayout()
        title = QLabel("NORTH <span style='color:#60a5fa'>DEBLOATER</span>"); title.setObjectName('title')
        sub = QLabel(t('app_sub')); sub.setObjectName('muted'); labels.addWidget(title); labels.addWidget(sub); head.addLayout(labels); head.addStretch()
        self.devbox = QComboBox(); self.devbox.setMinimumWidth(240); self.devbox.setToolTip(t('dev_tip')); head.addWidget(self.devbox)
        self.status = QLabel(t('checking')); self.status.setObjectName('status'); head.addWidget(self.status); lay.addLayout(head)

        controls = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText(t('search_ph')); controls.addWidget(self.search, 1)
        self.mode = QComboBox(); self.mode.addItems([t('mode0'), t('mode1'), t('mode2')]); controls.addWidget(self.mode)
        self.scan = QPushButton(t('scan_btn')); controls.addWidget(self.scan); lay.addLayout(controls)

        flt = QHBoxLayout()
        self.f_state = QComboBox(); self.f_state.addItem(t('f_state_all'), '')
        for s in (ST_ACTIVE, ST_DISABLED, ST_REMOVED): self.f_state.addItem(t('st_' + s), s)
        self.f_risk = QComboBox(); self.f_risk.addItem(t('f_risk_all'), '')
        for k in ('safe', 'caution', 'critical', 'unknown'): self.f_risk.addItem(t('risk_' + k), k)
        self.f_list = QComboBox(); self.f_list.addItem(t('f_list_all'), ''); self.f_list.addItem(t('f_known'), 'known'); self.f_list.addItem(t('f_unknown'), 'unknown')
        for k in BRAND_HINTS: self.f_list.addItem(t('b_' + k), k)
        for c in (self.f_state, self.f_risk, self.f_list): flt.addWidget(c)
        flt.addStretch(); self.sel_label = QLabel(t('sel_count', 0)); self.sel_label.setObjectName('muted'); flt.addWidget(self.sel_label)
        self.b_all = QPushButton(t('sel_all')); self.b_none = QPushButton(t('sel_none')); flt.addWidget(self.b_all); flt.addWidget(self.b_none); lay.addLayout(flt)

        self.table = QTableWidget(0, 6); self.table.setHorizontalHeaderLabels(t('cols'))
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.table.verticalHeader().setVisible(False); self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        h = self.table.horizontalHeader(); R = QHeaderView.ResizeMode
        h.setSectionResizeMode(0, R.Interactive); h.setSectionResizeMode(1, R.Stretch); h.setSectionResizeMode(2, R.ResizeToContents); h.setSectionResizeMode(3, R.ResizeToContents); h.setSectionResizeMode(4, R.ResizeToContents); h.setSectionResizeMode(5, R.Stretch)
        self.table.setColumnWidth(0, 190); lay.addWidget(self.table, 1)

        foot = QHBoxLayout(); self.count = QLabel(t('not_scanned')); self.count.setObjectName('muted'); foot.addWidget(self.count); foot.addStretch()
        self.tools = QPushButton(t('tools')); menu = QMenu(self)
        for key, fn in (('m_details', self.show_details), ('m_profile', self.apply_profile), ('m_save', self.save_backup), ('m_load', lambda: self.load_backup()),
                        ('m_last_auto', self.undo_last_auto), ('m_open_auto', self.open_auto_dir), ('m_wifi', self.wifi), ('m_csv', self.export_csv), ('m_update', self.update_list)):
            menu.addAction(t(key), fn)
        lm = menu.addMenu(t('m_lang'))
        for code, label in (('tr', 'Türkçe'), ('en', 'English')):
            a = lm.addAction(label); a.setCheckable(True); a.setChecked(code == LANG); a.triggered.connect(lambda _=False, c=code: self.set_language(c))
        self.tools.setMenu(menu); foot.addWidget(self.tools)
        self.undo = QPushButton(t('undo')); self.undo.setToolTip(t('undo_tip')); foot.addWidget(self.undo)
        self.disable = QPushButton(t('disable')); self.disable.setObjectName('primary'); foot.addWidget(self.disable)
        self.remove = QPushButton(t('remove')); self.remove.setObjectName('danger'); foot.addWidget(self.remove); lay.addLayout(foot)
        self.progress = QProgressBar(); self.progress.setTextVisible(False); self.progress.setFixedHeight(8); lay.addWidget(self.progress)
        note = QLabel(t('note')); note.setObjectName('muted'); note.setWordWrap(True); lay.addWidget(note)
        self.setCentralWidget(root)
        self.setStyleSheet('QMainWindow,QWidget,QDialog{background:#0b1120;color:#e5e7eb;font-size:13px} QLabel#title{font-size:25px;font-weight:800} QLabel#muted{color:#94a3b8} QLabel#status{background:#172033;border:1px solid #334155;border-radius:8px;padding:9px} QLineEdit,QComboBox,QPlainTextEdit,QListWidget{background:#111b2e;border:1px solid #334155;border-radius:8px;padding:8px;color:#fff} QComboBox QAbstractItemView{background:#111b2e;color:#fff;selection-background-color:#1d4ed8} QPushButton{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:10px 14px;color:#f8fafc} QPushButton:hover{background:#29364c} QPushButton:disabled{color:#64748b} QPushButton#primary{background:#1d4ed8;font-weight:700} QPushButton#danger{background:#7f1d1d;font-weight:700} QMenu{background:#111b2e;color:#fff;border:1px solid #334155} QMenu::item:selected{background:#1d4ed8} QTableWidget{background:#0f172a;alternate-background-color:#111c30;border:1px solid #253149;gridline-color:#253149;selection-background-color:#1d4ed8} QHeaderView::section{background:#172033;color:#cbd5e1;padding:10px;border:none} QProgressBar{background:#111827;border:none} QProgressBar::chunk{background:#60a5fa}')
        if geometry: self.setGeometry(geometry)
        # sinyaller en sonda bağlanır (tüm bileşenler hazır olsun)
        self.search.textChanged.connect(self.render); self.mode.currentIndexChanged.connect(lambda _: self.load()); self.scan.clicked.connect(self.load)
        for c in (self.f_state, self.f_risk, self.f_list): c.currentIndexChanged.connect(lambda _: self.render())
        self.devbox.activated.connect(self.on_device_chosen)
        self.table.cellDoubleClicked.connect(lambda *_: self.show_details()); self.table.itemSelectionChanged.connect(self.update_sel)
        self.b_all.clicked.connect(self.table.selectAll); self.b_none.clicked.connect(self.table.clearSelection)
        self.undo.clicked.connect(self.undo_selected); self.disable.clicked.connect(lambda: self.act_selected('disable')); self.remove.clicked.connect(lambda: self.act_selected('remove'))
        QTimer.singleShot(0, self.load)

    def closeEvent(self, e):
        if self.worker and self.working: self.worker.wait(8000)
        e.accept()

    # ---- ortak ----
    def busy(self, b):
        self.progress.setRange(0, 0 if b else 1); self.progress.setValue(0)
        for w in (self.scan, self.remove, self.disable, self.undo, self.tools, self.mode, self.devbox): w.setEnabled(not b)
        if not b: self.update_buttons()

    def update_buttons(self):
        removed_view = self.mode.currentIndex() == MODE_REMOVED
        self.remove.setEnabled(not removed_view); self.disable.setEnabled(not removed_view)

    def run(self, fn, cb, progress=False, on_error=None):
        if self.working: return
        if self.worker: self.worker.wait()      # önceki iş parçacığı tamamen bitsin
        self.working = True; self.busy(True)
        self.worker = Worker(fn, progress); self.worker.progress.connect(self.on_progress)
        self.worker.done.connect(lambda result, err: self.finished(result, err, cb, on_error)); self.worker.start()

    def on_progress(self, i, total, text):
        self.progress.setRange(0, max(total, 1)); self.progress.setValue(i)
        if text: self.status.setText(t('progress', i + 1, total, text))

    def finished(self, result, err, cb, on_error=None):
        self.working = False; self.busy(False)
        if err:
            self.status.setText(t('error')); QMessageBox.warning(self, t('failed_title'), err)
            if on_error: on_error()
        else: cb(result)

    def need_device(self):
        if not self.dev: QMessageBox.information(self, t('no_device_t'), t('no_device')); return False
        return True

    # ---- tarama / görünüm ----
    def load(self):
        if not adb_path():
            a = QMessageBox.question(self, t('adb_missing_t'), t('adb_missing'))
            if a != QMessageBox.StandardButton.Yes: self.status.setText(t('adb_none')); return
            self.status.setText(t('adb_downloading')); self.run(download_adb, lambda _: self.load()); return
        self.status.setText(t('scanning')); mode = self.mode.currentIndex(); pref = self.pref
        self.run(lambda: scan(mode, pref), self.loaded, on_error=self.load_failed)

    def load_failed(self):
        self.dev = None; self.rows = []; self.devbox.clear(); self.render()

    def loaded(self, r):
        self.dev, self.brand, self.rows = r['dev'], r['brand'], r['rows']; self.pref = self.dev
        self.devbox.clear()
        for ser, st, model in r['devices']:
            self.devbox.addItem((model + ' · ' if model else '') + ser + ('' if st == 'device' else f'  [{st}]'), ser)
        self.devbox.setCurrentIndex(max(self.devbox.findData(self.dev), 0))
        self.status.setText(t('connected') + (r['model'] + ' · ' if r['model'] else '') + self.dev); self.render()

    def on_device_chosen(self, i):
        ser = self.devbox.itemData(i)
        if ser and ser != self.dev: self.pref = ser; self.load()

    def render(self):
        mode = self.mode.currentIndex(); q = self.search.text().lower().strip()
        fs, fr, fl = self.f_state.currentData(), self.f_risk.currentData(), self.f_list.currentData()
        self.table.setSortingEnabled(False); self.table.setRowCount(0); shown = 0
        for p, state, size in self.rows:
            name, lab, col, desc, risk = info(p, mode)
            if q and q not in p.lower() and q not in name.lower(): continue
            if fs and state != fs: continue
            if fr and risk != fr: continue
            if fl == 'known' and not is_known(p): continue
            if fl == 'unknown' and is_known(p): continue
            if fl in BRAND_HINTS and brand_of(p) != fl: continue
            row = self.table.rowCount(); self.table.insertRow(row); shown += 1
            cells = [QTableWidgetItem(name or '—'), QTableWidgetItem(p), QTableWidgetItem(t('st_' + state)), QTableWidgetItem(lab), SizeItem(size), QTableWidgetItem(desc)]
            cells[3].setForeground(QColor(col)); cells[2].setForeground(QColor({ST_ACTIVE: GREEN, ST_DISABLED: YELLOW, ST_REMOVED: RED}[state])); cells[5].setToolTip(desc)
            for c, it in enumerate(cells): self.table.setItem(row, c, it)
        self.table.setSortingEnabled(True); self.count.setText(t('count', shown, len(self.rows))); self.update_buttons(); self.update_sel()

    def update_sel(self):
        self.sel_label.setText(t('sel_count', len({x.row() for x in self.table.selectionModel().selectedRows()})))

    def selected(self):
        return [self.table.item(i, 1).text() for i in sorted({x.row() for x in self.table.selectionModel().selectedRows()})]

    def state_of(self, p): return next((s for q, s, _ in self.rows if q == p), ST_ACTIVE)

    # ---- işlemler ----
    OPS = {'remove': (['shell', 'pm', 'uninstall', '--user', '0'], 'success', 'KALDIR'),
           'disable': (['shell', 'pm', 'disable-user', '--user', '0'], 'disabled', 'DEVRE_DISI'),
           'restore': (['shell', 'cmd', 'package', 'install-existing', '--user', '0'], 'installed', 'GERI_YUKLE'),
           'enable': (['shell', 'pm', 'enable', '--user', '0'], 'enabled', 'ETKINLESTIR')}

    def make_work(self, tasks, backup=True):
        """tasks: [(op, paket)]; op: remove | disable | restore | enable. Kaldır/devre dışı varsa önce otomatik yedek alınır."""
        dev = self.dev
        def work(report):
            bpath = ''
            if backup and any(o in ('remove', 'disable') for o, _ in tasks):
                try: bpath = write_auto_backup(dev, tasks)
                except Exception as e: raise RuntimeError(t('backup_fail', e))
            res = []; n = len(tasks)
            for i, (op, p) in enumerate(tasks):
                report(i, n, p); args, needle, tag = self.OPS[op]
                try: out = adb(['-s', dev, *args, p]); ok = needle in out.lower(); m = out or t('done_msg')
                except Exception as e: ok, m = False, str(e)
                log_action(tag, dev, p, ok, m); res.append((p, m, ok))
            report(n, n, '')
            return {'results': res, 'backup': bpath}
        return work

    def confirm(self, title, text, pkgs):
        crit = [p for p in pkgs if info(p, MODE_ALL)[4] == 'critical']
        if crit: text += '\n\n' + t('crit_warn', len(crit), crit[0])
        return QMessageBox.warning(self, title, text + '\n\n' + t('continue_q'), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes

    def act_selected(self, op, pkgs=None):
        pkgs = pkgs if pkgs is not None else self.selected()
        if not pkgs: QMessageBox.information(self, t('select_first_t'), t('select_first')); return
        if not self.need_device(): return
        if op == 'remove': ok = self.confirm(t('confirm_remove_t'), t('confirm_remove', len(pkgs)), pkgs)
        else: ok = self.confirm(t('confirm_disable_t'), t('confirm_disable', len(pkgs)), pkgs)
        if ok: self.run(self.make_work([(op, p) for p in pkgs]), self.report, progress=True)

    def undo_selected(self):
        pkgs = self.selected()
        if not pkgs: QMessageBox.information(self, t('select_first_t'), t('select_undo')); return
        if not self.need_device(): return
        states = {p: self.state_of(p) for p in pkgs}
        todo = [p for p, s in states.items() if s != ST_ACTIVE]
        if not todo: QMessageBox.information(self, t('undo_already_t'), t('undo_already')); return
        if QMessageBox.question(self, t('undo_t'), t('undo_confirm', len(todo))) != QMessageBox.StandardButton.Yes: return
        tasks = [('restore', p) for p in todo if states[p] == ST_REMOVED] + [('enable', p) for p in todo if states[p] == ST_DISABLED]
        self.run(self.make_work(tasks, backup=False), self.report, progress=True)

    def report(self, r):
        res = r['results']; ok = sum(x[2] for x in res)
        detail = '\n'.join(('OK' if good else 'ERR') + ' — ' + p + ': ' + m for p, m, good in res)
        text = t('result', ok, len(res))
        if r['backup']: text += '\n\n' + t('result_backup', r['backup'])
        text += '\n' + t('result_log', os.path.join(data_dir(), 'islem_gunlugu.txt'))
        box = QMessageBox(self); box.setIcon(QMessageBox.Icon.Information); box.setWindowTitle(t('result_t')); box.setText(text); box.setDetailedText(detail); box.exec()
        self.load()

    # ---- ayrıntılar / izinler ----
    def show_details(self):
        ps = self.selected()
        if len(ps) != 1: QMessageBox.information(self, t('select_one_t'), t('select_one')); return
        if not self.need_device(): return
        p, dev = ps[0], self.dev; name, lab, _, desc, _ = info(p, self.mode.currentIndex())
        size = next((s for q, _, s in self.rows if q == p), None); unk = '?'
        def done(d):
            lines = [f'{name or p}  [{lab}]', p, '', desc, '', f'{t("det_version")}: {d["version"] or unk}', f'{t("det_first")}: {d["installed"] or unk}', f'{t("det_updated")}: {d["updated"] or unk}',
                     f'{t("det_installer")}: {d["installer"] or unk}', f'{t("det_path")}: {d["path"] or unk}', f'{t("det_size")}: {human(size) or t("det_unknown")}', '']
            perms = d['granted'] or {}; req = d['requested']
            dang = sorted(k for k in set(perms) | set(req) if short_perm(k) in DANGEROUS)
            lines.append(t('det_perms', len(set(req) | set(perms)), sum(perms.values())))
            lines.append(t('det_sensitive') + ('' if dang else t('det_none')))
            for k in dang: lines.append(f'  {t("det_granted") if perms.get(k) else t("det_denied")}  {short_perm(k)}')
            others = sorted(k for k in set(req) | set(perms) if k not in dang)
            if others: lines += ['', t('det_others')] + [f'  {"✔" if perms.get(k) else "·"} {short_perm(k)}' for k in others]
            dlg = QDialog(self); dlg.setWindowTitle(t('det_title')); dlg.resize(640, 620); l = QVBoxLayout(dlg)
            te = QPlainTextEdit('\n'.join(lines)); te.setReadOnly(True); l.addWidget(te); bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close); bb.rejected.connect(dlg.reject); l.addWidget(bb); dlg.exec()
        self.run(lambda: package_details(dev, p), done)

    # ---- marka profilleri ----
    def apply_profile(self):
        if not self.need_device(): return
        if not PROFILES: QMessageBox.information(self, t('prof_none_t'), t('prof_none')); return
        keys = list(PROFILES); b = (self.brand or '').lower()
        guess = next((i for i, n in enumerate(keys) if PROFILES[n].get('brand') and PROFILES[n]['brand'] in b), 0)
        dlg = QDialog(self); dlg.setWindowTitle(t('prof_t')); l = QVBoxLayout(dlg); l.addWidget(QLabel(t('prof_pick')))
        cb = QComboBox()
        for k in keys: cb.addItem(loc(PROFILES[k], 'name') if LANG == 'en' else k, k)
        cb.setCurrentIndex(guess); l.addWidget(cb)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel); bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); l.addWidget(bb)
        if not dlg.exec(): return
        prof = PROFILES[cb.currentData()]; dev = self.dev; shown = cb.currentText()
        def preview(installed):
            items = [(p, f'{loc(OWN[p], "name")} — {loc(OWN[p], "desc")}', True) for p in prof['packages'] if p in installed and p in OWN]
            if not items: QMessageBox.information(self, t('prof_t'), t('prof_empty')); return
            d = ChecklistDialog(self, shown, t('prof_intro', len(items)), items, [t('prof_a0'), t('prof_a1')])
            if d.exec():
                chosen, idx = d.result_items()
                if chosen: self.act_selected('disable' if idx == 0 else 'remove', chosen)
        self.run(lambda: pkg_set(dev) - pkg_set(dev, '-d'), preview)

    # ---- yedek ----
    def save_backup(self):
        if not self.need_device(): return
        path, _ = QFileDialog.getSaveFileName(self, t('bk_save_t'), f'north-yedek-{datetime.now():%Y%m%d}.json', 'JSON (*.json)')
        if not path: return
        dev = self.dev
        def work():
            data = snapshot(dev)
            with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=1)
            return data
        self.run(work, lambda d: QMessageBox.information(self, t('bk_saved_t'), t('bk_saved', len(d['removed']), len(d['disabled']), path)))

    def undo_last_auto(self):
        files = list_auto_backups()
        if not files: QMessageBox.information(self, t('bk_t'), t('bk_no_auto')); return
        self.load_backup(files[-1])

    def open_auto_dir(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(auto_backup_dir()))

    def load_backup(self, path=None):
        if not self.need_device(): return
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, t('bk_open_t'), auto_backup_dir(), 'JSON (*.json)')
            if not path: return
        data = load_json(path)
        if not isinstance(data, dict) or data.get('app') != 'NorthDebloater': QMessageBox.warning(self, t('bk_bad_t'), t('bk_bad')); return
        dev = self.dev; auto = bool(data.get('auto')); changed = set(data.get('changes', {}).get('remove', [])) | set(data.get('changes', {}).get('disable', []))
        def preview(state):
            installed, disabled, uninstalled = state; items = []
            for p in data.get('removed', []):
                if p in installed or p in uninstalled: items.append((p, f'{t("bk_was_removed")} — {info(p, MODE_ALL)[0] or p}', (p in changed) if auto and changed else True))
            for p in data.get('disabled', []):
                if p in installed: items.append((p, f'{t("bk_was_disabled")} — {info(p, MODE_ALL)[0] or p}', (p in changed) if auto and changed else True))
            if not items: QMessageBox.information(self, t('bk_t'), t('bk_none')); return
            mdl, when = data.get('model', '?'), data.get('created', '?')
            intro = t('bk_intro_auto', mdl, when) if auto else t('bk_intro', mdl, when, len(items))
            d = ChecklistDialog(self, t('bk_dlg'), intro, items, [t('bk_a0'), t('bk_a1')], default_action=1 if auto else 0)
            if not d.exec(): return
            chosen, idx = d.result_items()
            if not chosen: return
            brem, bdis = set(data.get('removed', [])), set(data.get('disabled', []))
            rem = [p for p in chosen if p in brem]; dis = [p for p in chosen if p in bdis and p not in rem]
            if idx == 0:
                if not self.confirm(t('bk_apply_t'), t('bk_apply', len(rem), len(dis)), chosen): return
                tasks = [('remove', p) for p in rem if p in installed] + [('disable', p) for p in dis if p in installed and p not in disabled]
            else:
                tasks = [('restore', p) for p in rem if p in uninstalled] + [('enable', p) for p in chosen if p in disabled]
            if not tasks: QMessageBox.information(self, t('bk_t'), t('nothing')); return
            self.run(self.make_work(tasks), self.report, progress=True)
        self.run(lambda: (pkg_set(dev), pkg_set(dev, '-d'), pkg_set(dev, '-u') - pkg_set(dev)), preview)

    # ---- kablosuz ADB / dil / diğer ----
    def wifi(self):
        WifiDialog(self).exec()

    def set_language(self, code):
        global LANG
        if code == LANG: return
        if self.working: QMessageBox.information(self, APP_NAME, t('lang_busy')); return
        LANG = code; SETTINGS['lang'] = code; save_settings()
        w = Window(pref=self.pref, geometry=self.geometry()); w.show(); self.hide(); self.deleteLater()
        QApplication.instance().main_window = w      # referansı canlı tut

    def update_list(self):
        self.run(update_community, lambda n: (QMessageBox.information(self, t('upd_t'), t('upd', n)), self.render()))

    def export_csv(self):
        if not self.rows: QMessageBox.information(self, t('csv_empty_t'), t('csv_empty')); return
        path, _ = QFileDialog.getSaveFileName(self, t('csv_t'), 'paketler.csv', 'CSV (*.csv)')
        if not path: return
        mode = self.mode.currentIndex()
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f); w.writerow(t('csv_cols'))
            for p, st, sz in self.rows: n, lab, _, d, _ = info(p, mode); w.writerow([n, p, t('st_' + st), lab, sz if sz is not None else '', d])
        QMessageBox.information(self, t('csv_saved_t'), path)


if __name__ == '__main__':
    app = QApplication(sys.argv); app.aboutToQuit.connect(stop_adb); app.main_window = Window(); app.main_window.show(); sys.exit(app.exec())
