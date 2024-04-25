from flask import Flask, render_template, request, send_file
import requests
from bs4 import BeautifulSoup
import re
from pymongo import MongoClient

app = Flask(__name__)

client = MongoClient("mongodb+srv://grknclf1907:12345@gcveri.2nmlzts.mongodb.net/")
db = client["Makaleler"]
collection = db["MakaleTablosu"]

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        anahtar_kelime = request.form["anahtar_kelime"]
        makaleler = []

        url = f"https://dergipark.org.tr/tr/search?q={anahtar_kelime}"
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            makaleler_html = soup.find_all('h5', class_='card-title')

            if makaleler_html:
                for makale_html in makaleler_html[:10]:
                    makale = {
                        "baslik": makale_html.find_next('a').text.strip(),
                        "link": makale_html.find_next('a')['href'],
                        "pdf_link": pdf_linki_getir(makale_html.find_next('a')['href'])  # PDF linkini ekleyelim

                    }
                    makaleler.append(makale)

                    makale_linki = makale["link"]
                    makale_bilgileri = makale_bilgilerini_getir(makale_linki)
                    makale_bilgilerini_veritabanina_ekle(makale_bilgileri)

        return render_template("index.html", makaleler=makaleler)

    return render_template("index.html")

@app.route("/makale/<path:makale_linki>")
def makale_detay(makale_linki):
    makale_bilgileri = makale_bilgilerini_getir(makale_linki)
    return render_template("makale_detay.html", makale_bilgileri=makale_bilgileri)

@app.route("/veritabani_goster")
def veritabani():
    makale_belgeleri = collection.find({}, {"_id": 0})

    makaleler = list(makale_belgeleri)

    return render_template("veritabani.html", makaleler=makaleler)


@app.route("/pdf_indir", methods=["GET"])
def pdf_indir():
    pdf_link = request.args.get("pdf_link")
    if pdf_link:
        response = requests.get(pdf_link)
        if response.status_code == 200:
            return send_file(response.content, as_attachment=True)
    return "PDF dosyası indirilemedi."

def makale_bilgilerini_getir(makale_linki):
    response = requests.get(makale_linki)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        bilgiler = {}

        baslik_bulunan = soup.find('h3', class_='article-title')
        bilgiler['baslik'] = baslik_bulunan.text.strip() if baslik_bulunan else "Bilgi bulunamadı."

        yazar_bulunan = soup.find('a', class_='is-user')
        bilgiler['yazar'] = yazar_bulunan.text.strip() if yazar_bulunan else "Bilgi bulunamadı."

        tarih_bulunan = soup.find('table', class_='record_properties table')
        bilgiler['tarih'] = tarih_bulunan.find_all('td')[3].text.strip() if tarih_bulunan else "Bilgi bulunamadı."

        yayinci_bulunan = soup.find('h1', id='journal-title')
        bilgiler['yayinci'] = yayinci_bulunan.text.strip() if yayinci_bulunan else "Bilgi bulunamadı."

        bilgiler['yayin_turu'] = "Makale"

        anahtar_kelimeler_bulunan = soup.find('div', class_='article-keywords data-section')
        bilgiler['anahtar_kelimeler'] = anahtar_kelimeler_bulunan.text.strip() if anahtar_kelimeler_bulunan else "Bilgi bulunamadı."

        ozet_bulunan = soup.find('div', class_='article-abstract data-section')
        bilgiler['ozet'] = ozet_bulunan.find('p').text.strip() if ozet_bulunan else "Bilgi bulunamadı."

        referanslar_bulunan = soup.find('div', class_='article-citations data-section')
        if referanslar_bulunan:
            referanslar = []
            for referans in referanslar_bulunan.find_all('ul', class_='fa-ul'):
                for li in referans.find_all('li'):
                    referanslar.append(li.text.strip())
            bilgiler['referanslar'] = referanslar
            bilgiler['alinti_sayisi'] = len(referanslar)
        else:
            bilgiler['referanslar'] = ["Referans bulunamadı."]
            bilgiler['alinti_sayisi'] = 0

        doi_bulunan = soup.find('a', href=re.compile(r'https://doi.org/'))
        bilgiler['doi'] = doi_bulunan['href'] if doi_bulunan else "DOİ numarası bulunamadı."

        bilgiler['url'] = makale_linki

        pdf_link_bulunan = soup.find('a', class_='btn.btn-sm.float-left.article-tool.pdf.d-flex.align-items-center')
        if pdf_link_bulunan:
            bilgiler['pdf_link'] = pdf_link_bulunan['href']
        else:
            bilgiler['pdf_link'] = "PDF indirme linki bulunamadı."

        return bilgiler
    else:
        return "Makale bilgileri alınamadı."


def makale_bilgilerini_veritabanina_ekle(bilgiler):
    collection.insert_one(bilgiler)
def pdf_linki_getir(makale_linki):
    response = requests.get(makale_linki)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        pdf_linki = soup.find('a', class_='btn btn-sm float-left article-tool pdf d-flex align-items-center')['href']
        if pdf_linki.startswith("/"):
            pdf_linki = "https://dergipark.org.tr" + pdf_linki
        return pdf_linki
    else:
        return "PDF indirme linki bulunamadı."

if __name__ == "__main__":
    app.run(debug=True)