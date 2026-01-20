# 🛠️ Comandos Útiles

Referencia rápida de comandos para trabajar con el proyecto.

---

## 🚀 Inicio Rápido

```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar entorno
cp .env.example .env

# Inicializar base de datos
python scripts/recreate_db.py

# Iniciar servidor
uvicorn main:app --reload

# Probar sistema
python tests/test_quick_payment.py
```

---

## 🗄️ Base de Datos

```bash
# Inicializar BD (primera vez)
python scripts/init_db.py

# Recrear BD desde cero
python scripts/recreate_db.py

# Actualizar esquema (agregar columnas)
python scripts/update_db.py

# Ver estructura de BD
sqlite3 mercadopago_enterprise.db ".schema"

# Ver datos de una tabla
sqlite3 mercadopago_enterprise.db "SELECT * FROM payments;"
```

---

## 🧪 Testing

```bash
# Test rápido del MVP
python tests/test_quick_payment.py

# Tests de seguridad completos
python tests/test_security.py

# Tests de OAuth
python tests/test_oauth.py

# Test de integración GHL
python tests/test_webhook_ghl.py

# Test completo del flujo
python tests/test_ghl_bridge.py

# Verificar token
python tests/test_token.py

# Ver estado de un pago
python tests/verify_payment.py <preference_id>
```

---

## 💳 Gestión de Pagos

```bash
# Aprobar pago manualmente
python scripts/force_approve.py <preference_id>

# Aprobar pago (versión Windows sin emojis)
python scripts/force_approve_simple.py <preference_id>

# Crear pago via API
curl -X POST http://localhost:8000/payments/create \
  -H "Authorization: Bearer tu_admin_token" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "test@example.com",
    "customer_name": "Test User",
    "ghl_contact_id": "ghl_123",
    "amount": 100,
    "description": "Test Payment",
    "created_by": "Admin"
  }'

# Ver detalles de un pago
curl -H "Authorization: Bearer tu_admin_token" \
  http://localhost:8000/payments/1
```

---

## 🔐 OAuth

```bash
# Iniciar autorización OAuth
curl -X POST http://localhost:8000/oauth/authorize \
  -H "Authorization: Bearer tu_admin_token" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "cliente_123",
    "client_name": "Mi Empresa",
    "client_email": "empresa@example.com"
  }'

# Listar cuentas OAuth
curl -H "Authorization: Bearer tu_admin_token" \
  http://localhost:8000/oauth/accounts

# Renovar token manualmente
curl -X POST http://localhost:8000/oauth/refresh/1 \
  -H "Authorization: Bearer tu_admin_token"

# Desactivar cuenta OAuth
curl -X DELETE http://localhost:8000/oauth/accounts/1 \
  -H "Authorization: Bearer tu_admin_token"
```

---

## 📊 Monitoreo y Auditoría

```bash
# Ver métricas del sistema
curl -H "Authorization: Bearer tu_admin_token" \
  http://localhost:8000/metrics

# Ver logs de auditoría
curl -H "Authorization: Bearer tu_admin_token" \
  http://localhost:8000/audit/logs?limit=50

# Ver logs de un pago específico
curl -H "Authorization: Bearer tu_admin_token" \
  http://localhost:8000/audit/logs?payment_id=1

# Ver alertas de seguridad
curl -H "Authorization: Bearer tu_admin_token" \
  http://localhost:8000/security/alerts

# Ver alertas no resueltas
curl -H "Authorization: Bearer tu_admin_token" \
  http://localhost:8000/security/alerts?is_resolved=false

# Resolver alerta
curl -X PUT http://localhost:8000/security/alerts/1/resolve \
  -H "Authorization: Bearer tu_admin_token" \
  -H "Content-Type: application/json" \
  -d '{"resolution_notes": "Falsa alarma, todo OK"}'
```

---

## 🔧 Servidor

```bash
# Iniciar en modo desarrollo
uvicorn main:app --reload

# Iniciar en puerto específico
uvicorn main:app --port 8001

# Iniciar en producción
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Ver logs en tiempo real
uvicorn main:app --reload --log-level debug

# Health check
curl http://localhost:8000/health
```

---

## 🐛 Debugging

