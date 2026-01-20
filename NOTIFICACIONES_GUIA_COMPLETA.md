# 🔔 SISTEMA DE NOTIFICACIONES EN TIEMPO REAL

## 📋 **RESUMEN**

El sistema de notificaciones envía alertas automáticamente por **Slack**, **Email** y **Webhooks** cuando ocurren eventos críticos como:
- 🚨 Ataques de fuerza bruta
- ⚠️ Errores del sistema
- 📊 Reconciliaciones completadas
- 🔗 Fallos de webhooks
- 💳 Problemas de pagos

---

## 🚀 **INSTALACIÓN RÁPIDA**

### **1. Instalar Dependencias**
```bash
pip install -r requirements.txt
```

### **2. Configurar Variables de Entorno**
```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar configuración
nano .env
```

### **3. Probar Sistema**
```bash
# Ejecutar configurador interactivo
python scripts/setup_notifications.py

# Probar notificaciones
python scripts/test_notifications.py
```

---

## ⚙️ **CONFIGURACIÓN DETALLADA**

### **🔧 Slack (Recomendado)**

#### **Paso 1: Crear App en Slack**
1. Ve a https://api.slack.com/apps
2. Clic en "Create New App" → "From scratch"
3. Nombre: `MercadoPago Enterprise`
4. Selecciona tu workspace

#### **Paso 2: Configurar Incoming Webhooks**
1. En tu app, ve a "Incoming Webhooks"
2. Activa "Activate Incoming Webhooks"
3. Clic en "Add New Webhook to Workspace"
4. Selecciona el canal (ej: `#alerts`)
5. Copia la URL del webhook

#### **Paso 3: Configurar Variables**
```bash
# En tu archivo .env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXXX/YYYY/ZZZZ
SLACK_CHANNEL=#alerts
SLACK_USERNAME=MercadoPago-Bot
```

#### **Paso 4: Probar**
```bash
curl -X POST http://localhost:8000/admin/test-notifications?notification_type=test \
  -H "Authorization: Bearer junior123"
```

### **📧 Email (Gmail)**

#### **Paso 1: Configurar Gmail**
1. Habilita autenticación de 2 factores en tu cuenta Gmail
2. Ve a "Gestionar tu cuenta de Google" → "Seguridad"
3. En "Acceso a Google", selecciona "Contraseñas de aplicaciones"
4. Genera una contraseña para "Correo"
5. Copia la contraseña generada (16 caracteres)

#### **Paso 2: Configurar Variables**
```bash
# En tu archivo .env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=tu-email@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop  # Contraseña de aplicación
FROM_EMAIL=tu-email@gmail.com
TO_EMAILS=admin1@company.com,admin2@company.com,security@company.com
```

#### **Paso 3: Probar**
```bash
curl -X POST http://localhost:8000/admin/test-notifications?notification_type=security \
  -H "Authorization: Bearer junior123"
```

### **🔗 Webhooks Personalizados**

#### **Configuración**
```bash
# En tu archivo .env
WEBHOOK_URLS=https://your-webhook-endpoint.com/alerts,https://backup-webhook.com/notifications
```

#### **Formato del Payload**
```json
{
  "title": "Alerta de Seguridad: brute_force_detected",
  "message": "CRITICAL: 5 failed login attempts detected...",
  "priority": "critical",
  "event_type": "brute_force",
  "timestamp": "2026-01-20T15:30:00Z",
  "data": {
    "alert_type": "brute_force_detected",
    "current_value": 5,
    "threshold_value": 3,
    "unique_ips": ["192.168.1.100"],
    "recommendation": "Block suspicious IPs"
  },
  "source": "mercadopago-enterprise"
}
```

---

## 🎯 **CONFIGURACIÓN AVANZADA**

### **Prioridades de Notificación**
```bash
# Solo notificaciones críticas y altas
MIN_NOTIFICATION_PRIORITY=high

# Todas las notificaciones
MIN_NOTIFICATION_PRIORITY=low
```

### **Rate Limiting**
```bash
# Evitar spam - máximo 1 notificación del mismo tipo cada 5 minutos
NOTIFICATION_RATE_LIMIT=5
```

### **Canales Específicos por Tipo**
El sistema automáticamente determina qué canales usar:
- **CRITICAL**: Slack + Email + Webhooks
- **MEDIUM**: Slack + Webhooks
- **LOW**: Solo Slack

---

## 🧪 **TESTING Y VERIFICACIÓN**

### **API Endpoints de Prueba**

#### **1. Probar Configuración**
```bash
curl -H "Authorization: Bearer junior123" \
  http://localhost:8000/admin/notification-config
```

