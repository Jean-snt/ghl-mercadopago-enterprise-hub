# Características de Seguridad Enterprise - MercadoPago System

## 🔒 Funcionalidades de Seguridad Implementadas

### 1. Auditoría Completa (AuditLog)
- **Registro de todas las acciones**: Cada operación del sistema queda registrada
- **Trazabilidad completa**: Desde la generación del link hasta el procesamiento del webhook
- **Metadatos de seguridad**: IP, User-Agent, timestamps, correlation IDs
- **Datos de request/response**: Para debugging y compliance

### 2. Validación de Idempotencia
- **Prevención de duplicados**: Verifica si un `payment_id` ya fue procesado
- **Alertas de seguridad**: Registra intentos de procesamiento duplicado
- **Protección contra replay attacks**: Evita procesamiento múltiple del mismo webhook

### 3. Validación de Montos (Crítica)
- **Comparación exacta**: Valida que el monto pagado coincida con el esperado
- **Tolerancia configurable**: Permite diferencias mínimas por redondeo
- **Bloqueo automático**: Si no coincide, NO actualiza GHL y genera alerta crítica
- **Alertas de seguridad**: Registra discrepancias como `AMOUNT_MISMATCH`

### 4. Sistema de Alertas de Seguridad
- **Clasificación por severidad**: LOW, MEDIUM, HIGH, CRITICAL
- **Tipos de alertas**:
  - `INVALID_WEBHOOK_SIGNATURE`: Firma inválida
  - `DUPLICATE_PAYMENT_ATTEMPT`: Intento de procesamiento duplicado
  - `AMOUNT_MISMATCH`: Discrepancia en montos
  - `UNKNOWN_PAYMENT_REFERENCE`: Referencia desconocida
- **Gestión de alertas**: Resolución manual con notas
- **Notificaciones críticas**: Para alertas de alta severidad

### 5. Validación de Webhooks
- **Verificación de firma HMAC**: Valida autenticidad del webhook
- **Whitelist de IPs**: Control de origen de webhooks
- **Log completo**: Registro de todos los webhooks recibidos
- **Reintentos controlados**: Manejo de fallos con límites

## 🛡️ Medidas de Protección

### Protección contra Ataques
1. **Replay Attacks**: Idempotencia por `payment_id`
2. **Man-in-the-middle**: Validación de firma HMAC
3. **Amount Tampering**: Validación estricta de montos
4. **Injection Attacks**: Uso de SQLAlchemy ORM
5. **Unauthorized Access**: Tokens de API obligatorios

### Monitoreo y Alertas
1. **Métricas en tiempo real**: Endpoint `/metrics`
2. **Dashboard de alertas**: Endpoint `/security/alerts`
3. **Logs de auditoría**: Endpoint `/audit/logs`
4. **Health checks**: Endpoint `/health`

## 📊 Endpoints de Monitoreo

### Auditoría
```
GET /audit/logs?payment_id=123&action=webhook_processed&limit=100
```

### Alertas de Seguridad
```
GET /security/alerts?is_resolved=false&severity=CRITICAL
PUT /security/alerts/123/resolve
```

### Métricas del Sistema
```
GET /metrics
```

## 🚨 Flujo de Seguridad en Webhooks

1. **Recepción**: Log del webhook entrante
2. **Validación de firma**: Verificación HMAC
3. **Verificación de idempotencia**: Check de `payment_id`
4. **Obtención de detalles**: Consulta a MercadoPago API
5. **Validación de monto**: Comparación crítica
6. **Procesamiento**: Solo si todas las validaciones pasan
7. **Auditoría**: Log de todas las acciones

## 🔧 Configuración de Seguridad

### Variables de Entorno Críticas
```bash
MP_WEBHOOK_SECRET=your_webhook_secret_key  # Para validación HMAC
ADMIN_API_KEY=your_super_secure_admin_key  # Para endpoints admin
DATABASE_URL=postgresql://...              # Base de datos segura
```

### Recomendaciones de Producción
1. **HTTPS obligatorio** para todos los endpoints
2. **Rate limiting** en endpoints públicos
3. **Firewall** para restringir IPs de webhooks
4. **Backup automático** de logs de auditoría
5. **Monitoreo 24/7** de alertas críticas
6. **Rotación de tokens** periódica

## 📈 Métricas de Seguridad

El sistema proporciona métricas clave:
- **Tasa de éxito de webhooks**
- **Número de alertas no resueltas**
- **Alertas críticas activas**
- **Tasa de aprobación de pagos**

## 🔍 Investigación de Incidentes

Para investigar problemas de seguridad:

1. **Consultar alertas**: `GET /security/alerts`
2. **Revisar logs de auditoría**: `GET /audit/logs`
3. **Verificar métricas**: `GET /metrics`
4. **Analizar webhooks**: Revisar `WebhookLog` table

Cada registro incluye `correlation_id` para tracking completo de requests.