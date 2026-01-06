# Backend de Visitantes y Validación de QR

Backend desarrollado en **Python** usando **FastAPI**, con una arquitectura por capas inspirada en **Hexagonal / Clean Architecture**.

El alcance actual del proyecto se centra en:
- Lectura del contenido textual de un QR
- Extracción de un identificador (`qr_id`)
- Validación del QR por ID contra la base de datos
- Gestión básica de visitantes

Módulos como **OCR avanzado**, **reconocimiento facial** y **llamadas telefónicas** se consideran integraciones externas o fuera del alcance actual.

---

## 🧱 Arquitectura

El proyecto está organizado por responsabilidades.

app/
├── api/ # Capa HTTP (FastAPI)
│ ├── routers/ # Endpoints
│ └── deps.py # Inyección de dependencias
│
├── application/ # Lógica de aplicación
│ ├── services/ # Servicios / casos de uso
│ └── dtos/ # DTOs de request y response
│
├── domain/ # Reglas de negocio y entidades
│
├── infrastructure/ # Base de datos e integraciones externas
│
└── main.py # Punto de entrada de la aplicación


### Principios
- La API no contiene lógica de negocio
- La capa application devuelve respuestas finales
- El dominio no depende de frameworks
- La infraestructura maneja DB y servicios externos

---

## ⚙️ Requisitos

- Python 3.10 o superior
- PostgreSQL
- pip

---

## 📦 Instalación

### 1. Clonar el repositorio
```bash
git clone <url-del-repositorio>
cd backend-visitas
2. Crear entorno virtual
bash

python -m venv .venv
Activar entorno:

Windows

bash

.venv\Scripts\activate
Linux / macOS

bash

source .venv/bin/activate
3. Instalar dependencias
Dependencias principales:

bash

pip install -r requirements/base.txt
OCR (opcional):

bash
pip install -r requirements/ocr.txt
🔐 Variables de entorno
Crear un archivo .env en la raíz del proyecto:

env
DATABASE_URL=postgresql+psycopg://usuario:password@localhost:5432/midb
El archivo .env no debe subirse al repositorio.

🚀 Ejecución
Desde la raíz del proyecto:

bash
uvicorn app.main:app --reload
La aplicación estará disponible en:

API: http://localhost:8000

Documentación Swagger: http://localhost:8000/docs

🔁 Endpoints disponibles
Leer contenido de un QR
arduino

POST /qr/read
Request:

json

{
  "raw": "QR:12345"
}
Response:

json

{
  "success": true,
  "message": "QR leído correctamente",
  "data": {
    "qr_id": 12345,
    "raw_normalized": "QR:12345"
  },
  "error": null
}
Validar QR por ID
bash

POST /qrs/{qr_id}/validar
Valida:

existencia del QR

vigencia

estado

uso previo

🧪 Pruebas
bash

pytest
🛑 Consideraciones
El QR no contiene información sensible

El QR solo actúa como identificador

La validación real ocurre en la base de datos

El reconocimiento facial se consume como servicio externo

El módulo de llamadas telefónicas no está implementado

📌 Tecnologías
FastAPI

SQLAlchemy (sync)

PostgreSQL

Pydantic

Uvicorn