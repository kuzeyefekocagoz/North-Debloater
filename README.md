# North Debloater

Windows için ADB tabanlı Android paket yöneticisi.

## Taşınabilir sürümü oluşturma (tek seferlik)
`BUILD_WINDOWS.bat` dosyasına çift tıkla. Betik eksik olan her şeyi kendisi halleder: Python yoksa 3.12'yi kullanıcı klasörüne kurar (yönetici izni gerekmez), PySide6 + PyInstaller'ı `.venv` içine kurar, resmi Android Platform-Tools'u indirir ve `NorthDebloater-Windows-Portable.zip` üretir. Gereken tek şey Windows 10/11 ve internet. Çıkan ZIP hedef bilgisayarda Python gerektirmez.

Windows'un yoksa projeyi GitHub'a yükle: *Actions > Build Windows portable > Run workflow* ZIP'i bulutta derler.

## Özellikler
- **Uygulama adı + açıklama veritabanı** (`packages_db.json`, 84 paket, Türkçe). Veritabanında olmayan paketler için isteğe bağlı topluluk listesi: *Araçlar > Topluluk listesini güncelle* (UAD-NG, ~5400 paket, İngilizce açıklama, GPL-3.0; pakete gömülü değil, çalışma anında indirilir)
- **Marka profilleri:** Samsung, Xiaomi, Oppo/Realme/OnePlus ve üçüncü taraf ön yüklü uygulamalar. Telefon markasına göre otomatik önerilir; yalnızca telefonda gerçekten bulunan paketler listelenir ve tek tek işaretlenebilir
- **Devre dışı bırak** (silmeden, geri alınabilir) veya **Kaldır** (`pm uninstall --user 0`); **Geri al** düğmesi her ikisini de geri çevirir
- **Yedek dosyası (JSON):** kaldırılan ve devre dışı paketleri kaydeder; başka telefonda uygulayabilir ya da geri alabilirsin
- **Boyut sütunu** (uygulama + veri, sıralanabilir) ve **ayrıntı penceresi** (çift tık): sürüm, kurulum tarihi, kuran, APK yolu, verilmiş/verilmemiş izinler, hassas izinler vurgulu
- **Otomatik yedek:** Her *Kaldır* / *Devre dışı bırak* işleminden hemen önce `%LOCALAPPDATA%\NorthDebloater\otomatik_yedekler` klasörüne yedek yazılır (son 30 saklanır; yedek alınamazsa işlem yapılmaz). *Araçlar > Son otomatik yedekten geri al* o işlemi tek adımda geri çevirir
- **Çoklu cihaz:** Üstteki cihaz listesinden bağlı telefonlar arasında geçiş yapılır
- **Kablosuz ADB:** *Araçlar > Kablosuz ADB (Wi-Fi)*: Android 11+ için eşleştirme kodu ile eşleştir/bağlan; Android 10 ve altı için USB bağlıyken "USB'den Wi-Fi'ye geç"
- **Filtreler:** Durum, risk ve liste/marka (bilinenler, bilinmeyenler, Samsung, Xiaomi, Oppo, Google, üçüncü taraf) süzgeçleri; "Görünenlerin hepsini seç" ve seçili sayısı
- **İlerleme:** Toplu işlemde paket paket ilerleme çubuğu ve durum satırı; sonuç penceresinde ayrıntılar katlanabilir
- **Türkçe / İngilizce:** *Araçlar > Dil / Language*; seçim `%LOCALAPPDATA%\NorthDebloater\settings.json` içinde saklanır. Veritabanındaki 84 paketin İngilizce açıklamaları da var
- Kaldırılmış paketler görünümü, ADB yoksa uygulama içinden indirme, CSV dışa aktarma, işlem günlüğü (`%LOCALAPPDATA%\NorthDebloater\islem_gunlugu.txt`)

## Android bağlantısı
Telefonda Geliştirici seçenekleri > USB hata ayıklama açık olmalı; bilgisayara izin verilmeli; veri destekli kablo gerekir.

## Güvenlik
Önce "Devre dışı bırak"ı dene. Bazı sistem paketleri (özellikle yeni Android sürümlerinde) devre dışı bırakmayı veya kaldırmayı reddedebilir; sonuç penceresi bunu gösterir. Kaldırma yalnızca Android kullanıcısı 0 içindir, APK sistem bölümünden silinmez. Risk etiketleri ve profil listeleri garanti değildir; cihaz/sürüm farkları olabilir. Bilinmeyen veya sistem paketlerini araştırmadan kaldırma.
