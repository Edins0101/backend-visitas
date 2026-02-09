# 🚪 Backend de Visitantes y Validación de QR

Backend desarrollado en **Python** usando **FastAPI**, con una arquitectura por capas inspirada en **Hexagonal / Clean Architecture**.

El proyecto se encarga de **leer, interpretar y validar códigos QR** para la gestión de visitantes, manteniendo la lógica de negocio desacoplada y preparada para integraciones externas.

> **Nota importante:**  
> El QR no almacena información sensible.  
> Solo contiene un identificador.  
> La validación real ocurre en la base de datos.

---

## 🎯 Alcance del Proyecto

### ✅ Incluye
- Lectura del contenido textual de un QR
- Extracción de un identificador (`qr_id`)
- Validación del QR contra la base de datos
- Gestión básica de visitantes
- OCR

### ❌ Fuera de alcance
- Reconocimiento facial

---

## 🧱 Arquitectura

Organización basada en responsabilidades claras, siguiendo principios de Clean Architecture.

```text
app/
├── api/                # Capa HTTP (FastAPI)
│   ├── routers/        # Endpoints
│   └── deps.py         # Inyección de dependencias
│
├── application/        # Casos de uso / lógica de aplicación
│   ├── services/       # Servicios
│   └── dtos/           # DTOs (request / response)
│
├── domain/             # Entidades y reglas de negocio
│
├── infrastructure/     # Base de datos e integraciones externas
│
└── main.py             # Punto de entrada
```

### 🏛️ Principios

- **API**: No contiene lógica de negocio
- **Application**: Devuelve las respuestas finales
- **Domain**: No depende de frameworks
- **Infrastructure**: Maneja la base de datos y servicios externos

---

## ⚙️ Requisitos

- Python 3.11.9
- PostgreSQL
- pip

---

## 📦 Instalación

1. **Clonar el repositorio:**
   ```bash
   git clone <url-del-repositorio>
   cd backend-visitas
   ```

2. **Crear entorno virtual:**
   ```bash
   python -m venv .venv
   ```

3. **Activar entorno virtual:**
   - **Windows:**
     ```bash
     py -3.11 -m venv .venv
      .\.venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS:**
     ```bash
     source .venv/bin/activate
     ```

4. **Instalar dependencias:**
   - Base:
     ```bash
     pip install -r requirements/base.txt
     ```
   - OCR (opcional):
     ```bash
     python -m pip install -r requirements/ocr.txt --extra-index-url https://download.pytorch.org/whl/cu121
     ```

---

## 🔐 Variables de Entorno

Crear un archivo `.env` en la raíz del proyecto:

```env
DATABASE_URL=postgresql+psycopg://usuario:password@localhost:5432/midb
EASYOCR_GPU=true // Si tiene grafica
```

> ⚠️ **Importante:** El archivo `.env` no debe subirse al repositorio

---

## 🚀 Ejecución

Desde la raíz del proyecto:

```bash
uvicorn app.main:app --reload
```

- **API:** http://localhost:8000
- **Swagger UI:** http://localhost:8000/docs

---

## 🔁 Endpoints

### Leer contenido de un QR

**`POST /qr/read`**

**Request:**
```json
{
  "raw": "QR:12345"
}
```

**Response:** Devuelve `qr_id` y contenido normalizado

### Validar QR por ID

**`POST /qrs/{qr_id}/validar`**

**Validaciones:**
- Existencia
- Vigencia
- Estado
- Uso previo

---

## 🧪 Pruebas

```bash
pytest
```

---

## 🛑 Consideraciones

- El QR no contiene información sensible y actúa solo como identificador
- La validación real ocurre en la base de datos
- El reconocimiento facial es un servicio externo
- El módulo de llamadas telefónicas se ejecuta dentro del backend (FastAPI)

---

## 📌 Tecnologías

- FastAPI
- SQLAlchemy (sync)
- PostgreSQL
- Pydantic
- Uvicorn

---

## Twilio (llamadas)

El backend incluye endpoints para realizar llamadas con Twilio.

### Variables de entorno

Agregar en `.env`:

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+15551234567
BASE_URL=https://your-public-url.example.com
```

`BASE_URL` debe ser un URL publico accesible por Twilio (por ejemplo usando ngrok).

### Endpoints

- `POST /api/call`
- `POST /twilio/voice`
- `POST /twilio/voice/handle-input`

Body ejemplo:

```json
{
  "to": "+593979684121",
  "residentName": "Juan Perez",
  "visitorName": "Carlos Lopez",
  "plate": "ABC-1234"
}
```

---

## 👥 Contribuidores

- Edinson Ramirez
- Pierre Orellana
