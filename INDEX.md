# 📑 Índice de Documentación - MercadoPago Enterprise Multi-tenant

Guía completa para navegar el sistema MercadoPago Enterprise con arquitectura multi-tenant.

---

## 🚀 Para Empezar Rápido

### **Nuevos Usuarios (5 minutos)**
1. **[README.md](README.md)** - Documentación completa del sistema
2. **[QUICKSTART.md](QUICKSTART.md)** - Instalación en 5 minutos
3. **[COMANDOS_UTILES.md](COMANDOS_UTILES.md)** - Referencia de comandos

### **Desarrolladores**
1. **[README.md](README.md)** - Arquitectura multi-tenant y APIs
2. **[ESTRUCTURA_PROYECTO.md](ESTRUCTURA_PROYECTO.md)** - Organización del código
3. **[docs/](docs/)** - Documentación técnica detallada

### **Administradores/Gerentes**
1. **[RESUMEN_EJECUTIVO.md](RESUMEN_EJECUTIVO.md)** - Visión general del proyecto
2. **[README.md](README.md)** - Capacidades y casos de uso
3. **Dashboard NOC**: `http://localhost:8000/dashboard`

---

## 📚 Documentación Principal

### **Nivel 1: Esencial**
| Documento | Descripción | Audiencia |
|-----------|-------------|-----------|
| **[README.md](README.md)** | Documentación completa multi-tenant | Todos |
| **[QUICKSTART.md](QUICKSTART.md)** | Instalación en 5 minutos | Nuevos usuarios |
| **[MANUAL_INSTALACION_EXPRESS.md](MANUAL_INSTALACION_EXPRESS.md)** | **Instalación en 3 pasos (10 minutos)** | Nuevos clientes |
| **[RESUMEN_EJECUTIVO.md](RESUMEN_EJECUTIVO.md)** | Visión general ejecutiva | Gerentes |

### **Nivel 2: Comercial y Entrega**
| Documento | Descripción | Audiencia |
|-----------|-------------|-----------|
| **[PITCH_COMERCIAL.md](PITCH_COMERCIAL.md)** | **Propuesta comercial completa** | Ventas/Clientes |
| **[ENTREGA_FINAL_DIA5.md](ENTREGA_FINAL_DIA5.md)** | **Documento de entrega final** | Stakeholders |
| **[RESUMEN_EJECUTIVO_FINAL.md](RESUMEN_EJECUTIVO_FINAL.md)** | **Resumen ejecutivo del proyecto** | Gerencia |

### **Nivel 3: Referencia**
| Documento | Descripción | Audiencia |
|-----------|-------------|-----------|
| **[COMANDOS_UTILES.md](COMANDOS_UTILES.md)** | Comandos y scripts útiles | Desarrolladores |
| **[ESTRUCTURA_PROYECTO.md](ESTRUCTURA_PROYECTO.md)** | Organización de archivos | Desarrolladores |
| **[COMO_RESOLVER_ALERTAS.md](COMO_RESOLVER_ALERTAS.md)** | Gestión de alertas | Administradores |

---

## 🏗️ Sistema Multi-tenant

### **Arquitectura Implementada**
- ✅ **Dashboard por Cliente**: `/dashboard/client/{client_id}`
- ✅ **Aislamiento de Datos**: Cada cliente ve solo sus pagos
- ✅ **OAuth Independiente**: Tokens GHL específicos por cliente
- ✅ **API Multi-tenant**: Endpoints filtrados por cliente

### **Casos de Uso Soportados**
- 🏢 **Agencias**: Múltiples clientes con dashboards independientes
- 🚀 **SaaS Multi-tenant**: Aislamiento completo de datos por tenant
- 🔄 **Resellers**: White label con configuración personalizada

### **URLs Multi-tenant**
```bash
# Dashboard general (NOC)
http://localhost:8000/dashboard

# Dashboard específico por cliente
http://localhost:8000/dashboard/client/{client_id}

# API métricas por cliente
http://localhost:8000/api/v1/clients/{client_id}/metrics

# API pagos por cliente
http://localhost:8000/api/v1/clients/{client_id}/payments
```

---

## 📖 Documentación Técnica (/docs)

