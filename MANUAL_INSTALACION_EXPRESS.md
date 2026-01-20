# 🚀 MANUAL DE INSTALACIÓN EXPRESS
## MercadoPago Enterprise Multi-tenant - 3 Pasos Simples

### ⏱️ **TIEMPO TOTAL: 10 MINUTOS**

---

## 📋 **REQUISITOS PREVIOS**
- ✅ Python 3.8+ instalado
- ✅ Cuenta MercadoPago (modo sandbox para pruebas)
- ✅ Cuenta GoHighLevel (opcional para desarrollo)

---

## 🎯 **PASO 1: INSTALACIÓN AUTOMÁTICA** *(3 minutos)*

### **1.1 Descargar e Instalar**
```bash
# Clonar repositorio
git clone <repository-url>
cd mercadopago-enterprise

# Instalar dependencias automáticamente
pip install -r requirements.txt
```

### **1.2 Configuración Básica**
```bash
# Copiar archivo de configuración
copy .env.example .env
```

**Editar `.env` con tus credenciales mínimas:**
```bash
# CONFIGURACIÓN MÍNIMA REQUERIDA
ADMIN_API_KEY=tu_token_admin_123
ENVIRONMENT=development

# MERCADOPAGO (Obligatorio)
MP_ACCESS_TOKEN=TEST-tu_access_token_sandbox
MP_WEBHOOK_SECRET=tu_webhook_secret

# GOHIGHLEVEL (Opcional - usar valores por defecto para desarrollo)
GHL_CLIENT_ID=default_client_id
GHL_CLIENT_SECRET=default_client_secret
```

### **1.3 Inicialización Automática**
```bash
# Crear base de datos y configurar multi-tenant
python scripts/recreate_db.py
python scripts/setup_multitenant_database.py
```

**✅ RESULTADO:** Sistema base instalado y configurado

---

## 🚀 **PASO 2: ACTIVACIÓN INMEDIATA** *(2 minutos)*

### **2.1 Iniciar Servidor**
```bash
# Iniciar en modo desarrollo
uvicorn main:app --reload
```

### **2.2 Verificación Automática**
```bash
# Verificar que todo funciona (en otra terminal)
python scripts/verify_multitenant_integration.py
```

**Deberías ver:**
```
✅ SISTEMA COMPLETAMENTE OPERATIVO
✅ Base de datos: OK
✅ API funcionando: OK  
✅ Multi-tenant: OK
✅ Cliente de prueba creado: cliente_prueba_oficial
```

### **2.3 Acceso Inmediato**
- **Dashboard Principal:** http://localhost:8000/dashboard
- **Dashboard Cliente:** http://localhost:8000/dashboard/client/cliente_prueba_oficial
- **API Docs:** http://localhost:8000/docs

**✅ RESULTADO:** Sistema funcionando y accesible

---

## 🎉 **PASO 3: PRIMER PAGO DE PRUEBA** *(5 minutos)*

### **3.1 Crear Pago desde Dashboard**
1. Ir a: http://localhost:8000/dashboard/client/cliente_prueba_oficial
2. Usar el formulario "Generar Link de Pago de Prueba"
3. Llenar datos:
   ```
   Email: test@ejemplo.com
   Nombre: Cliente Prueba
   Monto: 100
   Descripción: Mi primer pago
   ```
4. Hacer clic en "Generar Link"

### **3.2 Simular Pago Aprobado**
```bash
# Aprobar el pago automáticamente (desarrollo)
python scripts/force_approve_simple.py <preference_id>
```

### **3.3 Verificar Resultado**
- **Dashboard actualizado** con el pago aprobado
- **Métricas en tiempo real** mostrando el pago
- **Logs de auditoría** registrando todas las acciones

**✅ RESULTADO:** Primer pago procesado exitosamente

---

## 🎯 **¡LISTO PARA USAR!**

### **🔥 LO QUE YA TIENES FUNCIONANDO:**
- ✅ **Creación de pagos** con links de MercadoPago
- ✅ **Dashboard multi-tenant** por cliente
- ✅ **Procesamiento de webhooks** automático
- ✅ **Sistema de seguridad** con auditoría completa
- ✅ **Integración GoHighLevel** (modo simulación)
- ✅ **Métricas en tiempo real** y alertas
- ✅ **Base de datos multi-tenant** completamente configurada

### **📱 ACCESOS RÁPIDOS:**
```bash
# Dashboard principal (NOC)
http://localhost:8000/dashboard

# Dashboard específico del cliente
http://localhost:8000/dashboard/client/cliente_prueba_oficial

# API completa documentada
http://localhost:8000/docs

# Health check del sistema
http://localhost:8000/health
```

---

## 🛠️ **COMANDOS ÚTILES POST-INSTALACIÓN**

### **Gestión de Pagos**
```bash
# Crear pago por API
curl -X POST http://localhost:8000/api/v1/payments/create \
  -H "Authorization: Bearer tu_token_admin_123" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "cliente@ejemplo.com",
    "customer_name": "Cliente Nuevo",
    "amount": 150.00,
    "description": "Pago por API",
    "client_id": "cliente_prueba_oficial"
  }'

# Ver todos los pagos del cliente
curl -H "Authorization: Bearer tu_token_admin_123" \
  http://localhost:8000/api/v1/clients/cliente_prueba_oficial/payments
```

