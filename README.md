# SmartCapital 360° 🏢
**Sistema Inteligente de Control de Accesos**  
Proyecto: Gerencia de Proyectos — Politécnico Grancolombiano  
Estudiante: Maria Del Mar Artunduaga Artunduaga

---

## Demo en línea
> Agrega aquí el link de Render una vez desplegado

---

## Credenciales de prueba

| Usuario | Email | Contraseña | Rol |
|---------|-------|------------|-----|
| Admin Sistema | admin@smartcapital.co | admin123 | Administrador |
| Carlos Rodríguez | carlos.rodriguez@smartcapital.co | emp123 | Empleado |
| Ana Martínez | ana.martinez@smartcapital.co | emp123 | Directivo |
| Pedro Gómez | pedro.gomez@smartcapital.co | seg123 | Seguridad |

---

## Stack Tecnológico

- **Backend:** Python + Flask
- **Base de datos:** SQLite
- **Frontend:** HTML + Jinja2 + Bootstrap
- **Servidor producción:** Gunicorn

---

## Estructura del proyecto

```
smartcapital360/
├── backend/
│   ├── app.py          # Aplicación Flask principal
│   └── db/
│       └── smartcapital.db  # Base de datos SQLite
├── frontend/
│   └── templates/      # Plantillas HTML (Jinja2)
├── requirements.txt    # Dependencias Python
├── Procfile            # Comando de inicio para Render
└── render.yaml         # Configuración de Render
```

---

##  Correr localmente

```bash
# 1. Clonar el repositorio
git clone https://github.com/delmar911/smartcapital360-GP.git
cd smartcapital360

# 2. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Iniciar servidor
cd backend
python app.py
```

Abrir en el navegador: http://localhost:5001

---

## ☁️ Despliegue en Render.com

1. Subir este repositorio a GitHub
2. Ir a [render.com](https://render.com) → **New Web Service**
3. Conectar el repositorio de GitHub
4. Render detecta automáticamente la configuración con `render.yaml`
5. Hacer clic en **Deploy**