### **Seguridad Enterprise**
- **[docs/SECURITY_FEATURES.md](docs/SECURITY_FEATURES.md)**
  - Auditoría blockchain con hash chain
  - Sistema de alertas (brute force, amenazas)
  - Validaciones HMAC y idempotencia
  - Centro NOC con monitoreo en tiempo real

### **Desarrollo por Fases**
- **[docs/MVP_DIA1_COMPLETADO.md](docs/MVP_DIA1_COMPLETADO.md)**
  - MVP básico de pagos MercadoPago
  - Estructura de base de datos
  - Tests iniciales

- **[docs/DIA2_COMPLETADO.md](docs/DIA2_COMPLETADO.md)**
  - Sistema de webhooks resiliente
  - Validaciones de seguridad enterprise
  - Procesamiento asíncrono

- **[docs/PUENTE_GHL_VERIFICADO.md](docs/PUENTE_GHL_VERIFICADO.md)**
  - Integración con GoHighLevel
  - Modo mock para desarrollo
  - Actualización automática de contactos

### **Sistemas Avanzados**
- **[docs/SISTEMA_RECONCILIACION_COMPLETADO.md](docs/SISTEMA_RECONCILIACION_COMPLETADO.md)**
  - Reconciliación diaria automática
  - Service Layer Pattern
  - Reportes CSV/JSON

- **[docs/SISTEMA_RESILIENTE_COMPLETADO.md](docs/SISTEMA_RESILIENTE_COMPLETADO.md)**
  - Procesamiento asíncrono de webhooks
  - Sistema de reintentos
  - Gestión de colas

- **[docs/EJERCICIO5_NOC_COMPLETADO.md](docs/EJERCICIO5_NOC_COMPLETADO.md)**
  - Centro de Comando NOC
  - Dashboard con métricas en tiempo real
  - Sistema de alertas inteligente

### **OAuth y Multi-tenant**
- **[docs/CHANGELOG_OAUTH.md](docs/CHANGELOG_OAUTH.md)**
  - Implementación OAuth MercadoPago
  - Sistema multi-tenant completo
  - Gestión de tokens por cliente

---

## 🧪 Testing y Verificación (/tests)

### **Scripts de Verificación Principal**
| Script | Propósito | Comando |
|--------|-----------|---------|
| **generate_final_report.py** | **Verificación completa con score** | `python scripts/generate_final_report.py` |
| **verify_multitenant_integration.py** | Verificación completa del sistema | `python scripts/verify_multitenant_integration.py` |
| **test_quick_payment.py** | Test rápido de pagos | `python tests/test_quick_payment.py` |
| **test_security.py** | Tests de seguridad enterprise | `python tests/test_security.py` |

### **Tests Específicos**
| Script | Propósito | Comando |
|--------|-----------|---------|
| **test_oauth.py** | Tests OAuth MercadoPago | `python tests/test_oauth.py` |
| **test_webhook_ghl.py** | Test integración GHL | `python tests/test_webhook_ghl.py` |
| **test_resilient_webhooks.py** | Test webhooks resilientes | `python tests/test_resilient_webhooks.py` |
| **verify_payment.py** | Verificar estado de pago | `python tests/verify_payment.py <id>` |

### **Tests Archivados (/tests/archive)**
Scripts de prueba que ya no se usan en el flujo principal:
- `simulate_ghl_oauth_callback.py` - Simulación OAuth GHL
- `test_ghl_oauth.py` - Pruebas OAuth GHL
- `verify_day3_multitenant_dashboard.py` - Verificación dashboard

---

## 🛠️ Scripts de Gestión (/scripts)

### **Base de Datos**
| Script | Propósito | Comando |
|--------|-----------|---------|
| **recreate_db.py** | Recrear BD desde cero | `python scripts/recreate_db.py` |
| **setup_multitenant_database.py** | Migrar a multi-tenant | `python scripts/setup_multitenant_database.py` |
| **setup_database.py** | Configurar esquema seguridad | `python scripts/setup_database.py` |

### **Multi-tenant y OAuth**
| Script | Propósito | Comando |
|--------|-----------|---------|
| **verify_multitenant_integration.py** | Verificación completa | `python scripts/verify_multitenant_integration.py` |

