# Asilbek Abdurahmonov 🌍📖

> Fikrlar, mulohazalar va hayot haqida shaxsiy blog.

## O'rnatish

### 1. Reponi clone qiling
```bash
git clone https://github.com/username/fikrzone.git
cd fikrzone
```

### 2. Avtomatik o'rnatish
```bash
chmod +x setup.sh
./setup.sh
```

### Yoki qo'lda:

```bash
# Virtual environment
python3 -m venv venv
source venv/bin/activate       # Linux/Mac
venv\Scripts\activate          # Windows

# Kutubxonalar
pip install -r requirements.txt

# .env fayl yarating
cp .env.example .env
# .env ichiga o'z SECRET_KEY ingizni yozing

# Migratsiyalar
python manage.py migrate

# Admin yaratish
python manage.py createsuperuser

# Serverni ishga tushirish
python manage.py runserver
```

## Foydalanish

| URL | Tavsif |
|-----|--------|
| `http://127.0.0.1:8000/` | Bosh sahifa |
| `http://127.0.0.1:8000/login/` | Admin kirish |
| `http://127.0.0.1:8000/write/` | Yangi maqola yozish |
| `http://127.0.0.1:8000/search/` | Qidirish |

## Texnologiyalar

- **Backend:** Django 4.2
- **Frontend:** Bootstrap 5, Vanilla JS
- **Editor:** Quill.js
- **Database:** SQLite
- **Shriftlar:** Syne, Inter, JetBrains Mono

## Litsenziya

MIT
