# Use official lightweight Python image
FROM python:3.11-slim

# Avoid .pyc creation + enforce unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies required for pillow/reportlab fonts
RUN apt-get update && apt-get install -y \
    libfreetype6 \
    liblcms2-2 \
    libjpeg62-turbo \
    libpng16-16 \
    libtiff6 \
    libwebp7 \
    libharfbuzz0b \
    libfribidi0 \
    && rm -rf /var/lib/apt/lists/*

# Set app directory
WORKDIR /app

# Copy requirements first for better Docker caching
COPY requirements.txt .

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Copy full source code
COPY . .

# Expose Streamlit default port
EXPOSE 8501

# Run the Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
