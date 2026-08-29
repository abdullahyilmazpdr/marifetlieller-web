import os
import json
import time
import re
from datetime import datetime
from googleapiclient.discovery import build
from google import genai
from google.genai import types
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
# ÇOKLU API ANAHTARI VE ÇOKLU MODEL SİSTEMİ
# ==========================================
gemini_keys_metni = os.environ.get('GEMINI_API_KEYS', '')
GEMINI_API_KEYS = gemini_keys_metni.split(',') if gemini_keys_metni else []

# Yöneticinin İstediği Öncelikli Modeller Listesi
MODELLER = [
    'gemini-flash-latest',
    'gemini-3.6-flash',
    'gemini-3.5-flash',
    'gemini-3.6-flash-lite',
    'gemini-3.5-flash-lite',
    'gemini-2.5-flash' # Sistemin çökmemesi için Google'ın garanti mevcut olan sürümü
]

aktif_api_indeksi = 0
aktif_model_indeksi = 0
client = genai.Client(api_key=GEMINI_API_KEYS[aktif_api_indeksi]) if GEMINI_API_KEYS else None
AI_KOTALARI_DOLDU = False 

# MERKEZİ YAPAY ZEKA MOTORU (Hem API hem Model Değiştirme Korumalı)
def gemini_istek_gonder(prompt):
    global aktif_api_indeksi, aktif_model_indeksi, client, AI_KOTALARI_DOLDU
    
    if AI_KOTALARI_DOLDU or not client:
        return ""
        
    deneme = 0
    # Tüm modelleri ve tüm API'leri en az 1 tur deneyebilmek için maksimum sınır
    maks_deneme = (len(GEMINI_API_KEYS) if GEMINI_API_KEYS else 1) * len(MODELLER) * 2
    
    while deneme < maks_deneme:
        secilen_model = MODELLER[aktif_model_indeksi]
        try:
            response = client.models.generate_content(model=secilen_model, contents=prompt)
            time.sleep(4)
            metin = response.text.replace("```html", "").replace("```", "").strip()
            if len(metin) > 20:
                return metin
            return ""
        except Exception as e:
            hata = str(e).lower()
            print(f"  X Hata ({secilen_model} | API {aktif_api_indeksi + 1}): {hata}")
            
            # 1. Hata Türü: Model Bulunamadı / Geçersiz İsim
            if '404' in hata or 'not found' in hata or 'invalid' in hata or 'not supported' in hata:
                aktif_model_indeksi += 1
                if aktif_model_indeksi >= len(MODELLER):
                    aktif_model_indeksi = 0
                    aktif_api_indeksi += 1
                    if aktif_api_indeksi >= len(GEMINI_API_KEYS):
                        AI_KOTALARI_DOLDU = True
                        print("  !!! TÜM MODELLER VE API'LER TÜKENDİ !!!")
                        return ""
                    client = genai.Client(api_key=GEMINI_API_KEYS[aktif_api_indeksi])
                print(f"  🔄 MODEL GEÇERSİZ -> Yeni Model Deneniyor: {MODELLER[aktif_model_indeksi]}")
            
            # 2. Hata Türü: Kota Doldu, Timeout veya Diğerleri
            else:
                aktif_api_indeksi += 1
                if aktif_api_indeksi >= len(GEMINI_API_KEYS):
                    # API'ler bittiyse başa dönüp Modeli değiştirelim
                    aktif_api_indeksi = 0
                    aktif_model_indeksi += 1
                    if aktif_model_indeksi >= len(MODELLER):
                        AI_KOTALARI_DOLDU = True
                        print("  !!! TÜM API'LERİN KOTASI DOLDU !!!")
                        return ""
                    print(f"  🔄 API'LER BİTTİ -> Yeni Model Deneniyor: {MODELLER[aktif_model_indeksi]}")
                else:
                    print(f"  🔄 KOTA DOLDU -> Yeni API'ye Geçildi: {aktif_api_indeksi + 1}")
                
                client = genai.Client(api_key=GEMINI_API_KEYS[aktif_api_indeksi])
            
            time.sleep(3)
            deneme += 1

    return ""

