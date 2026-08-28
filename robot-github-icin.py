import os
import json
import time
import re
from datetime import datetime
from googleapiclient.discovery import build
from google import genai
from jinja2 import Environment, FileSystemLoader
import csv
import io
import requests

# API ANAHTARLARI
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
KANAL_ID = 'UCeVsdlvXtrlBTYY3QCRze9w'
SITE_URL = 'https://marifetliel.com/' 

youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# ==========================================
# ÇOKLU API ANAHTARI SİSTEMİ (ROUND-ROBIN)
# ==========================================
gemini_keys_metni = os.environ.get('GEMINI_API_KEYS', '')

if gemini_keys_metni:
    GEMINI_API_KEYS = gemini_keys_metni.split(',')
else:
    GEMINI_API_KEYS = []

aktif_api_indeksi = 0
client = genai.Client(api_key=GEMINI_API_KEYS[aktif_api_indeksi]) if GEMINI_API_KEYS else None
SECILEN_MODEL = 'gemini-flash-latest'
AI_KOTALARI_DOLDU = False 

def onayli_modelleri_cek():
  csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQkpPlQW7YV4ZgYv4swHZdQxV5NdGhmkxmsTXS2cR2XgV5W7lt9przPz3nuhB4yvg3Wf1-j0jZqdjEu/pub?output=csv"

  try:
    response = requests.get(csv_url)
    response.raise_for_status()

    f = io.StringIO(response.content.decode("utf-8"))
    reader = csv.reader(f)

    onayli_liste = []
    basliklar = next(reader)  

    for satir in reader:
      if len(satir) >= 8 and satir[7] == "Onaylandı":
            baslik_seo = url_uyumlu_yap(satir[4]) 
            if len(baslik_seo) > 50: 
                baslik_seo = baslik_seo[:50].strip('-')
            kisa_id = str(satir[0])[-5:] 
            uretilen_dosya_adi = f"{baslik_seo}-{kisa_id}.html"

            model_verisi = {
                "id": satir[0],
                "tarih": satir[1],
                "yazar": satir[2],
                "kategori": satir[3],
                "baslik": satir[4],
                "makale": satir[5],
                "medya": satir[6],
                "durum": satir[7],
                "dosya_adi": uretilen_dosya_adi,
            }
            onayli_liste.append(model_verisi)

    return onayli_liste
  except Exception as e:
    print(f"E-Tablo okuma hatası: {e}")
    return []

# YENİ EKLENEN: HAFTANIN POPÜLER VİDEOLARINI ÇEKME
def populer_videolari_getir():
    print("\n--- Popüler Videolar Çekiliyor ---")
    try:
        request = youtube.search().list(
            part="snippet", 
            channelId=KANAL_ID, 
            order="viewCount", 
            type="video", 
            maxResults=4
        )
        response = request.execute()
        populerler = []
        for item in response.get('items', []):
            videoid = item['id']['videoId']
            baslik = item['snippet']['title']
            resim = item['snippet']['thumbnails']['high']['url']
            
            baslik_seo = url_uyumlu_yap(baslik)
            if len(baslik_seo) > 50: baslik_seo = baslik_seo[:50].strip('-')
            link = f"{baslik_seo}-{videoid}.html"
            
            populerler.append({'baslik': baslik, 'resim': resim, 'link': link})
        return populerler
    except Exception as e:
        print(f"Popüler video çekme hatası: {e}")
        return []

def api_anahtarini_degistir():
    global aktif_api_indeksi, client, AI_KOTALARI_DOLDU
    aktif_api_indeksi += 1
    
    if aktif_api_indeksi >= len(GEMINI_API_KEYS):
        print("  !!! TÜM API KOTALARI DOLDU. SİTE HIZLICA OLUŞTURULUYOR !!!")
        AI_KOTALARI_DOLDU = True
        return False
        
    client = genai.Client(api_key=GEMINI_API_KEYS[aktif_api_indeksi])
    print(f"  🔄 API DEĞİŞTİRİLDİ -> Şu an {aktif_api_indeksi + 1}. API kullanılıyor.")
    return True

