# 🚀 MercadoPago Enterprise

> **Sistema empresarial de pagos con auditoría crítica, arquitectura multi-tenant y seguridad reforzada para integraciones GoHighLevel**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-orange.svg)](https://sqlalchemy.org)
[![Security](https://img.shields.io/badge/Security-Enterprise-red.svg)](https://owasp.org)
[![Multi-tenant](https://img.shields.io/badge/Architecture-Multi--tenant-purple.svg)](https://en.wikipedia.org/wiki/Multitenancy)

---

## 📋 Descripción

**MercadoPago Enterprise** es una plataforma de procesamiento de pagos de nivel empresarial diseñada específicamente para agencias y empresas SaaS que requieren integración segura con MercadoPago y GoHighLevel. Ofrece arquitectura multi-tenant, auditoría crítica completa y simulación de pagos para desarrollo.

### 🎯 Características Principales

- **🔐 Auditoría Crítica**: Sistema completo de trazabilidad con blockchain-level audit trails
- **🏗️ Multi-tenant**: Aislamiento completo de datos entre clientes
- **🔄 Simulación de Pagos**: Entorno de desarrollo sin transacciones reales
- **📊 Dashboard NOC**: Centro de comando con métricas en tiempo real
- **🛡️ Seguridad Reforzada**: Preparado para auditorías con Kali Linux
- **🔗 Integración GoHighLevel**: OAuth automático y tagging de contactos

---

## 🛠️ Tecnologías

### Backend
- **[FastAPI](https://fastapi.tiangolo.com/)** - Framework web moderno y rápido
- **[SQLAlchemy](https://sqlalchemy.org/)** - ORM avanzado con soporte multi-tenant
- **[Pydantic](https://pydantic.dev/)** - Validación de datos con type hints
- **[SQLite](https://sqlite.org/)** - Base de datos embebida (configurable a PostgreSQL)

### Frontend
- **[Tailwind CSS](https://tailwindcss.com/)** - Framework CSS utility-first
- **[Chart.js](https://chartjs.org/)** - Visualización de datos interactiva
- **[Font Awesome](https://fontawesome.com/)** - Iconografía profesional

### Seguridad & Auditoría
- **HMAC SHA-256** - Validación de webhooks
- **OAuth 2.0** - Autenticación segura con MercadoPago
- **Correlation IDs** - Trazabilidad completa de requests
- **Blockchain-style Audit** - Cadena inmutable de eventos

---

## 🚀 Instalación y Configuración

### Prerrequisitos

```bash
# Python 3.8 o superior
python --version

# Git para clonar el repositorio
git --version
```

### 1. Clonar el Repositorio

```bash
git clone https://github.com/tu-usuario/mercadopago-enterprise.git
cd mercadopago-enterprise
```

### 2. Crear Entorno Virtual

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Configuración de Variables de Entorno

```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar .env con tus credenciales
```

#### Variables Requeridas:

```env
# MercadoPago
MP_ACCESS_TOKEN=tu_access_token_aqui
MP_WEBHOOK_SECRET=tu_webhook_secret_aqui
MP_CLIENT_ID=tu_client_id_oauth
MP_CLIENT_SECRET=tu_client_secret_oauth

# GoHighLevel
GHL_API_KEY=tu_ghl_api_key_aqui

# Administración
ADMIN_API_KEY=tu_admin_token_seguro

# Base de Datos (opcional)
DATABASE_URL=sqlite:///./mercadopago_enterprise.db
```

### 5. Inicializar Base de Datos

```bash
# Ejecutar script de inicialización
python scripts/init_db.py
```

### 6. Ejecutar la Aplicación

```bash
# Modo desarrollo
python main.py

# O usando uvicorn directamente
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

La aplicación estará disponible en: **http://localhost:8003**

---

## 📊 Dashboards y Interfaces

### 🎛️ Dashboard NOC (Centro de Comando)
- **URL**: `http://localhost:8003/dashboard`
- **Funciones**: Métricas en tiempo real, alertas de seguridad, estado del sistema
- **Acceso**: Requiere token de administrador

### 👤 Dashboard Cliente
- **URL**: `http://localhost:8003/dashboard/client/{client_id}`
- **Funciones**: Métricas por cliente, generación de pagos, estado GHL
- **Acceso**: Específico por cliente

### 🔗 Endpoints Principales

```bash
# Crear pago
POST /api/v1/payments/create

# Procesar webhook
POST /api/v1/webhooks/mercadopago

# OAuth MercadoPago
GET /oauth/authorize

# Métricas dashboard
GET /api/v1/dashboard/overview
```

---

## 🔐 Seguridad

### Características de Seguridad Implementadas

#### 🛡️ Validación de Webhooks
- **HMAC SHA-256** para verificar autenticidad
- **Replay attack protection** con timestamps
- **Idempotencia** para evitar procesamiento duplicado

#### 📋 Auditoría Crítica
- **Trazabilidad completa** de todas las operaciones
- **Blockchain-style hashing** para inmutabilidad
- **Correlation IDs** para seguimiento de requests
- **Metadatos de seguridad** (IP, User-Agent, timestamps)

#### 🔒 Aislamiento Multi-tenant
- **Separación completa** de datos entre clientes
- **OAuth independiente** por cliente
- **Dashboards aislados** sin cross-contamination

#### 🚨 Sistema de Alertas
- **Detección de anomalías** en tiempo real
- **Alertas de seguridad** automáticas
- **Monitoreo de brute force** attacks
- **Notificaciones** vía Slack/Email

### 🔍 Preparado para Auditorías

El sistema está diseñado para superar auditorías de seguridad con herramientas como:
- **Kali Linux** - Penetration testing
- **OWASP ZAP** - Security scanning
- **Burp Suite** - Web application security
- **Nmap** - Network discovery

---

## 🧪 Simulación de Pagos

### Modo Desarrollo

El sistema incluye un **simulador de pagos** completo para desarrollo sin transacciones reales:

```bash
# Generar link de pago simulado
POST /api/v1/payments/create
{
  "customer_email": "test@example.com",
  "amount": 100.00,
  "ghl_contact_id": "contact_123",
  "description": "Pago de prueba"
}

# Simular aprobación
GET /simulate-payment/{preference_id}
```

### Características del Simulador

- ✅ **Links de pago funcionales** sin cargos reales
- ✅ **Webhooks simulados** con datos realistas
- ✅ **Integración GHL simulada** con tagging automático
- ✅ **Dashboards con datos de prueba** para demos
- ✅ **Flujo completo** desde generación hasta confirmación

---

## 📁 Arquitectura del Proyecto

```
mercadopago-enterprise/
├── app/                          # Aplicación principal
│   ├── api/                      # Endpoints FastAPI
│   │   ├── payments.py           # Rutas de pagos
│   │   ├── webhooks.py           # Rutas de webhooks
│   │   ├── oauth.py              # Rutas OAuth
│   │   ├── dashboard.py          # Rutas dashboard
│   │   ├── admin.py              # Rutas administrativas
│   │   └── security.py           # Rutas de seguridad
│   ├── core/                     # Lógica central
│   │   ├── config.py             # Configuración
│   │   ├── database.py           # Conexión DB
│   │   ├── models.py             # Modelos SQLAlchemy
│   │   ├── schemas.py            # Esquemas Pydantic
│   │   ├── security.py           # Utilidades seguridad
│   │   └── middleware.py         # Middleware personalizado
│   ├── services/                 # Servicios externos
│   │   ├── payment_service.py    # Lógica de pagos
│   │   ├── webhook_service.py    # Procesamiento webhooks
│   │   ├── oauth_service.py      # Manejo OAuth
│   │   ├── audit_service.py      # Auditoría crítica
│   │   ├── alert_service.py      # Sistema de alertas
│   │   └── notification_service.py # Notificaciones
│   ├── static/                   # Archivos estáticos
│   │   ├── dashboard.html        # Dashboard NOC
│   │   └── client_dashboard.html # Dashboard cliente
│   └── main.py                   # Aplicación FastAPI
├── scripts/                      # Scripts de utilidad
│   ├── init_db.py               # Inicializar DB
│   ├── daily_reconcile.py       # Reconciliación diaria
│   └── setup_notifications.py   # Configurar notificaciones
├── tests/                        # Tests automatizados
├── docs/                         # Documentación
├── logs/                         # Logs del sistema
├── reports/                      # Reportes generados
├── requirements.txt              # Dependencias Python
├── .env.example                  # Plantilla de configuración
├── .gitignore                    # Archivos ignorados
└── README.md                     # Este archivo
```

---

## 🔧 Scripts de Utilidad

### Inicialización

```bash
# Inicializar base de datos
python scripts/init_db.py

# Configurar notificaciones
python scripts/setup_notifications.py

# Crear cliente de prueba
python scripts/create_test_client.py
```

### Mantenimiento

```bash
# Reconciliación diaria
python scripts/daily_reconcile.py

# Resolver alertas
python scripts/resolve_alerts.py

# Archivar logs a S3
python scripts/archive_logs_to_s3.py
```

### Monitoreo

```bash
# Verificar auditoría
python scripts/check_audit_trail.py

# Monitoreo de alertas
python scripts/start_alert_monitoring.py
```

---

## 🧪 Testing

### Ejecutar Tests

```bash
# Todos los tests
python -m pytest tests/

# Tests específicos
python -m pytest tests/test_payments.py
python -m pytest tests/test_security.py
python -m pytest tests/test_webhooks.py
```

### Tests de Seguridad

```bash
# Test de penetración básico
python tests/test_security.py

# Verificar webhooks
python tests/test_webhook_ghl.py

# Test OAuth
python tests/test_oauth.py
```

---

## 📈 Monitoreo y Métricas

### Métricas Disponibles

- **💰 Volumen de transacciones** por hora/día/mes
- **✅ Tasa de éxito** de pagos procesados
- **⚡ Tiempo de respuesta** de webhooks
- **🚨 Alertas de seguridad** activas
- **👥 Actividad por cliente** multi-tenant
- **🔗 Estado de integraciones** (GHL, MP)

### Alertas Automáticas

- **Brute force attacks** (3+ intentos fallidos)
- **Discrepancias de montos** en pagos
- **Webhooks fallidos** o rechazados
- **Tokens OAuth expirados**
- **Errores de sistema** críticos

---

## 🤝 Contribución

### Desarrollo Local

1. Fork del repositorio
2. Crear rama feature: `git checkout -b feature/nueva-funcionalidad`
3. Commit cambios: `git commit -am 'Agregar nueva funcionalidad'`
4. Push a la rama: `git push origin feature/nueva-funcionalidad`
5. Crear Pull Request

### Estándares de Código

- **Type hints** en todas las funciones
- **Docstrings** para clases y métodos públicos
- **Tests** para nueva funcionalidad
- **Logging** apropiado para debugging
- **Validación** de entrada con Pydantic

---

## 📄 Licencia

Este proyecto está bajo licencia empresarial. Ver archivo `LICENSE` para más detalles.

---

## 🆘 Soporte

### Documentación Adicional

- **[Guía de Seguridad](docs/SECURITY_FEATURES.md)** - Características de seguridad detalladas
- **[Manual de Instalación](QUICKSTART.md)** - Guía rápida de inicio
- **[Índice de Documentación](INDEX.md)** - Todos los documentos disponibles

### Contacto

- **Issues**: [GitHub Issues](https://github.com/tu-usuario/mercadopago-enterprise/issues)
- **Documentación**: Ver carpeta `docs/`
- **Email**: soporte@tu-empresa.com

---

## 🏆 Características Destacadas

### ✨ Lo que nos diferencia

- **🔐 Seguridad de nivel bancario** con auditoría completa
- **🏗️ Arquitectura multi-tenant real** con aislamiento total
- **🧪 Simulador completo** para desarrollo sin riesgos
- **📊 Dashboards profesionales** con métricas en tiempo real
- **🛡️ Preparado para auditorías** de seguridad
- **🔄 Integración nativa** con GoHighLevel
- **⚡ Performance optimizado** para alta concurrencia
- **📈 Escalabilidad empresarial** probada

### 🎯 Casos de Uso Ideales

- **Agencias de Marketing** con múltiples clientes
- **Empresas SaaS** que necesitan procesamiento de pagos
- **Consultores GoHighLevel** que requieren integración MP
- **Empresas** que necesitan auditoría completa de transacciones
- **Desarrolladores** que buscan una base sólida para pagos

---

*Desarrollado con ❤️ para la comunidad empresarial que requiere soluciones de pago robustas y seguras.*