def yapay_zeka_makale_yazdir(baslik, aciklama):
    prompt = f"""
    Sen yöresel el sanatları ve iğne oyası konusunda uzman, çok okunan bir blog yazarısın.
    Şu YouTube videosu için web sitesinde yayınlanmak üzere SEO uyumlu, kadın ziyaretçileri sitede tutacak samimi bir makale yaz.
    Video Başlığı: "{baslik}"
    
    LÜTFEN SADECE ŞU YAPIYI HTML ETİKETLERİ İLE (<h3>, <p>, <ul>, <li>, <strong>) VER (```html bloğu kullanma, doğrudan kodu ver):
    1. <h3>Modelin Özellikleri ve Zarafeti</h3> 
    2. <h3>Renk Uyumu ve İp Seçimi Tavsiyeleri</h3> 
    3. <h3>Sıkça Sorulan Sorular</h3> 
    """
    return gemini_istek_gonder(prompt)

def model_gorsel_analizi_yap(resim_url, baslik):
    global client, AI_KOTALARI_DOLDU
    if AI_KOTALARI_DOLDU or not client:
        return {"anahtar_kelimeler": [], "baskin_kategori": ""}
        
    try:
        # Resmi indiriyoruz
        resim_data = requests.get(resim_url, timeout=10).content
    except:
        return {"anahtar_kelimeler": [], "baskin_kategori": ""}

    prompt = f"""
    Sen uzman bir oya ve el işi analistisin. Sana '{baslik}' başlıklı bir eğitim videosunun kapak fotoğrafını gönderiyorum.
    Görevlerin:
    1. Resimdeki oya modelini/motifini dikkatlice incele (şekli, tarzı, belirgin renkleri, tekniği).
    2. Bu modeli bir kullanıcının arama çubuğunda aratabileceği EN BELİRGİN 5-6 spesifik anahtar kelimeyi (Örn: "menekşe", "karanfil", "sıralı", "keloğlan", "zarif yaprak", "sarı lacivert") belirle.
    3. Bu modelin aşağıdaki kategorilerden HANGİSİNE en çok (Baskın olarak) ait olduğunu seç:
       ["İğne Oyası Yapılışı", "Mekik Oyası Yapılışı", "Yazmada İğne Oyası Modelleri", "Fular Modelleri ve Anlatımlı Yapılış Videoları", "Keloğlan Modelleri", "Kelebek Modelleri", "İğne Oyası Havlu Kenarı Modelleri ve Yapılışları"]

    SADECE GEÇERLİ BİR JSON DÖNDÜR. Markdown veya açıklama kullanma. Format:
    {{
      "anahtar_kelimeler": ["kelime1", "kelime2", "kelime3", "kelime4", "kelime5"],
      "baskin_kategori": "Seçilen Kategori Adı"
    }}
    """
    
    deneme = 0
    maks_deneme = (len(GEMINI_API_KEYS) if GEMINI_API_KEYS else 1) * 2
    
    while deneme < maks_deneme:
        try:
            # Resmi ve metni Gemini'ye gönderiyoruz
            response = client.models.generate_content(
                model=SECILEN_MODEL,
                contents=[
                    prompt,
                    types.Part.from_bytes(data=resim_data, mime_type='image/jpeg')
                ]
            )
            time.sleep(4)
            metin = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(metin)
        except Exception as e:
            hata = str(e).lower()
            if '429' in hata or 'quota' in hata or 'exhausted' in hata:
                if not api_anahtarini_degistir():
                    return {"anahtar_kelimeler": [], "baskin_kategori": ""}
            time.sleep(3)
            deneme += 1
            
    return {"anahtar_kelimeler": [], "baskin_kategori": ""}