**Respuesta esperada:**
```json
{
  "success": true,
  "config": {
    "slack_configured": true,
    "email_configured": true,
    "webhooks_configured": true,
    "enabled_channels": ["slack", "email", "webhook"],
    "min_priority": "medium",
    "rate_limit_minutes": 5
  }
}
```

#### **2. Probar Notificación Básica**
```bash
curl -X POST -H "Authorization: Bearer junior123" \
  "http://localhost:8000/admin/test-notifications?notification_type=test"
```

#### **3. Probar Alerta de Seguridad**
```bash
curl -X POST -H "Authorization: Bearer junior123" \
  "http://localhost:8000/admin/test-notifications?notification_type=security"
```

#### **4. Probar Error del Sistema**
```bash
curl -X POST -H "Authorization: Bearer junior123" \
  "http://localhost:8000/admin/test-notifications?notification_type=system_error"
```

### **Scripts de Prueba**

#### **Configurador Interactivo**
```bash
python scripts/setup_notifications.py
```

**Opciones disponibles:**
1. Crear archivo de configuración
2. Probar sistema de notificaciones
3. Probar notificaciones específicas
4. Guía configuración Slack
5. Guía configuración Email
6. Crear script de pruebas

#### **Probador Manual**
```bash
python scripts/test_notifications.py
```

---

## 🔄 **INTEGRACIÓN AUTOMÁTICA**

### **Eventos que Disparan Notificaciones**

#### **Alertas de Seguridad**
- ✅ Automático cuando `AlertService` detecta amenazas
- ✅ Brute force attacks (3+ intentos fallidos)
- ✅ Múltiples amenazas de seguridad
- ✅ Fallos de webhooks críticos

#### **Errores del Sistema**
- ✅ APIs lentas (>5 segundos)
- ✅ Tasa alta de errores de webhook (>15%)
- ✅ Sobrecarga del sistema (>100 pagos/min)
- ✅ Credenciales OAuth expirando

#### **Eventos de Negocio**
- ✅ Reconciliaciones completadas con discrepancias
- ✅ Pagos aprobados (opcional, prioridad baja)
- ✅ Fallos de integración GHL

### **Configuración en Código**

#### **Enviar Notificación Personalizada**
```python
from services.notification_service import NotificationService, NotificationMessage, NotificationPriority

# En tu código
notification_service = NotificationService(db)

notification = NotificationMessage(
    title="Mi Alerta Personalizada",
    message="Descripción del evento",
    priority=NotificationPriority.HIGH,
    event_type="custom_event",
    data={"custom_field": "custom_value"}
)

result = notification_service.send_notification(notification)
```

#### **Usar Métodos de Conveniencia**
```python
# Alerta de seguridad
notification_service.notify_brute_force_attack("192.168.1.100", 5)

# Error del sistema
notification_service.notify_system_error(
    "Database connection failed",
    "database_error",
    component="payment_processor"
)

# Reconciliación completada
notification_service.notify_reconciliation_completed("recon_123", 3, 2)
```

---

## 📊 **MONITOREO Y LOGS**

### **Logs de Notificaciones**
```bash
# Ver logs de notificaciones
tail -f logs/app.log | grep "notification"

# Ver solo errores de notificaciones
tail -f logs/app.log | grep "notification.*ERROR"
```

### **Métricas de Notificaciones**
```bash
# Ver estado de configuración
curl -H "Authorization: Bearer junior123" \
  http://localhost:8000/admin/notification-config

# Probar conectividad
curl -X POST -H "Authorization: Bearer junior123" \
  "http://localhost:8000/admin/test-notifications?notification_type=test"
```

---

## 🚨 **TROUBLESHOOTING**

### **Problemas Comunes**

#### **Slack no recibe notificaciones**
```bash
# Verificar URL del webhook
echo $SLACK_WEBHOOK_URL

# Probar manualmente
curl -X POST $SLACK_WEBHOOK_URL \
  -H 'Content-type: application/json' \
  -d '{"text":"Test message"}'
```

#### **Email no se envía**
```bash
# Verificar configuración SMTP
python -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('$SMTP_USERNAME', '$SMTP_PASSWORD')
print('SMTP OK')
server.quit()
"
```

#### **Webhooks fallan**
```bash
# Probar endpoint manualmente
curl -X POST https://your-webhook-endpoint.com/alerts \
  -H 'Content-Type: application/json' \
  -d '{"test": "message"}'
```

### **Logs de Debug**
```bash
# Habilitar logs detallados
export LOG_LEVEL=DEBUG

# Ver logs de NotificationService
tail -f logs/app.log | grep "notification_service"
```

---