### **Monitoreo del Sistema**
```bash
# Ver métricas en tiempo real
curl -H "Authorization: Bearer tu_token_admin_123" \
  http://localhost:8000/api/v1/dashboard/metrics/realtime

# Ver alertas de seguridad
curl -H "Authorization: Bearer tu_token_admin_123" \
  http://localhost:8000/security/alerts

# Ver logs de auditoría
curl -H "Authorization: Bearer tu_token_admin_123" \
  http://localhost:8000/audit/logs?limit=20
```

### **Gestión Multi-tenant**
```bash
# Listar todos los clientes
curl -H "Authorization: Bearer tu_token_admin_123" \
  http://localhost:8000/clients

# Ver métricas específicas de un cliente
curl -H "Authorization: Bearer tu_token_admin_123" \
  http://localhost:8000/api/v1/clients/cliente_prueba_oficial/metrics
```

---

## 🔧 **CONFIGURACIÓN AVANZADA (OPCIONAL)**

### **Habilitar Notificaciones en Tiempo Real**
```bash
# Agregar a .env para notificaciones Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/tu/webhook/url
NOTIFICATION_ENABLED=true

# Probar notificaciones
python scripts/setup_notifications.py
```

### **Configurar Archivado S3 (Producción)**
```bash
# Agregar a .env para archivado automático
AWS_ACCESS_KEY_ID=tu_aws_access_key
AWS_SECRET_ACCESS_KEY=tu_aws_secret_key
S3_BUCKET_NAME=tu-bucket-logs
ARCHIVE_ENABLED=true

# Configurar archivado automático
python scripts/setup_s3_cron.py --install weekly
```

### **Modo Producción**
```bash
# Cambiar a producción en .env
ENVIRONMENT=production
BASE_URL=https://tu-dominio.com

# Usar credenciales reales de MercadoPago
MP_ACCESS_TOKEN=APP_USR-tu_token_real
MP_WEBHOOK_SECRET=tu_secret_real

# Iniciar en producción
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 🆘 **SOLUCIÓN DE PROBLEMAS RÁPIDA**

### **❌ Error: "ADMIN_API_KEY no configurado"**
**Solución:** Edita `.env` y agrega `ADMIN_API_KEY=tu_token_123`

### **❌ Error: "Base de datos no encontrada"**
**Solución:** Ejecuta `python scripts/recreate_db.py`

### **❌ Error: "Puerto 8000 en uso"**
**Solución:** Usa otro puerto: `uvicorn main:app --port 8001`

### **❌ Error: "Module not found"**
**Solución:** Ejecuta `pip install -r requirements.txt`

### **❌ Dashboard no carga**
**Solución:** Verifica que el servidor esté corriendo en http://localhost:8000

### **❌ No se crean pagos**
**Solución:** Verifica que `MP_ACCESS_TOKEN` esté configurado en `.env`

---

## 📞 **SOPORTE INMEDIATO**

### **🔍 Verificación del Sistema**
```bash
# Ejecutar diagnóstico completo
python scripts/generate_final_report.py

# Verificar componentes específicos
python scripts/verify_multitenant_integration.py
python scripts/verify_day3_multitenant_dashboard.py
```

### **📋 Logs para Debugging**
```bash
# Ver logs del servidor en tiempo real
# (Ejecutar en terminal separada mientras el servidor corre)
tail -f logs/app.log

# Ver logs de auditoría desde la API
curl -H "Authorization: Bearer tu_token_admin_123" \
  http://localhost:8000/audit/logs?limit=50
```

### **🎯 Tests Rápidos**
```bash
# Test completo del sistema
python tests/test_quick_payment.py

# Test de seguridad
python tests/test_security.py

# Test de integración GHL
python tests/test_webhook_ghl.py
```

---

## 🎉 **¡FELICITACIONES!**

### **🏆 HAS INSTALADO EXITOSAMENTE:**
- ✅ **Sistema de pagos enterprise** con MercadoPago
- ✅ **Arquitectura multi-tenant** para múltiples clientes
- ✅ **Integración GoHighLevel** con OAuth automático
- ✅ **Seguridad nivel bancario** con auditoría blockchain
- ✅ **Dashboard profesional** con métricas en tiempo real
- ✅ **Sistema de alertas** automático
- ✅ **Procesamiento resiliente** de webhooks

### **🚀 PRÓXIMOS PASOS:**
1. **Personalizar** el sistema para tu negocio específico
2. **Agregar clientes reales** usando el flujo OAuth
3. **Configurar notificaciones** para tu equipo
4. **Habilitar archivado S3** para retención a largo plazo
5. **Migrar a producción** cuando estés listo

### **📚 DOCUMENTACIÓN COMPLETA:**
- `README.md` - Documentación técnica completa
- `QUICKSTART.md` - Guía de inicio rápido
- `docs/` - Documentación detallada por componente

---

**🎯 TIEMPO TOTAL INVERTIDO: 10 MINUTOS**  
**🏆 RESULTADO: SISTEMA ENTERPRISE COMPLETAMENTE FUNCIONAL**

---

*Manual creado: Enero 2026*  
*Versión del sistema: 3.0.0 Multi-tenant*  
*Estado: ✅ PRODUCCIÓN READY*