def yapay_zeka_makale_yazdir(baslik, aciklama):
    global client, AI_KOTALARI_DOLDU
    
    if AI_KOTALARI_DOLDU or not client:
        return None
        
    prompt = f"""
    Sen yöresel el sanatları ve iğne oyası konusunda uzman, çok okunan bir blog yazarısın.
    Şu YouTube videosu için web sitesinde yayınlanmak üzere SEO uyumlu, kadın ziyaretçileri sitede tutacak samimi bir makale yaz.
    Video Başlığı: "{baslik}"
    
    LÜTFEN SADECE ŞU YAPIYI HTML ETİKETLERİ İLE (<h3>, <p>, <ul>, <li>, <strong>) VER (```html bloğu kullanma, doğrudan kodu ver):
    1. <h3>Modelin Özellikleri ve Zarafeti</h3> 
    2. <h3>Renk Uyumu ve İp Seçimi Tavsiyeleri</h3> 
    3. <h3>Sıkça Sorulan Sorular</h3> 
    """
    
    deneme_sayisi = 0
    maksimum_deneme = len(GEMINI_API_KEYS) if GEMINI_API_KEYS else 1
    
    while deneme_sayisi < maksimum_deneme:
        try:
            response = client.models.generate_content(model=SECILEN_MODEL, contents=prompt)
            time.sleep(7) 
            metin = response.text.replace("```html", "").replace("```", "").strip()
            
            if len(metin) < 50:
                print("  ! API çok kısa bir yanıt döndürdü, geçiliyor.")
                return None
            return metin
            
        except Exception as e:
            hata_mesaji = str(e)
            if '429' in hata_mesaji or 'RESOURCE_EXHAUSTED' in hata_mesaji or 'Quota' in hata_mesaji:
                if not api_anahtarini_degistir():
                    return None
                deneme_sayisi += 1
            else:
                print(f"  X Bilinmeyen hata: {e}")
                time.sleep(10)
                return None
                
    return None

def oynatma_listelerini_getir():
    request = youtube.playlists().list(part="snippet", channelId=KANAL_ID, maxResults=50)
    return request.execute().get('items', [])

def listedeki_videolari_getir(playlist_id):
    request = youtube.playlistItems().list(part="snippet", playlistId=playlist_id, maxResults=50)
    videolar = []
    response = None
    for deneme in range(3): 
        try:
            response = request.execute()
            break 
        except Exception as e:
            print(f"YouTube bağlantısı yoruldu (Deneme {deneme+1}/3). 2 saniye bekleniyor... Hata: {e}")
            time.sleep(2)  
            
    if not response:
        return []

    for item in request.execute().get('items', []):
        snippet = item['snippet']
        if 'videoId' in snippet['resourceId']:
            thumbs = snippet.get('thumbnails', {})
            resim_url = thumbs.get('high', {}).get('url') or thumbs.get('medium', {}).get('url') or thumbs.get('default', {}).get('url', '')
            videolar.append({
                'id': snippet['resourceId']['videoId'],
                'title': snippet['title'],
                'description': snippet['description'],
                'thumbnail': resim_url
            })
    return videolar

def url_uyumlu_yap(metin):
    metin = str(metin).lower()
    metin = metin.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
    metin = re.sub(r'[^a-z0-9\s-]', '', metin)
    metin = re.sub(r'[-\s]+', '-', metin).strip('-')
    return metin

def guvenli_dosya_adi(isim):
    isim = isim.replace('ı', 'i').replace('İ', 'i').replace('ğ', 'g').replace('Ğ', 'g')
    isim = isim.replace('ü', 'u').replace('Ü', 'u').replace('ş', 's').replace('Ş', 's')
    isim = isim.replace('ö', 'o').replace('Ö', 'o').replace('ç', 'c').replace('Ç', 'c')
    isim = isim.lower()
    isim = re.sub(r'[^a-z0-9]+', '-', isim)
    return isim.strip('-')[:50]

def sitemap_olustur(sayfa_listesi):
    bugun = datetime.now().strftime("%Y-%m-%d")
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="[http://www.sitemaps.org/schemas/sitemap/0.9](http://www.sitemaps.org/schemas/sitemap/0.9)">\n'
    for sayfa in sayfa_listesi:
        xml += f'  <url>\n    <loc>{SITE_URL}{sayfa.replace(" ", "%20")}</loc>\n    <lastmod>{bugun}</lastmod>\n  </url>\n'
    xml += '</urlset>'
    with open('sitemap.xml', 'w', encoding='utf-8') as f: f.write(xml)

