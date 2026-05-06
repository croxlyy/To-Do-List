from flask import Flask, render_template, request, redirect
import sqlite3
import uuid
from datetime import datetime

app = Flask(__name__)

def gorev_analizi(baslik):
    baslik_kucuk = baslik.lower()
    
    if any(kelime in baslik_kucuk for kelime in ["toplantı", "sunum", "müşteri", "rapor", "proje", "ofis", "iş"]):
        kategori = "İş"
    elif any(kelime in baslik_kucuk for kelime in ["ödeme", "fatura", "para", "maaş", "kredi", "taksit", "hesap"]):
        kategori = "Finans"
    elif any(kelime in baslik_kucuk for kelime in ["ödev", "sınav", "ders", "okul", "çalış", "slayt", "not"]):
        kategori = "Eğitim"
    elif any(kelime in baslik_kucuk for kelime in ["doktor", "ilaç", "hastane", "sağlık", "spor", "diyet"]):
        kategori = "Sağlık"
    elif any(kelime in baslik_kucuk for kelime in ["market", "al", "sipariş", "alışveriş", "bakkal"]):
        kategori = "Alışveriş"
    else:
        kategori = "Kişisel"

    seviye_5_kriz = [
        "acil", "hemen", "bugün", "yarın", "son gün", "kriz", "hastane", "doktor", 
        "fatura", "ceza", "vergi", "uyarı", "tehlike", "ameliyat", "kaza", "mahkeme", 
        "iptal", "gecikmiş", "şart", "mecburi", "acil servis", "polis", "imdat", "kapanıyor"
    ]
    seviye_4_yuksek = [
        "toplantı", "proje", "müşteri", "ödeme", "önemli", "sunum", "randevu", 
        "mülakat", "sözleşme", "imza", "teslim", "vize", "uçuş", "bilet", "banka", 
        "kredi", "borç", "onay", "yönetim", "patron", "müdür", "sınav", "final"
    ]
    seviye_3_orta = [
        "ödev", "çalış", "ders", "alışveriş", "market", "spor", "antrenman", 
        "tamir", "bakım", "kargo", "sipariş", "tesisat", "muayene", "veteriner", 
        "pazar", "manav", "kasap", "eczane", "kuaför", "berber", "kurs"
    ]
    seviye_2_rutin = [
        "temizlik", "ara", "mail", "not", "düzenle", "çamaşır", "bulaşık", "ütü", 
        "yemek", "mesaj", "e-posta", "toparla", "yedekle", "güncelle", "planla", 
        "oku", "izle", "yürüyüş", "çöp", "fırın", "süpür", "sil"
    ]

    if any(kelime in baslik_kucuk for kelime in seviye_5_kriz):
        onem = 5
    elif any(kelime in baslik_kucuk for kelime in seviye_4_yuksek):
        onem = 4
    elif any(kelime in baslik_kucuk for kelime in seviye_3_orta):
        onem = 3
    elif any(kelime in baslik_kucuk for kelime in seviye_2_rutin):
        onem = 2
    else:
        onem = 1  

    return kategori, onem

def init_db():
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id TEXT PRIMARY KEY, 
                  title TEXT, 
                  deadline TEXT, 
                  importance INTEGER, 
                  category TEXT,
                  completed BOOLEAN)''')
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def index():
    conn = sqlite3.connect('tasks.db')
    conn.row_factory = sqlite3.Row 
    c = conn.cursor()
    c.execute("SELECT * FROM tasks")
    raw_tasks = c.fetchall()
    conn.close()

    tasks = []
    # SAAT FARKINI YOK ETMEK İÇİN SADECE TARİHİ (.date()) ALIYORUZ
    today = datetime.today().date() 

    for row in raw_tasks:
        task = dict(row)
        
        try:
            deadline = datetime.strptime(task["deadline"], "%Y-%m-%d").date()
        except ValueError:
            deadline = datetime.strptime(task["deadline"], "%d.%m.%Y").date()
            
        days_left = (deadline - today).days

        # GÖREV SÜRESİ KONTROLLERİ (Yeni Mantık)
        if days_left < 0:
            task["days_display"] = "⏳ Zamanı Geçti"
            task["is_overdue"] = True
            task["priority"] = -100 # En alta düşmesi için negatif puan
        elif days_left == 0:
            task["days_display"] = "🚨 Bugün Doluyor!"
            task["is_overdue"] = False
            task["priority"] = task["importance"] * 2 # Bugüne özel aciliyet artışı
        else:
            task["days_display"] = f"{days_left} gün kaldı"
            task["is_overdue"] = False
            task["priority"] = round(task["importance"] / (days_left + 1), 2)

        task["days_left"] = days_left 
        tasks.append(task)

    tasks.sort(key=lambda x: x["priority"], reverse=True)
    return render_template("index.html", tasks=tasks)

@app.route("/add", methods=["POST"])
def add_task():
    title = request.form["title"]
    deadline = request.form["deadline"]
    task_id = str(uuid.uuid4()) 
    predicted_category, predicted_importance = gorev_analizi(title)
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("INSERT INTO tasks (id, title, deadline, importance, category, completed) VALUES (?, ?, ?, ?, ?, ?)",
              (task_id, title, deadline, predicted_importance, predicted_category, False))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/complete/<task_id>")
def complete_task(task_id):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("UPDATE tasks SET completed = ? WHERE id = ?", (True, task_id))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/delete/<task_id>")
def delete_task(task_id):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)