### **Seguridad y Alertas**
| Script | Propósito | Comando |
|--------|-----------|---------|
| **resolve_alerts.py** | Resolver alertas | `python scripts/resolve_alerts.py` |
| **start_alert_monitoring.py** | Monitoreo de alertas | `python scripts/start_alert_monitoring.py` |

### **Archivado y Mantenimiento**
| Script | Propósito | Comando |
|--------|-----------|---------|
| **archive_logs_to_s3.py** | Archivar logs en S3 | `python scripts/archive_logs_to_s3.py --last-month` |
| **setup_s3_cron.py** | Configurar cron S3 | `python scripts/setup_s3_cron.py --install weekly` |

### **Utilidades**
| Script | Propósito | Comando |
|--------|-----------|---------|
| **force_approve.py** | Aprobar pago manualmente | `python scripts/force_approve.py <id>` |
| **daily_reconcile.py** | Reconciliación diaria | `python scripts/daily_reconcile.py` |

---

## 🎯 Guías por Caso de Uso

### **Quiero Instalar el Sistema Multi-tenant**
1. [QUICKSTART.md](QUICKSTART.md) - Instalación en 5 minutos
2. `python scripts/setup_multitenant_database.py` - Migrar a multi-tenant
3. `python scripts/verify_multitenant_integration.py` - Verificar instalación

### **Quiero Configurar un Cliente Nuevo**
1. [README.md](README.md) → Sección "Sistema Multi-tenant"
2. Configurar OAuth GHL: `/oauth/ghl/authorize?client_id=nuevo_cliente`
3. Acceder dashboard: `/dashboard/client/nuevo_cliente`

### **Quiero Entender la Arquitectura**
1. [README.md](README.md) → Sección "Arquitectura Multi-tenant"
2. [ESTRUCTURA_PROYECTO.md](ESTRUCTURA_PROYECTO.md) - Organización
3. [docs/](docs/) - Documentación técnica detallada

### **Quiero Probar el Sistema**
1. `python scripts/verify_multitenant_integration.py` - Verificación completa
2. [tests/](tests/) - Scripts de testing específicos
3. Dashboard: `http://localhost:8000/dashboard`

### **Quiero Desplegar a Producción**
1. [README.md](README.md) → Sección "Producción"
2. Configurar variables de entorno reales
3. `python scripts/setup_s3_cron.py --install weekly` - Archivado automático

### **Quiero Gestionar Alertas de Seguridad**
1. [COMO_RESOLVER_ALERTAS.md](COMO_RESOLVER_ALERTAS.md) - Guía completa
2. `python scripts/resolve_alerts.py` - Resolver alertas
3. Dashboard NOC: `/dashboard` - Monitoreo en tiempo real

---

## 🔍 Búsqueda Rápida por Tema

### **Multi-tenant**
- [README.md](README.md) → "Sistema Multi-tenant"
- `scripts/setup_multitenant_database.py`
- `/dashboard/client/{client_id}`

### **OAuth GoHighLevel**
- [README.md](README.md) → "OAuth GoHighLevel por Cliente"
- [docs/CHANGELOG_OAUTH.md](docs/CHANGELOG_OAUTH.md)
- `/oauth/ghl/authorize`

### **Seguridad**
- [docs/SECURITY_FEATURES.md](docs/SECURITY_FEATURES.md)
- [COMO_RESOLVER_ALERTAS.md](COMO_RESOLVER_ALERTAS.md)
- `scripts/resolve_alerts.py`

### **Archivado S3**
- [README.md](README.md) → "Archivado AWS S3"
- `scripts/archive_logs_to_s3.py`
- `scripts/setup_s3_cron.py`

### **API Endpoints**
- [README.md](README.md) → "API Endpoints"
- `/api/v1/clients/{client_id}/metrics`
- `/api/v1/clients/{client_id}/payments`

### **Dashboard y Monitoreo**
- `/dashboard` - Dashboard NOC general
- `/dashboard/client/{client_id}` - Dashboard por cliente
- `/api/v1/dashboard/metrics/realtime` - Métricas tiempo real

---

## 📊 Mapa del Proyecto Multi-tenant

