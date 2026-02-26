#!/bin/bash
echo "🚀 Asilbek Abdurahmonov — o'rnatish boshlandi..."

# Virtual environment
python3 -m venv venv
source venv/bin/activate

# Kutubxonalar
pip install -r requirements.txt

# Migratsiyalar
python manage.py migrate

# Superuser yaratish
echo ""
echo "👤 Admin foydalanuvchi yaratish:"
python manage.py createsuperuser

# Static fayllar
python manage.py collectstatic --no-input

echo ""
echo "✅ Tayyor! Serverni ishga tushirish:"
echo "   source venv/bin/activate"
echo "   python manage.py runserver"
echo ""
echo "🌐 Sayt: http://127.0.0.1:8000"
echo "🔑 Admin kirish: http://127.0.0.1:8000/login/"
