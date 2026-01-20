# 📁 Estructura del Proyecto

## Organización Final

```
mercadopago-enterprise/
│
├── 📄 README.md                    # Documentación principal
├── 📄 QUICKSTART.md                # Guía de inicio rápido
├── 📄 requirements.txt             # Dependencias Python
├── 📄 .env.example                 # Ejemplo de configuración
├── 📄 .env                         # Configuración (no commitear)
├── 📄 .gitignore                   # Archivos ignorados por Git
│
├── 🐍 main.py                      # API principal (FastAPI)
├── 🐍 models.py                    # Modelos de base de datos
├── 🗄️ mercadopago_enterprise.db   # Base de datos SQLite
│
├── 📂 scripts/                     # Scripts de utilidad
│   ├── init_db.py                 # Inicializar BD
│   ├── recreate_db.py             # Recrear BD desde cero
│   ├── update_db.py               # Actualizar esquema
│   ├── force_approve.py           # Aprobar pagos (con emojis)
│   └── force_approve_simple.py    # Aprobar pagos (sin emojis)
│
├── 📂 tests/                       # Tests y verificación
│   ├── test_quick_payment.py      # Test rápido MVP
│   ├── test_security.py           # Tests de seguridad
│   ├── test_oauth.py              # Tests OAuth
│   ├── test_webhook_ghl.py        # Test puente GHL
│   ├── test_ghl_bridge.py         # Test completo
│   ├── test_token.py              # Test de tokens
│   └── verify_payment.py          # Verificar pagos
│
└── 📂 docs/                        # Documentación detallada
    ├── SECURITY_FEATURES.md       # Características de seguridad
    ├── MVP_DIA1_COMPLETADO.md     # Documentación MVP
    ├── DIA2_COMPLETADO.md         # Sistema de webhooks
    ├── PUENTE_GHL_VERIFICADO.md   # Integración GHL
    └── CHANGELOG_OAUTH.md         # Changelog OAuth
```

## 🎯 Archivos Principales

### Core del Sistema
- **main.py** - API REST con FastAPI, endpoints, servicios
- **models.py** - Modelos SQLAlchemy, tablas de BD

### Configuración
- **.env** - Variables de entorno (secreto)
- **.env.example** - Plantilla de configuración
- **requirements.txt** - Dependencias del proyecto

### Documentación
- **README.md** - Documentación completa del proyecto
- **QUICKSTART.md** - Guía de inicio rápido
- **docs/** - Documentación técnica detallada

## 🛠️ Scripts de Utilidad

| Script | Propósito | Uso |
|--------|-----------|-----|
| `init_db.py` | Inicializar BD primera vez | `python scripts/init_db.py` |
| `recreate_db.py` | Recrear BD desde cero | `python scripts/recreate_db.py` |
| `update_db.py` | Actualizar esquema BD | `python scripts/update_db.py` |
| `force_approve.py` | Aprobar pagos manualmente | `python scripts/force_approve.py <id>` |
| `force_approve_simple.py` | Aprobar pagos (Windows) | `python scripts/force_approve_simple.py <id>` |

## 🧪 Tests Disponibles

| Test | Propósito | Uso |
|------|-----------|-----|
| `test_quick_payment.py` | Verificar endpoint de pagos | `python tests/test_quick_payment.py` |
| `test_security.py` | Tests de seguridad completos | `python tests/test_security.py` |
| `test_oauth.py` | Tests de flujo OAuth | `python tests/test_oauth.py` |
| `test_webhook_ghl.py` | Verificar puente GHL | `python tests/test_webhook_ghl.py` |
| `test_ghl_bridge.py` | Test completo del flujo | `python tests/test_ghl_bridge.py` |
| `test_token.py` | Verificar tokens | `python tests/test_token.py` |
| `verify_payment.py` | Ver estado de pago | `python tests/verify_payment.py <id>` |

## 📚 Documentación Técnica

| Documento | Contenido |
|-----------|-----------|
| `SECURITY_FEATURES.md` | Características de seguridad enterprise |
| `MVP_DIA1_COMPLETADO.md` | Documentación del MVP y Día 1 |
| `DIA2_COMPLETADO.md` | Sistema de webhooks y validaciones |
| `PUENTE_GHL_VERIFICADO.md` | Integración con GoHighLevel |
| `CHANGELOG_OAUTH.md` | Changelog de implementación OAuth |

## 🗄️ Base de Datos

### Tablas Principales

1. **payments** - Pagos y transacciones
   - Datos del pago
   - Estado y procesamiento
   - Relación con cuenta OAuth

2. **mercadopago_accounts** - Cuentas OAuth
   - Tokens de acceso
   - Tokens de renovación
   - Expiración y gestión

3. **audit_logs** - Auditoría
   - Todas las acciones del sistema
   - Trazabilidad completa
   - Correlation IDs

4. **security_alerts** - Alertas de Seguridad
   - Alertas automáticas
   - Clasificación por severidad
   - Gestión de resolución

5. **webhook_logs** - Logs de Webhooks
   - Webhooks recibidos
   - Validación de firma
   - Estado de procesamiento

## 🔄 Flujo de Trabajo

### Desarrollo
1. Editar código en `main.py` o `models.py`
2. Ejecutar tests: `python tests/test_quick_payment.py`
3. Verificar logs del servidor
4. Iterar

### Testing
1. Crear pago: `POST /payments/create`
2. Aprobar: `python scripts/force_approve_simple.py <id>`
3. Verificar: `python tests/verify_payment.py <id>`
4. Ver auditoría: `GET /audit/logs`

### Deployment
1. Configurar `.env` para producción
2. Recrear BD: `python scripts/recreate_db.py`
3. Iniciar servidor: `uvicorn main:app --host 0.0.0.0`
4. Monitorear: `GET /metrics`

## 📦 Archivos Ignorados (.gitignore)

- `__pycache__/` - Cache de Python
- `.env` - Variables de entorno secretas
- `*.db` - Base de datos local
- `*.log` - Archivos de log
- `.vscode/`, `.idea/` - Configuración de IDEs

## ✨ Limpieza Realizada

### Archivos Organizados
- ✅ Documentación movida a `/docs`
- ✅ Tests movidos a `/tests`
- ✅ Scripts movidos a `/scripts`
- ✅ Archivos duplicados eliminados

### Archivos Eliminados
- ❌ `alembic.ini` (no usado)

### Archivos Creados
- ✅ `README.md` - Documentación principal
- ✅ `QUICKSTART.md` - Guía rápida
- ✅ `.gitignore` - Control de versiones
- ✅ `ESTRUCTURA_PROYECTO.md` - Este archivo

## 🎯 Resultado

Proyecto limpio, organizado y profesional con:
- 📁 Estructura clara y lógica
- 📚 Documentación completa
- 🧪 Tests organizados
- 🛠️ Scripts de utilidad separados
- 🔒 Archivos sensibles protegidos

---

**Total de archivos:** ~25  
**Líneas de código:** ~3,500+  
**Cobertura de tests:** Alta  
**Documentación:** Completa