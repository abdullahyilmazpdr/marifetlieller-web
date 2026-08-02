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
# 2. Gemini Anahtarlarını Çekme ve Listeye Çevirme
gemini_keys_metni = os.environ.get('GEMINI_API_KEYS', '')

# Eğer GitHub'dan metin geldiyse, virgüllerden bölüp Python listesine dönüştür
if gemini_keys_metni:
    GEMINI_API_KEYS = gemini_keys_metni.split(',')
else:
    # Eğer bilgisayarınızda test yapıyorsanız ve sistem değişkeni yoksa
    # hata vermemesi için boş liste atayabilir veya geçici test anahtarı yazabilirsiniz.
    GEMINI_API_KEYS = []

aktif_api_indeksi = 0
client = genai.Client(api_key=GEMINI_API_KEYS[aktif_api_indeksi])
SECILEN_MODEL = 'gemini-flash-latest'
AI_KOTALARI_DOLDU = False # Kota dolduğunda hızlı çıkış için bayrak

def onayli_modelleri_cek():
  # Google E-Tablonuzun "Web'de Yayınla" diyerek aldığınız CSV bağlantısı
  csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQkpPlQW7YV4ZgYv4swHZdQxV5NdGhmkxmsTXS2cR2XgV5W7lt9przPz3nuhB4yvg3Wf1-j0jZqdjEu/pub?output=csv"

  try:
    response = requests.get(csv_url)
    response.raise_for_status()

    # CSV verisini oku
    f = io.StringIO(response.content.decode("utf-8"))
    reader = csv.reader(f)

    onayli_liste = []
    basliklar = next(reader)  # İlk satır başlıkları atla

    for satir in reader:
      # Kolon sıralamanıza göre: [ID, Tarih, Yazar, Kategori, Baslik, Makale, Medya, Durum]
      if len(satir) >= 8 and satir[7] == "Onaylandı":
        model_verisi = {
            "id": satir[0],
            "tarih": satir[1],
            "yazar": satir[2],
            "kategori": satir[3],
            "baslik": satir[4],
            "makale": satir[5],
            "medya": satir[6],
            "durum": satir[7],
            # URL uyumlu dosya adı oluşturuyoruz (örn: "boncuklu-oya-123.html")
            "dosya_adi": f"model_{satir[0].lower()}.html",
        }
        onayli_liste.append(model_verisi)

    return onayli_liste
  except Exception as e:
    print(f"E-Tablo okuma hatası: {e}")
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
    
    if AI_KOTALARI_DOLDU:
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
    maksimum_deneme = len(GEMINI_API_KEYS)
    
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

def guvenli_dosya_adi(isim):
    # Türkçe karakterleri İngilizceye çevir
    isim = isim.replace('ı', 'i').replace('İ', 'i').replace('ğ', 'g').replace('Ğ', 'g')
    isim = isim.replace('ü', 'u').replace('Ü', 'u').replace('ş', 's').replace('Ş', 's')
    isim = isim.replace('ö', 'o').replace('Ö', 'o').replace('ç', 'c').replace('Ç', 'c')
    
    # Tüm harfleri küçük yap
    isim = isim.lower()
    
    # Alfasayısal olmayan (boşluk dahil) her şeyi tireye (-) çevir
    isim = re.sub(r'[^a-z0-9]+', '-', isim)
    
    # Baştaki ve sondaki fazlalık tireleri temizle, en fazla 50 karakter al
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
    
    # 2. Robot (Güncelleyici) için Ham Veritabanı
    tum_videolar_ham = []

    listeler = oynatma_listelerini_getir()
    print(f"Sistem Başlatıldı. {len(listeler)} kategori bulundu.\n")
    
    tum_kategoriler = []
    for liste in listeler:
        kat_adi = liste['snippet']['title']
        tum_kategoriler.append({'baslik': kat_adi, 'dosya_adi': f"kategori_{guvenli_dosya_adi(kat_adi)}.html"})

    for index, liste in enumerate(listeler):
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
            dosya_adi = f"video_{video['id']}.html" 
            
            # Güncelleyici Robot İçin Veriyi Kaydet
            tum_videolar_ham.append({
                'id': video['id'],
                'title': video['title'],
                'description': video['description'],
                'thumbnail': video['thumbnail'],
                'kategori_adi': kategori_adi,
                'kategori_dosya_adi': kategori_dosya_adi
            })

            # YAPAY ZEKA KONTROLÜ
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
            
            # HTML içeriği render edilir
            html_icerik = template_video.render(video=video, kategori_adi=kategori_adi, kategori_dosya_adi=kategori_dosya_adi, tum_kategoriler=tum_kategoriler)
            
            # Oluşturulan içerik dosyaya yazdırılır
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

    # 1. E-Tablodan Onaylı Modelleri Çek
    onayli_modeller = onayli_modelleri_cek()

    template_kullanici_model = env.get_template('kullanici_model_sablon.html')

    for model in onayli_modeller:
      # Her model için HTML içeriği üret
      model_html = template_kullanici_model.render(model=model)
      dosya_yolu = os.path.join('', model['dosya_adi'])

      with open(dosya_yolu, 'w', encoding='utf-8') as f:
        f.write(model_html)

      # Google'ın dizine eklemesi için sitemap listesine dahil et
      uretilen_sayfalar.append(model['dosya_adi'])
      print(f"Yayınlanan Model Sayfası Üretildi: {model['dosya_adi']}")

    print("\nAna sayfa, Sitemap ve Veritabanları oluşturuluyor...")
    index_icerik = template_index.render(is_ana_sayfa=True, sayfa_basligi="Ana Sayfa", site_verisi=site_verisi, tum_kategoriler=tum_kategoriler)
    with open('index.html', 'w', encoding='utf-8') as f: f.write(index_icerik)
    sitemap_olustur(uretilen_sayfalar)

    # Giriş Sayfasını Oluştur ve Çıktı Klasörüne Aktar
    template_giris = env.get_template('giris_sablon.html')
    giris_icerik = template_giris.render()
    with open('giris.html', 'w', encoding='utf-8') as f: f.write(giris_icerik)
    uretilen_sayfalar.append('giris.html') # Sitemap'e (Site Haritasına) dahil et

    # Model Gönderme Sayfasını Oluştur
    template_model = env.get_template('model_sablon.html')
    model_icerik = template_model.render(tum_kategoriler=tum_kategoriler)
    with open('model-gonder.html', 'w', encoding='utf-8') as f: 
        f.write(model_icerik)
    uretilen_sayfalar.append('model-gonder.html')

    with open('arama_verisi.json', 'w', encoding='utf-8') as f:
        json.dump(tum_videolar_arama_icin, f, ensure_ascii=False)
        
    with open('tum_videolar_ham.json', 'w', encoding='utf-8') as f:
        json.dump(tum_videolar_ham, f, ensure_ascii=False)
        
    print("İşlem tamamlandı! Web sitesi oluşturuldu.")

if __name__ == '__main__':
    sayfalari_olustur()