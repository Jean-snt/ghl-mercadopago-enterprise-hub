# 🔧 CÓMO RESOLVER ALERTAS DE SEGURIDAD

## 📋 **RESUMEN**

Cuando el sistema detecta una amenaza (como brute force), el dashboard se pone **ROJO** (`threat_level: "high"`). Para volver el dashboard a **VERDE**, necesitas marcar las alertas como **RESUELTAS**.

---

## 🚨 **ESTADO ACTUAL DEL SISTEMA**

### **Dashboard en VERDE** ✅
```json
{
  "security": {
    "threat_level": "low",
    "top_threats": []
  }
}
```

### **Dashboard en ROJO** ❌
```json
{
  "security": {
    "threat_level": "high",
    "top_threats": [
      {
        "threat_type": "brute_force_detected",
        "severity": "CRITICAL",
        "count": 1
      }
    ]
  }
}
```

---

## 🛠️ **MÉTODOS PARA RESOLVER ALERTAS**

### **Método 1: Script Automático (Recomendado)**

```bash
# Resolver todas las alertas automáticamente
python scripts/resolve_alerts.py --auto

# Modo interactivo (te pregunta qué hacer)
python scripts/resolve_alerts.py
```

**Salida esperada:**
```
🔧 Resolver Alertas de Seguridad - MercadoPago Enterprise
============================================================
📊 Verificando estado actual del dashboard...
   Nivel de amenaza: high
   Amenazas activas: 1

🚨 Obteniendo alertas activas...
📋 Encontradas 1 alertas activas:
------------------------------------------------------------
   ID: 1
   Tipo: brute_force_detected
   Severidad: CRITICAL
   Título: [CRITICAL] BRUTE FORCE ATTACK DETECTED
   Creada: 2026-01-20T12:36:39
------------------------------------------------------------

🤖 Modo automático: Resolviendo todas las alertas...
   ✅ Alerta 1 resuelta

📊 Verificando estado final del dashboard...
   Nivel de amenaza: low
   Amenazas activas: 0
🎉 ¡Dashboard vuelto a verde exitosamente!
```

### **Método 2: API REST Manual**

#### **Paso 1: Obtener alertas activas**
```bash
curl -H "Authorization: Bearer junior123" \
  "http://localhost:8000/security/alerts?is_resolved=false"
```

**Respuesta:**
```json
{
  "alerts": [
    {
      "id": 1,
      "alert_type": "brute_force_detected",
      "severity": "CRITICAL",
      "title": "[CRITICAL] BRUTE FORCE ATTACK DETECTED",
      "is_resolved": false,
      "created_at": "2026-01-20T12:36:39"
    }
  ]
}
```

#### **Paso 2: Resolver alerta específica**
```bash
curl -X PUT \
  -H "Authorization: Bearer junior123" \
  "http://localhost:8000/security/alerts/1/resolve?resolution_notes=Brute force attack mitigated. Security measures enhanced."
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Alert resolved successfully"
}
```

#### **Paso 3: Verificar dashboard**
```bash
curl -H "Authorization: Bearer junior123" \
  "http://localhost:8000/api/v1/dashboard/overview"
```

**Resultado esperado:**
```json
{
  "data": {
    "security": {
      "threat_level": "low",  // ✅ VERDE!
      "top_threats": []       // ✅ SIN AMENAZAS!
    }
  }
}
```

### **Método 3: PowerShell (Windows)**

#### **Obtener alertas activas:**
```powershell
$alerts = Invoke-RestMethod -Uri "http://localhost:8000/security/alerts?is_resolved=false" -Headers @{"Authorization"="Bearer junior123"}
$alerts.alerts
```