def kategori_seo_uret(kategori_adi):
    prompt = f"""
    Sen yöresel el sanatları, iğne oyası ve mekik oyası konusunda uzman, güncel arama trendlerine hakim bir SEO içerik yazarısın. Sitenin adı 'Marifetli Eller'.
    İçerik üreteceğin kategori: "{kategori_adi}"
    
    Görevlerin:
    1. Önce bu kategori ismi için kullanıcıların Google'da en çok aratabileceği, niş ve ilgili anahtar kelimeleri (SGE uyumlu, semantik kelimeleri) kendi zihninde analiz et.
    2. Ardından, bu belirlediğin özel anahtar kelimeleri metnin içine yapay durmayacak şekilde, doğal bir akışla yedirerek 2 paragraflık özgün bir SEO açıklama metni yaz. Ziyaretçiye değer katsın ve okuması keyifli olsun.
    
    LÜTFEN SADECE <p> ve vurgulamak istediğin yerler için <strong> etiketlerini kullan. Başka HTML veya Markdown (```) işareti KULLANMA. Bana anahtar kelime listesini verme, SADECE doğrudan web sitesine basılacak olan HTML formatındaki 2 paragrafı ver.
    """
    return gemini_istek_gonder(prompt)

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
            
            # YENİ: Eğer tabloda sabit bir URL varsa onu kullan, yoksa başlıkta üret ve sabitle
            sabit_url_degeri = satir[10] if len(satir) > 10 and satir[10].strip() != "" else ""
            
            if sabit_url_degeri:
                uretilen_dosya_adi = sabit_url_degeri
            else:
                baslik_seo = url_uyumlu_yap(satir[4]) 
                if len(baslik_seo) > 50: 
                    baslik_seo = baslik_seo[:50].strip('-')
                kisa_id = str(satir[0])[-5:] 
                uretilen_dosya_adi = f"{baslik_seo}-{kisa_id}.html"
                # (İsteğe bağlı: İleride bu ilk üretilen adı Apps Script ile otomatik olarak K sütununa da yazdırabiliriz)

            model_verisi = {
                "id": satir[0],
                "tarih": satir[1],
                "yazar": satir[2],
                "kategori": satir[3],
                "baslik": satir[4],
                "makale": satir[5],
                "medya": satir[6],
                "durum": satir[7],
                "dosya_adi": uretilen_dosya_adi, # Sabit dosya adı artık mühürlendi!
            }
            onayli_liste.append(model_verisi)

    return onayli_liste
  except Exception as e:
    print(f"E-Tablo okuma hatası: {e}")
    return []

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
            aciklama = item['snippet']['description'] 
            
            thumbs = item['snippet'].get('thumbnails', {})
            resim = thumbs.get('high', {}).get('url') or thumbs.get('medium', {}).get('url') or thumbs.get('default', {}).get('url', '')
            
            baslik_seo = url_uyumlu_yap(baslik)
            if len(baslik_seo) > 50: baslik_seo = baslik_seo[:50].strip('-')
            link = f"{baslik_seo}-{videoid}.html"
            
            populerler.append({'id': videoid, 'baslik': baslik, 'description': aciklama, 'resim': resim, 'link': link})
        return populerler
    except Exception as e:
        print(f"Popüler video çekme hatası: {e}")
        return []

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
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for sayfa in sayfa_listesi:
        xml += f'  <url>\n    <loc>{SITE_URL}{sayfa.replace(" ", "%20")}</loc>\n    <lastmod>{bugun}</lastmod>\n  </url>\n'
    xml += '</urlset>'
    with open('sitemap.xml', 'w', encoding='utf-8') as f: f.write(xml)

ISTENEN_SIRALAMA = [
    "İğne Oyası Yapılışı",
    "Mekik Oyası Yapılışı",
    "Yazmada İğne Oyası Modelleri",
    "Fular Modelleri ve Anlatımlı Yapılış Videoları",
    "Keloğlan Modelleri",
    "Kelebek Modelleri",
    "İğne Oyası Havlu Kenarı Modelleri ve Yapılışları",
]