def sayfalari_olustur():
    if not os.path.exists('cikti_sayfalari'): os.makedirs('cikti_sayfalari')

    cache_dosyasi = 'ai_icerik_cache.json'
    if os.path.exists(cache_dosyasi):
        with open(cache_dosyasi, 'r', encoding='utf-8') as f:
            ai_cache = json.load(f)
    else:
        ai_cache = {}

    env = Environment(loader=FileSystemLoader('.'))
    template_video = env.get_template('video_sablon.html')
    template_index = env.get_template('index_sablon.html') 

    site_verisi = {} 
    ana_menuler = [] 
    uretilen_sayfalar = ['index.html']
    tum_videolar_arama_icin = []
    tum_videolar_ham = []

    # 1. YouTube'dan Popüler Videoları Çekme
    populer_videolar = populer_videolari_getir()

    listeler = oynatma_listelerini_getir()
    print(f"Sistem Başlatıldı. {len(listeler)} kategori bulundu.\n")
    
    tum_kategoriler = []
    for liste in listeler:
        kat_adi = liste['snippet']['title']
        tum_kategoriler.append({'baslik': kat_adi, 'dosya_adi': f"kategori_{guvenli_dosya_adi(kat_adi)}.html"})

    # Kategori Sıralama Altyapısı: Eğer ileride yöneticiden bir sıralama listesi gelirse burada tum_kategoriler'i sort edebiliriz.
    
    for index, liste in enumerate(listeler):
        time.sleep(0.5) 
        kategori_adi = liste['snippet']['title']
        playlist_id = liste['id']
        kategori_dosya_adi = f"kategori_{guvenli_dosya_adi(kategori_adi)}.html"
        
        print(f"\n--- [{kategori_adi}] İşleniyor ---")
        videolar = listedeki_videolari_getir(playlist_id)
        if not videolar: continue
            
        site_verisi[kategori_adi] = {'dosya_adi': kategori_dosya_adi, 'ilk_resim': videolar[0]['thumbnail'], 'video_sayisi': len(videolar)}
        if index < 4: ana_menuler.append({'baslik': kategori_adi, 'dosya_adi': kategori_dosya_adi})
        uretilen_sayfalar.append(kategori_dosya_adi)
        video_verileri_kategori_icin = []

        for video in videolar:
            baslik_seo = url_uyumlu_yap(video['title'])
            if len(baslik_seo) > 50: baslik_seo = baslik_seo[:50].strip('-')
            dosya_adi = f"{baslik_seo}-{video['id']}.html" 
            
            tum_videolar_ham.append({
                'id': video['id'],
                'title': video['title'],
                'description': video['description'],
                'thumbnail': video['thumbnail'],
                'kategori_adi': kategori_adi,
                'kategori_dosya_adi': kategori_dosya_adi,
                'dosya_adi': dosya_adi
            })

            if video['id'] in ai_cache and len(ai_cache[video['id']]) > 50:
                print(f"  √ {video['title'][:30]}... (Önbellekten alındı)")
                video['ai_metin'] = ai_cache[video['id']]
            else:
                if AI_KOTALARI_DOLDU:
                    video['ai_metin'] = ""
                else:
                    print(f"  + {video['title'][:30]}... (Yapay Zeka Makale Yazıyor)")
                    yeni_metin = yapay_zeka_makale_yazdir(video['title'], video['description'])
                    if yeni_metin:
                        video['ai_metin'] = yeni_metin
                        ai_cache[video['id']] = yeni_metin
                        with open(cache_dosyasi, 'w', encoding='utf-8') as f:
                            json.dump(ai_cache, f, ensure_ascii=False, indent=4)
                    else:
                        video['ai_metin'] = ""
            
            html_icerik = template_video.render(video=video, kategori_adi=kategori_adi, kategori_dosya_adi=kategori_dosya_adi, tum_kategoriler=tum_kategoriler)
            
            with open(f"{dosya_adi}", 'w', encoding='utf-8') as f: 
                f.write(html_icerik)

            uretilen_sayfalar.append(dosya_adi)
            video_verileri_kategori_icin.append({'title': video['title'], 'dosya_adi': dosya_adi, 'thumbnail': video['thumbnail']})

            tum_videolar_arama_icin.append({
                "baslik": video['title'],
                "link": dosya_adi,
                "resim": video['thumbnail']
            })
            
        kategori_html = template_index.render(is_ana_sayfa=False, sayfa_basligi=kategori_adi, videolar=video_verileri_kategori_icin, tum_kategoriler=tum_kategoriler)
        with open(f"{kategori_dosya_adi}", 'w', encoding='utf-8') as f: f.write(kategori_html)

    # 2. E-Tablodan Onaylı Modelleri Çek
    onayli_modeller = onayli_modelleri_cek()
    
    # 3. YENİ EKLENEN: Son 5 Modeli Ayrıştırma (Sondan başa doğru ilk 5'i al)
    son_5_model = list(reversed(onayli_modeller))[:5]

    template_kullanici_model = env.get_template('kullanici_model_sablon.html')

    for model in onayli_modeller:
      model_html = template_kullanici_model.render(model=model)
      dosya_yolu = os.path.join('', model['dosya_adi'])

      with open(dosya_yolu, 'w', encoding='utf-8') as f:
        f.write(model_html)

      uretilen_sayfalar.append(model['dosya_adi'])
      print(f"Yayınlanan Model Sayfası Üretildi: {model['dosya_adi']}")

    # ==========================================
    # KULLANICI KATEGORİ SAYFALARININ ÜRETİLMESİ
    # ==========================================
    kullanici_kategorileri = {
        "İğne Oyası": "kullanici_kategori_igne_oyasi.html",
        "Mekik Oyası": "kullanici_kategori_mekik_oyasi.html",
        "Tığ Oyası": "kullanici_kategori_tig_oyasi.html",
        "Örgü Modelleri": "kullanici_kategori_orgu_modelleri.html",
        "Diğer El İşleri": "kullanici_kategori_diger_el_isleri.html"
    }

    # Modelleri ait oldukları kategoriye göre gruplamak için boş sözlükler oluşturuyoruz
    kategori_modelleri = {k: [] for k in kullanici_kategorileri.keys()}

    # Onaylı modelleri tarayıp ilgili kategori listesine ekliyoruz
    for model in onayli_modeller:
        kat = model['kategori']
        if kat in kategori_modelleri:
            kategori_modelleri[kat].append({
                'title': model['baslik'],
                'dosya_adi': model['dosya_adi'],
                'thumbnail': model['medya'] # Kapak fotoğrafı olarak yüklenen medyayı kullanıyoruz
            })

    print("\nKullanıcı Kategori Sayfaları Oluşturuluyor...")
    # Her bir kategori için HTML sayfasını üretiyoruz
    for kat_adi, dosya_adi in kullanici_kategorileri.items():
        kat_html = template_index.render(
            is_ana_sayfa=False, 
            sayfa_basligi=f"{kat_adi} (Sizden Gelenler)", 
            videolar=kategori_modelleri[kat_adi], 
            tum_kategoriler=tum_kategoriler
        )
        with open(dosya_adi, 'w', encoding='utf-8') as f:
            f.write(kat_html)
        
        uretilen_sayfalar.append(dosya_adi)
        print(f"  √ {dosya_adi} üretildi. ({len(kategori_modelleri[kat_adi])} model)")
    # ==========================================

    print("\nAna sayfa, Sitemap ve Veritabanları oluşturuluyor...")
    
    # ŞABLONA YENİ VERİLERİ (POPÜLER VİDEOLAR VE SON 5 MODEL) GÖNDERİYORUZ
    index_icerik = template_index.render(
        is_ana_sayfa=True, 
        sayfa_basligi="Ana Sayfa", 
        site_verisi=site_verisi, 
        tum_kategoriler=tum_kategoriler,
        populer_videolar=populer_videolar,  
        son_modeller=son_5_model            
    )
    
    with open('index.html', 'w', encoding='utf-8') as f: f.write(index_icerik)
    sitemap_olustur(uretilen_sayfalar)

    template_giris = env.get_template('giris_sablon.html')
    giris_icerik = template_giris.render()
    with open('giris.html', 'w', encoding='utf-8') as f: f.write(giris_icerik)
    uretilen_sayfalar.append('giris.html') 

    template_profil = env.get_template('profil_sablon.html')
    profil_icerik = template_profil.render(tum_kategoriler=tum_kategoriler)
    with open('profil.html', 'w', encoding='utf-8') as f: f.write(profil_icerik)
    uretilen_sayfalar.append('profil.html') 

    template_model = env.get_template('model_sablon.html')
    model_icerik = template_model.render(tum_kategoriler=tum_kategoriler)
    with open('model-gonder.html', 'w', encoding='utf-8') as f: 
        f.write(model_icerik)
    uretilen_sayfalar.append('model-gonder.html')
    
    uretilen_sayfalar.extend(['hakkimizda.html', 'iletisim.html', 'gizlilik-politikasi.html'])
    sitemap_olustur(uretilen_sayfalar)

    with open('arama_verisi.json', 'w', encoding='utf-8') as f:
        json.dump(tum_videolar_arama_icin, f, ensure_ascii=False)
        
    with open('tum_videolar_ham.json', 'w', encoding='utf-8') as f:
        json.dump(tum_videolar_ham, f, ensure_ascii=False)
        
    print("İşlem tamamlandı! Web sitesi oluşturuldu.")

if __name__ == '__main__':
    sayfalari_olustur()
