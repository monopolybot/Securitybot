FROM python:3.9-slim

# تثبيت مكتبات النظام اللازمة لمعالجة الصور
RUN apt-get update && apt-get install -y \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# نسخ الملفات
COPY . .

# تثبيت المكتبات البرمجية (أضفنا Pillow هنا لسرعة التشغيل)
RUN pip install --no-cache-dir telethon Pillow

# إنشاء مجلد البيانات والتأكد من صلاحياته (لحل مشكلة التخزين صفر)
RUN mkdir -p /app/data && chmod 777 /app/data

CMD ["python", "main.py"]