#### **Resolver alerta:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/security/alerts/1/resolve?resolution_notes=Attack mitigated" -Method PUT -Headers @{"Authorization"="Bearer junior123"}
```

#### **Verificar dashboard:**
```powershell
$dashboard = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/dashboard/overview" -Headers @{"Authorization"="Bearer junior123"}
$dashboard.data.security.threat_level  # Debe mostrar "low"
```

---

## 📊 **ENDPOINTS DISPONIBLES**

| Método | Endpoint | Descripción | Parámetros |
|--------|----------|-------------|------------|
| `GET` | `/security/alerts` | Listar todas las alertas | `?is_resolved=false` |
| `GET` | `/security/alerts?is_resolved=false` | Solo alertas activas | - |
| `GET` | `/security/alerts?is_resolved=true` | Solo alertas resueltas | - |
| `PUT` | `/security/alerts/{id}/resolve` | Resolver alerta específica | `?resolution_notes=texto` |
| `GET` | `/api/v1/dashboard/overview` | Estado del dashboard | - |

---

## 🔄 **FLUJO COMPLETO DE RESOLUCIÓN**

### **1. Detectar Problema**
```
Dashboard ROJO → threat_level: "high" → Hay alertas activas
```

### **2. Identificar Alertas**
```bash
GET /security/alerts?is_resolved=false
```

### **3. Resolver Alertas**
```bash
PUT /security/alerts/{id}/resolve?resolution_notes="Problema resuelto"
```

### **4. Verificar Resultado**
```bash
GET /api/v1/dashboard/overview
# threat_level debe ser "low"
# top_threats debe estar vacío []
```

---

## 🧪 **EJEMPLO PRÁCTICO COMPLETO**

### **Escenario**: Dashboard en rojo por ataque de brute force

```bash
# 1. Verificar estado actual
curl -H "Authorization: Bearer junior123" http://localhost:8000/api/v1/dashboard/overview
# Resultado: threat_level: "high"

# 2. Ver alertas activas
curl -H "Authorization: Bearer junior123" "http://localhost:8000/security/alerts?is_resolved=false"
# Resultado: 1 alerta de brute_force_detected

# 3. Resolver la alerta
curl -X PUT -H "Authorization: Bearer junior123" \
  "http://localhost:8000/security/alerts/1/resolve?resolution_notes=IPs bloqueadas y medidas de seguridad reforzadas"
# Resultado: {"success": true, "message": "Alert resolved successfully"}

# 4. Verificar que dashboard volvió a verde
curl -H "Authorization: Bearer junior123" http://localhost:8000/api/v1/dashboard/overview
# Resultado: threat_level: "low", top_threats: []
```

---

## ⚡ **COMANDOS RÁPIDOS**

### **Resolver todas las alertas de una vez:**
```bash
python scripts/resolve_alerts.py --auto
```

### **Ver solo el estado del dashboard:**
```bash
curl -s -H "Authorization: Bearer junior123" http://localhost:8000/api/v1/dashboard/overview | grep -o '"threat_level":"[^"]*"'
```

### **Contar alertas activas:**
```bash
curl -s -H "Authorization: Bearer junior123" "http://localhost:8000/security/alerts?is_resolved=false" | grep -o '"id":[0-9]*' | wc -l
```

---

## 🎯 **NOTAS IMPORTANTES**

### **Resolución de Alertas**
- ✅ Las alertas resueltas **NO** aparecen en `top_threats`
- ✅ Solo alertas **NO resueltas** afectan el `threat_level`
- ✅ El `threat_level` cambia automáticamente cuando se resuelven alertas críticas

### **Tipos de Threat Level**
- 🟢 **`"low"`**: Sin amenazas activas o solo amenazas menores
- 🟡 **`"medium"`**: Amenazas activas de severidad MEDIUM
- 🔴 **`"high"`**: Amenazas activas de severidad CRITICAL

### **Buenas Prácticas**
- 📝 Siempre incluir `resolution_notes` descriptivas
- 🔍 Verificar que el problema real esté resuelto antes de marcar la alerta
- 📊 Monitorear el dashboard después de resolver alertas
- 🔄 Usar el script automático para resoluciones masivas

---

## 🚀 **AUTOMATIZACIÓN**

### **Cron Job para Auto-Resolución (Opcional)**
```bash
# Resolver alertas automáticamente cada hora
0 * * * * cd /path/to/project && python scripts/resolve_alerts.py --auto >> logs/auto_resolve.log 2>&1
```

### **Monitoreo Continuo**
```bash
# Script para monitorear estado del dashboard
while true; do
  threat_level=$(curl -s -H "Authorization: Bearer junior123" http://localhost:8000/api/v1/dashboard/overview | grep -o '"threat_level":"[^"]*"' | cut -d'"' -f4)
  echo "$(date): Dashboard threat level: $threat_level"
  sleep 60
done
```

---

*Documento actualizado el: 2026-01-20 12:40:00*  
*Estado: SISTEMA DE RESOLUCIÓN DE ALERTAS COMPLETAMENTE FUNCIONAL ✅*