def sayfalari_olustur():
    if not os.path.exists('cikti_sayfalari'): os.makedirs('cikti_sayfalari')

    cache_dosyasi = 'ai_icerik_cache.json'
    if os.path.exists(cache_dosyasi):
        with open(cache_dosyasi, 'r', encoding='utf-8') as f:
            ai_cache = json.load(f)
    else:
        ai_cache = {}

    seo_dosyasi = 'kategori_seo.json'
    if os.path.exists(seo_dosyasi):
        with open(seo_dosyasi, 'r', encoding='utf-8') as f:
            kategori_seo_sozluk = json.load(f)
    else:
        kategori_seo_sozluk = {}

    # Görsel Analiz Cache Dosyası
    vision_cache_dosyasi = 'vision_cache.json'
    if os.path.exists(vision_cache_dosyasi):
        with open(vision_cache_dosyasi, 'r', encoding='utf-8') as f:
            vision_cache = json.load(f)
    else:
        vision_cache = {}
    
    env = Environment(loader=FileSystemLoader('.'))
    template_video = env.get_template('video_sablon.html')
    template_index = env.get_template('index_sablon.html') 

    site_verisi = {} 
    ana_menuler = [] 
    uretilen_sayfalar = ['index.html']
    tum_videolar_arama_icin = {} 
    tum_videolar_ham = []

    populer_videolar = populer_videolari_getir()

    listeler = oynatma_listelerini_getir()
    print(f"Sistem Başlatıldı. {len(listeler)} kategori bulundu.\n")

    def siralama_anahtari(liste_item):
        baslik = liste_item['snippet']['title']
        try:
            return ISTENEN_SIRALAMA.index(baslik)
        except ValueError:
            return 999

    listeler.sort(key=siralama_anahtari)
    
    tum_kategoriler = []
    for liste in listeler:
        kat_adi = liste['snippet']['title']
        tum_kategoriler.append({'baslik': kat_adi, 'dosya_adi': f"kategori_{guvenli_dosya_adi(kat_adi)}.html"})

    for index, liste in enumerate(listeler):
        try:
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
                try:
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

                    # Sadece başlık değil, açıklama ve makaleyi de arama hafızasına alıyoruz
                    # --- YAPAY ZEKA KAPAK FOTOĞRAFI ANALİZİ ---
                    if video['id'] in vision_cache:
                        print(f"    √ Görsel analiz hafızadan alındı.")
                        gorsel_verisi = vision_cache[video['id']]
                    else:
                        print(f"    + Kapak fotoğrafı AI ile analiz ediliyor...")
                        gorsel_verisi = model_gorsel_analizi_yap(video['thumbnail'], video['title'])
                        if gorsel_verisi and len(gorsel_verisi.get("anahtar_kelimeler", [])) > 0:
                            vision_cache[video['id']] = gorsel_verisi
                            with open(vision_cache_dosyasi, 'w', encoding='utf-8') as f:
                                json.dump(vision_cache, f, ensure_ascii=False, indent=4)
                    # -------------------------------------------

                    tum_videolar_arama_icin[dosya_adi] = {
                        "baslik": str(video.get('title', '')),
                        "link": dosya_adi,
                        "resim": video.get('thumbnail', ''),
                        "aciklama": str(video.get('description', '')),
                        "makale": str(video.get('ai_metin', '')),
                        "ai_anahtar_kelimeler": gorsel_verisi.get("anahtar_kelimeler", []), # YENİ
                        "baskin_kategori": gorsel_verisi.get("baskin_kategori", kategori_adi) # YENİ
                    }
                except Exception as e:
                    print(f"  ! Video işlenirken hata (Atlanıyor): {e}")

            if kategori_adi not in kategori_seo_sozluk or len(kategori_seo_sozluk[kategori_adi]) < 10:
                print(f"  + Kategori SEO Metni Yazdırılıyor: {kategori_adi}")
                yeni_seo = kategori_seo_uret(kategori_adi)
                if yeni_seo:
                    kategori_seo_sozluk[kategori_adi] = yeni_seo
                    with open(seo_dosyasi, 'w', encoding='utf-8') as f:
                        json.dump(kategori_seo_sozluk, f, ensure_ascii=False, indent=4)
                else:
                    kategori_seo_sozluk[kategori_adi] = "" 
            
            kat_seo_metni = kategori_seo_sozluk.get(kategori_adi, "")
                
            kategori_html = template_index.render(is_ana_sayfa=False, sayfa_basligi=kategori_adi, videolar=video_verileri_kategori_icin, tum_kategoriler=tum_kategoriler,kategori_seo_metni=kat_seo_metni)
            with open(f"{kategori_dosya_adi}", 'w', encoding='utf-8') as f: f.write(kategori_html)
            
        except Exception as e:
            print(f"! Kategori işlenirken genel hata (Atlanıyor): {e}")

    # GÜVENLİK AĞI EKLENDİ (TRY-EXCEPT)
    print("\n--- Serbest Popüler Videolar Kontrol Ediliyor ---")
    for pop_vid in populer_videolar:
        try:
            dosya_adi = pop_vid['link']
            
            if dosya_adi not in uretilen_sayfalar:
                print(f"  + Eksik popüler video bulundu, sayfası üretiliyor: {pop_vid['baslik']}")
                
                video_data = {
                    'id': pop_vid['id'],
                    'title': pop_vid['baslik'],
                    'description': pop_vid['description'],
                    'thumbnail': pop_vid['resim']
                }
                
                if video_data['id'] in ai_cache and len(ai_cache[video_data['id']]) > 50:
                    print(f"  √ (Önbellekten alındı)")
                    video_data['ai_metin'] = ai_cache[video_data['id']]
                else:
                    print(f"  + (Yapay Zeka Makale Yazıyor)")
                    yeni_metin = yapay_zeka_makale_yazdir(video_data['title'], video_data['description'])
                    if yeni_metin:
                        video_data['ai_metin'] = yeni_metin
                        ai_cache[video_data['id']] = yeni_metin
                        with open(cache_dosyasi, 'w', encoding='utf-8') as f:
                            json.dump(ai_cache, f, ensure_ascii=False, indent=4)
                    else:
                        video_data['ai_metin'] = ""
                            
                html_icerik = template_video.render(
                    video=video_data, 
                    kategori_adi="Popüler Videolar", 
                    kategori_dosya_adi="index.html", 
                    tum_kategoriler=tum_kategoriler
                )
                
                with open(dosya_adi, 'w', encoding='utf-8') as f: 
                    f.write(html_icerik)
                    
                uretilen_sayfalar.append(dosya_adi)
                # Sadece başlık değil, açıklama ve makaleyi de arama hafızasına alıyoruz
                # --- YAPAY ZEKA KAPAK FOTOĞRAFI ANALİZİ ---
                    if video['id'] in vision_cache:
                        print(f"    √ Görsel analiz hafızadan alındı.")
                        gorsel_verisi = vision_cache[video['id']]
                    else:
                        print(f"    + Kapak fotoğrafı AI ile analiz ediliyor...")
                        gorsel_verisi = model_gorsel_analizi_yap(video['thumbnail'], video['title'])
                        if gorsel_verisi and len(gorsel_verisi.get("anahtar_kelimeler", [])) > 0:
                            vision_cache[video['id']] = gorsel_verisi
                            with open(vision_cache_dosyasi, 'w', encoding='utf-8') as f:
                                json.dump(vision_cache, f, ensure_ascii=False, indent=4)
                    # -------------------------------------------

                    tum_videolar_arama_icin[dosya_adi] = {
                        "baslik": str(video.get('title', '')),
                        "link": dosya_adi,
                        "resim": video.get('thumbnail', ''),
                        "aciklama": str(video.get('description', '')),
                        "makale": str(video.get('ai_metin', '')),
                        "ai_anahtar_kelimeler": gorsel_verisi.get("anahtar_kelimeler", []), # YENİ
                        "baskin_kategori": gorsel_verisi.get("baskin_kategori", kategori_adi) # YENİ
                    }
        except Exception as e:
            print(f"  ! Popüler video işlenirken hata oluştu (Atlanıyor): {e}")

    onayli_modeller = onayli_modelleri_cek()
    son_5_model = list(reversed(onayli_modeller))[:5]

    template_kullanici_model = env.get_template('kullanici_model_sablon.html')

    for model in onayli_modeller:
      try:
          model_html = template_kullanici_model.render(model=model)
          dosya_yolu = os.path.join('', model['dosya_adi'])
    
          with open(dosya_yolu, 'w', encoding='utf-8') as f:
            f.write(model_html)
    
          uretilen_sayfalar.append(model['dosya_adi'])
          print(f"Yayınlanan Model Sayfası Üretildi: {model['dosya_adi']}")
      except Exception as e:
          print(f"Kullanıcı modeli üretilirken hata: {e}")

    kullanici_kategorileri = {
        "İğne Oyası": "kullanici_kategori_igne_oyasi.html",
        "Mekik Oyası": "kullanici_kategori_mekik_oyasi.html",
        "Tığ Oyası": "kullanici_kategori_tig_oyasi.html",
        "Örgü Modelleri": "kullanici_kategori_orgu_modelleri.html",
        "Diğer El İşleri": "kullanici_kategori_diger_el_isleri.html"
    }

    kategori_modelleri = {k: [] for k in kullanici_kategorileri.keys()}

    for model in onayli_modeller:
        kat = model['kategori']
        if kat in kategori_modelleri:
            medya_linki = str(model['medya'])
            if "drive.google.com/file/d/" in medya_linki:
                try:
                    dosya_id = medya_linki.split('/d/')[1].split('/')[0]
                    medya_linki = f"https://lh3.googleusercontent.com/d/{dosya_id}"
                except:
                    pass 
            
            kategori_modelleri[kat].append({
                'title': model['baslik'],
                'dosya_adi': model['dosya_adi'],
                'thumbnail': medya_linki 
            })

    print("\nKullanıcı Kategori Sayfaları Oluşturuluyor...")
    for kat_adi, dosya_adi in kullanici_kategorileri.items():
        try:
            sayfa_basligi_tam = f"{kat_adi} (Sizden Gelenler)"
            
            if sayfa_basligi_tam not in kategori_seo_sozluk or len(kategori_seo_sozluk[sayfa_basligi_tam]) < 10:
                print(f"  + Kategori SEO Metni Yazdırılıyor: {sayfa_basligi_tam}")
                yeni_seo = kategori_seo_uret(sayfa_basligi_tam)
                if yeni_seo:
                    kategori_seo_sozluk[sayfa_basligi_tam] = yeni_seo
                    with open(seo_dosyasi, 'w', encoding='utf-8') as f:
                        json.dump(kategori_seo_sozluk, f, ensure_ascii=False, indent=4)
                else:
                    kategori_seo_sozluk[sayfa_basligi_tam] = ""
            
            kat_seo_metni = kategori_seo_sozluk.get(sayfa_basligi_tam, "")
            kat_html = template_index.render(
                is_ana_sayfa=False, 
                sayfa_basligi=f"{kat_adi} (Sizden Gelenler)", 
                videolar=kategori_modelleri[kat_adi], 
                tum_kategoriler=tum_kategoriler,
                kategori_seo_metni=kat_seo_metni
            )
            with open(dosya_adi, 'w', encoding='utf-8') as f:
                f.write(kat_html)
            
            uretilen_sayfalar.append(dosya_adi)
            print(f"  √ {dosya_adi} üretildi. ({len(kategori_modelleri[kat_adi])} model)")
        except Exception as e:
            print(f"! Kullanıcı kategorisi işlenirken hata: {e}")

    print("\nAna sayfa, Sitemap ve Veritabanları oluşturuluyor...")
    
    try:
        index_icerik = template_index.render(
            is_ana_sayfa=True, 
            sayfa_basligi="Ana Sayfa", 
            site_verisi=site_verisi, 
            tum_kategoriler=tum_kategoriler,
            populer_videolar=populer_videolar,  
            son_modeller=son_5_model            
        )
        with open('index.html', 'w', encoding='utf-8') as f: f.write(index_icerik)
    except Exception as e:
        print(f"Ana sayfa üretilirken hata: {e}")
        
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

    # Yapay Zeka Asistan Sayfasını Oluştur
    template_asistan = env.get_template('asistan_sablon.html')
    asistan_icerik = template_asistan.render(tum_kategoriler=tum_kategoriler)
    with open('akilli-asistan.html', 'w', encoding='utf-8') as f: 
        f.write(asistan_icerik)
    uretilen_sayfalar.append('akilli-asistan.html')
    
    uretilen_sayfalar.extend(['hakkimizda.html', 'iletisim.html', 'gizlilik-politikasi.html'])
    sitemap_olustur(uretilen_sayfalar)

    with open('arama_verisi.json', 'w', encoding='utf-8') as f:
        json.dump(list(tum_videolar_arama_icin.values()), f, ensure_ascii=False)
        
    with open('tum_videolar_ham.json', 'w', encoding='utf-8') as f:
        json.dump(tum_videolar_ham, f, ensure_ascii=False)
        
    print("İşlem tamamlandı! Web sitesi oluşturuldu.")

if __name__ == '__main__':
    sayfalari_olustur()