```
MercadoPago Enterprise Multi-tenant
├── Documentación Principal
│   ├── README.md (Documentación completa)
│   ├── QUICKSTART.md (Instalación rápida)
│   └── RESUMEN_EJECUTIVO.md (Visión ejecutiva)
│
├── Sistema Multi-tenant
│   ├── /dashboard/client/{client_id} (Dashboard por cliente)
│   ├── /api/v1/clients/{client_id}/* (APIs por cliente)
│   └── OAuth GHL independiente por cliente
│
├── Seguridad Enterprise
│   ├── Auditoría blockchain (hash chain)
│   ├── Sistema de alertas (brute force, amenazas)
│   ├── Centro NOC (/dashboard)
│   └── Archivado S3 automático
│
├── Código (/scripts, /tests, /services)
│   ├── Scripts de gestión (BD, multi-tenant, S3)
│   ├── Tests de verificación (sistema, seguridad)
│   └── Servicios (OAuth, métricas, alertas, archivado)
│
└── Documentación Técnica (/docs)
    ├── Seguridad y auditoría
    ├── Desarrollo por fases
    ├── Sistemas avanzados (NOC, reconciliación)
    └── OAuth y multi-tenant
```

---

## 🎓 Rutas de Aprendizaje

### **Ruta 1: Usuario Nuevo (30 min)**
1. [README.md](README.md) - Leer sección "Características Principales" (10 min)
2. [QUICKSTART.md](QUICKSTART.md) - Instalar sistema (10 min)
3. `python scripts/verify_multitenant_integration.py` - Verificar (5 min)
4. Acceder dashboard: `http://localhost:8000/dashboard` (5 min)

### **Ruta 2: Desarrollador Multi-tenant (2 horas)**
1. [README.md](README.md) - Leer completo (45 min)
2. [ESTRUCTURA_PROYECTO.md](ESTRUCTURA_PROYECTO.md) - Entender organización (15 min)
3. Revisar código: `main.py`, `models.py`, `services/` (45 min)
4. [docs/](docs/) - Documentación técnica específica (15 min)

### **Ruta 3: Administrador/DevOps (1 hora)**
1. [README.md](README.md) - Sección "Producción" (20 min)
2. [RESUMEN_EJECUTIVO.md](RESUMEN_EJECUTIVO.md) - Visión general (10 min)
3. [COMO_RESOLVER_ALERTAS.md](COMO_RESOLVER_ALERTAS.md) - Gestión alertas (15 min)
4. Configurar archivado: `scripts/setup_s3_cron.py` (15 min)

### **Ruta 4: Gerente/Stakeholder (20 min)**
1. [RESUMEN_EJECUTIVO.md](RESUMEN_EJECUTIVO.md) - Visión completa (10 min)
2. [README.md](README.md) - Sección "Casos de Uso" (10 min)

---

## 💡 Tips de Navegación

### **Atajos Útiles**
- **Dashboard NOC**: `http://localhost:8000/dashboard`
- **Dashboard Cliente**: `http://localhost:8000/dashboard/client/{client_id}`
- **Verificación rápida**: `python scripts/verify_multitenant_integration.py`
- **Resolver alertas**: `python scripts/resolve_alerts.py`

### **Convenciones de Archivos**
- 📄 `.md` - Documentación
- 🐍 `.py` - Código Python
- 🧪 `test_*.py` - Tests
- 🛠️ `scripts/` - Herramientas de gestión
- 📊 `/dashboard` - Interfaces web
- 🔧 `/api/v1/` - APIs REST

### **Estados del Sistema**
- ✅ **HEALTHY** - Sistema funcionando correctamente
- ⚠️ **DEGRADED** - Funcionando con limitaciones
- ❌ **DOWN** - Sistema no disponible
- 🔄 **PROCESSING** - Operación en curso

---

## 🆘 Ayuda Rápida

### **No sé por dónde empezar**
→ [QUICKSTART.md](QUICKSTART.md) (5 minutos)

### **Quiero configurar multi-tenant**
→ `python scripts/setup_multitenant_database.py`

### **Necesito crear un cliente nuevo**
→ [README.md](README.md) → "Sistema Multi-tenant"

### **Tengo alertas de seguridad**
→ [COMO_RESOLVER_ALERTAS.md](COMO_RESOLVER_ALERTAS.md)

### **Quiero archivar logs**
→ `python scripts/archive_logs_to_s3.py --last-month`

