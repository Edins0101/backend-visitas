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

### ❌ Fuera de alcance
- OCR avanzado
- Reconocimiento facial
- Llamadas telefónicas

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

- Python 3.10 o superior
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
     .venv\Scripts\activate
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
     pip install -r requirements/ocr.txt
     ```

---

## 🔐 Variables de Entorno

Crear un archivo `.env` en la raíz del proyecto:

```env
DATABASE_URL=postgresql+psycopg://usuario:password@localhost:5432/midb
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
- El módulo de llamadas telefónicas no está implementado

---

## 📌 Tecnologías

- FastAPI
- SQLAlchemy (sync)
- PostgreSQL
- Pydantic
- Uvicorn

---

## 👥 Contribuidores

- Edinson Ramirez
- Pierre Orellana