```bash
# Ver logs del servidor
# (Los logs aparecen en la terminal donde corre uvicorn)

# Ver estructura de BD
sqlite3 mercadopago_enterprise.db ".tables"

# Ver últimos pagos
sqlite3 mercadopago_enterprise.db \
  "SELECT id, customer_email, status, created_at FROM payments ORDER BY created_at DESC LIMIT 10;"

# Ver últimos logs de auditoría
sqlite3 mercadopago_enterprise.db \
  "SELECT action, description, timestamp FROM audit_logs ORDER BY timestamp DESC LIMIT 10;"

# Ver alertas de seguridad
sqlite3 mercadopago_enterprise.db \
  "SELECT alert_type, severity, title, created_at FROM security_alerts WHERE is_resolved = 0;"

# Contar pagos por estado
sqlite3 mercadopago_enterprise.db \
  "SELECT status, COUNT(*) FROM payments GROUP BY status;"
```

---

## 📦 Deployment

```bash
# Configurar variables de entorno para producción
export DATABASE_URL="postgresql://user:pass@host:5432/db"
export ENVIRONMENT="production"
export MP_ACCESS_TOKEN="prod_token"
export GHL_API_KEY="prod_ghl_key"
export ADMIN_API_KEY="prod_admin_key"

# Inicializar BD en producción
python scripts/recreate_db.py

# Iniciar servidor en producción
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Con gunicorn (recomendado para producción)
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## 🔄 Git

```bash
# Inicializar repositorio
git init

# Agregar archivos
git add .

# Commit inicial
git commit -m "Initial commit: MercadoPago Enterprise System"

# Agregar remote
git remote add origin <repository-url>

# Push
git push -u origin main

# Ver estado
git status

# Ver cambios
git diff
```

---

## 🧹 Limpieza

```bash
# Limpiar cache de Python
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Limpiar base de datos (cuidado!)
rm mercadopago_enterprise.db
python scripts/recreate_db.py

# Reinstalar dependencias
pip uninstall -r requirements.txt -y
pip install -r requirements.txt
```

---

## 📝 Desarrollo

```bash
# Crear nueva rama
git checkout -b feature/nueva-funcionalidad

# Ejecutar tests antes de commit
python tests/test_quick_payment.py
python tests/test_security.py

# Ver documentación de API
# Abrir en navegador: http://localhost:8000/docs

# Ver documentación alternativa
# Abrir en navegador: http://localhost:8000/redoc
```

---

## 🔍 Búsqueda y Análisis

```bash
# Buscar en código
grep -r "función_especifica" .

# Contar líneas de código
find . -name "*.py" -not -path "./__pycache__/*" | xargs wc -l

# Ver dependencias
pip list

# Ver dependencias desactualizadas
pip list --outdated

# Generar requirements.txt actualizado
pip freeze > requirements.txt
```

---

## 💡 Tips Útiles

### Variables de Entorno Rápidas
```bash
# Desarrollo
export ENVIRONMENT=development
export ADMIN_API_KEY=test_admin_token_123

# Producción
export ENVIRONMENT=production
export ADMIN_API_KEY=prod_secure_token_xyz
```

### Alias Útiles (agregar a .bashrc o .zshrc)
```bash
alias mp-start="uvicorn main:app --reload"
alias mp-test="python tests/test_quick_payment.py"
alias mp-db="python scripts/recreate_db.py"
alias mp-logs="tail -f logs/app.log"
```

### Atajos de Teclado en Terminal
- `Ctrl+C` - Detener servidor
- `Ctrl+Z` - Suspender proceso
- `Ctrl+L` - Limpiar terminal
- `↑` - Comando anterior

---

## 📚 Recursos

- **Documentación FastAPI:** https://fastapi.tiangolo.com/
- **Documentación SQLAlchemy:** https://docs.sqlalchemy.org/
- **API MercadoPago:** https://www.mercadopago.com.ar/developers
- **API GoHighLevel:** https://highlevel.stoplight.io/

---

## 🆘 Ayuda

```bash
# Ver ayuda de Python
python --help

# Ver ayuda de pip
pip --help

# Ver ayuda de uvicorn
uvicorn --help

# Ver versión de Python
python --version

# Ver versión de pip
pip --version
```

---

**Tip:** Guarda este archivo como referencia rápida. Todos estos comandos están probados y funcionan. 🚀