## 🔐 **SEGURIDAD**

### **Buenas Prácticas**

#### **Slack**
- ✅ Usar webhooks específicos por canal
- ✅ No compartir URLs de webhook públicamente
- ✅ Rotar webhooks periódicamente

#### **Email**
- ✅ Usar contraseñas de aplicación (no contraseña principal)
- ✅ Habilitar 2FA en cuentas de email
- ✅ Usar SMTP con TLS/SSL

#### **Webhooks**
- ✅ Usar HTTPS únicamente
- ✅ Implementar autenticación en endpoints
- ✅ Validar payloads recibidos

### **Variables Sensibles**
```bash
# Nunca commitear estas variables
SLACK_WEBHOOK_URL=*
SMTP_PASSWORD=*
WEBHOOK_URLS=*
```

---

## 📈 **ESCALABILIDAD**

### **Para Múltiples Entornos**
```bash
# Desarrollo
MIN_NOTIFICATION_PRIORITY=high
SLACK_CHANNEL=#dev-alerts

# Staging
MIN_NOTIFICATION_PRIORITY=medium
SLACK_CHANNEL=#staging-alerts

# Producción
MIN_NOTIFICATION_PRIORITY=low
SLACK_CHANNEL=#prod-alerts
```

### **Para Múltiples Equipos**
```bash
# Configurar múltiples webhooks
WEBHOOK_URLS=https://security-team.com/alerts,https://devops-team.com/alerts,https://business-team.com/alerts

# Configurar múltiples emails
TO_EMAILS=security@company.com,devops@company.com,cto@company.com
```

---

## 🎉 **EJEMPLOS DE NOTIFICACIONES**

### **Slack - Brute Force Attack**
```
🛡️ [CRITICAL] BRUTE FORCE ATTACK DETECTED

CRITICAL: 5 failed login attempts detected in 15 minutes (threshold: 3). 
Possible brute force attack in progress!

Prioridad: CRITICAL
Tipo de Evento: brute_force
Timestamp: 2026-01-20 15:30:00 UTC
Unique Ips: 1
Total Unique Ips: 1
Recommendation: IMMEDIATE ACTION: Block suspicious IPs, review security logs
```

### **Email - System Error**
```
Subject: [HIGH] Error del Sistema: database_error

Database connection failed

Detalles del Evento:
- Tipo: database_error
- Prioridad: HIGH
- Timestamp: 2026-01-20 15:30:00 UTC

Datos Adicionales:
- Component: payment_processor
- Error Code: DB_CONN_TIMEOUT

---
MercadoPago Enterprise Notification System
```

### **Webhook - Reconciliation**
```json
{
  "title": "Reconciliación Completada: 3 discrepancias",
  "message": "La reconciliación diaria ha finalizado. Se encontraron 3 discrepancias y se aplicaron 2 correcciones automáticas.",
  "priority": "high",
  "event_type": "reconciliation",
  "timestamp": "2026-01-20T15:30:00Z",
  "data": {
    "execution_id": "recon_20260120_153000",
    "discrepancies_found": 3,
    "corrections_applied": 2,
    "completion_time": "2026-01-20T15:30:00Z"
  }
}
```

---

## 🔄 **AUTOMATIZACIÓN**

### **Cron Jobs para Monitoreo**
```bash
# Verificar notificaciones cada hora
0 * * * * curl -s -H "Authorization: Bearer junior123" http://localhost:8000/admin/notification-config > /dev/null

# Probar notificaciones diariamente
0 9 * * * curl -s -X POST -H "Authorization: Bearer junior123" "http://localhost:8000/admin/test-notifications?notification_type=test" > /dev/null
```

### **Integración con CI/CD**
```yaml
# .github/workflows/test-notifications.yml
name: Test Notifications
on:
  schedule:
    - cron: '0 9 * * *'  # Daily at 9 AM
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Test Notifications
        run: |
          curl -X POST -H "Authorization: Bearer ${{ secrets.ADMIN_API_KEY }}" \
            "${{ secrets.BASE_URL }}/admin/test-notifications?notification_type=test"
```

---

*Documento actualizado el: 2026-01-20 15:30:00*  
*Estado: SISTEMA DE NOTIFICACIONES COMPLETAMENTE FUNCIONAL ✅*

---

## 🎯 **PRÓXIMOS PASOS**

1. **Configurar Slack** - Más rápido y visual
2. **Configurar Email** - Para alertas críticas
3. **Probar sistema** - Usar scripts incluidos
4. **Integrar con alertas** - Ya está automático
5. **Monitorear logs** - Verificar funcionamiento

**¡El sistema está listo para producción!** 🚀