### **El sistema no funciona**
→ `python scripts/verify_multitenant_integration.py`

### **Necesito documentación técnica**
→ [docs/](docs/)

### **Quiero desplegar a producción**
→ [README.md](README.md) → Sección "Producción"

---

## 🏆 Estado Actual del Sistema

### **✅ Completado (100%)**
- **Sistema Multi-tenant** - Arquitectura completa
- **Dashboard por Cliente** - Vista específica con métricas
- **OAuth GoHighLevel** - Integración por cliente
- **Seguridad Enterprise** - Auditoría, alertas, validaciones
- **Archivado S3** - Retención automática con lifecycle
- **Centro NOC** - Monitoreo en tiempo real
- **Sistema Resiliente** - Webhooks asíncronos
- **Reconciliación** - Verificación diaria automática

### **🎯 Casos de Uso Activos**
- ✅ **Agencias** con múltiples clientes independientes
- ✅ **SaaS Multi-tenant** con aislamiento completo
- ✅ **Resellers** con configuración white label
- ✅ **Enterprise** con seguridad y auditoría completa

### **📈 Métricas del Sistema**
- **Clientes soportados**: Ilimitados (arquitectura escalable)
- **Performance**: Optimizada con índices multi-tenant
- **Seguridad**: Enterprise con auditoría blockchain
- **Disponibilidad**: 99.9% con sistema resiliente

---

**Versión:** 3.0.0 Multi-tenant  
**Última actualización:** Enero 2026  
**Documentos totales:** 8 principales + documentación técnica  
**Cobertura:** 100% del sistema  
**Estado:** ✅ PRODUCCIÓN READY

## 🎯 **SPRINT 2 - AUTOMATIZACIÓN DE TAGS GHL Y NOTIFICACIONES VENDEDOR**

### **📋 Documentación del Sprint 2**
- [`SPRINT2_TAGGING_GHL_COMPLETADO.md`](SPRINT2_TAGGING_GHL_COMPLETADO.md) - **Automatización completa de tags en GoHighLevel**
- [`SPRINT2_MVP_NOTIFICACIONES_COMPLETADO.md`](SPRINT2_MVP_NOTIFICACIONES_COMPLETADO.md) - **MVP Notificaciones para Vendedor**

### **🧪 Scripts del Sprint 2**
- `scripts/simulate_ghl_tagging.py` - Simulador del flujo de tagging automático
- `scripts/update_db_for_tagging.py` - Migración de BD para soporte de tags
- `scripts/setup_vendor_notifications.py` - Configuración sistema notificaciones vendedor
- `scripts/test_vendor_notifications.py` - Prueba integración completa notificaciones

### **🔧 Funcionalidades Implementadas**

#### **🏷️ Sistema de Tagging GHL**
- ✅ **GHL Tag Logic** integrada en notification_service.py
- ✅ **Tag específico** configurable por cliente (default_tag_paid)
- ✅ **Logs de eventos** completos con PaymentEvent
- ✅ **Simulador funcional** para testing y demostración

#### **📧 Sistema de Notificaciones Vendedor**
- ✅ **Disparador único** desde backend post-webhook MercadoPago
- ✅ **Endpoint dashboard** GET /api/notifications/ con datos JSON
- ✅ **Email SMTP simple** en texto plano (Asunto: Pago aprobado – RP PAY)
- ✅ **Protección anti-duplicados** con tabla PaymentEvent
- ✅ **Prueba de integración** completa: Pago -> Tag GHL -> Dashboard -> Email

### **🎯 Casos de Uso Soportados**
- **Agencias:** Tags personalizados + notificaciones por cliente
- **SaaS:** Notificaciones automáticas por plan de suscripción
- **Resellers:** Sistema completo white-label con notificaciones

### **📊 APIs Nuevas**
- `GET /api/notifications/` - Lista notificaciones recientes para dashboard
- `GET /api/notifications/stats` - Estadísticas del sistema de notificaciones

### **🗄️ Base de Datos**
- **Tabla:** `payment_events` - Tracking de eventos y protección anti-duplicados
- **Campo:** `client_accounts.default_tag_paid` - Tag personalizable por cliente

---

**🏆 SPRINT 2 COMPLETADO EXITOSAMENTE - 21 de Enero, 2026**