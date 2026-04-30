FROM python:3.12-slim

LABEL maintainer="attendance-variation-system"
LABEL description="Attendance Report Variation System – production CLI"

# -----------------------------------------------------------------------
# System dependencies
# -----------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-heb \
        poppler-utils \
        libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------------------
# Python environment
# -----------------------------------------------------------------------
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------
# Application code
# -----------------------------------------------------------------------
COPY . .

# Default output directory inside the container (mount a volume here)
RUN mkdir -p /data/output

# -----------------------------------------------------------------------
# Expose web interface port
# -----------------------------------------------------------------------
EXPOSE 5000

# -----------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------
# Usage:
#   docker run --rm \
#     -v /host/input:/data/input:ro \
#     -v /host/output:/data/output \
#     attendance-variation \
#     /data/input/report.pdf -o /data/output --seed 12345
#
# CLI mode (default): python main.py --help
# Web mode:           docker run -p 5000:5000 <image> web
ENTRYPOINT ["python", "main.py"]
CMD ["--help"]
