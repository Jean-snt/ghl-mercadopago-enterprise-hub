# 🚀 Guía de Inicio Rápido

## Instalación en 5 Minutos

### 1. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 2. Configurar Variables de Entorno
```bash
cp .env.example .env
```

Editar `.env` con tus valores (mínimo requerido):
```bash
ADMIN_API_KEY=tu_token_admin_123
ENVIRONMENT=development
```

### 3. Inicializar Base de Datos
```bash
python scripts/recreate_db.py
```

### 4. Iniciar Servidor
```bash
uvicorn main:app --reload
```

### 5. Probar el Sistema
```bash
python tests/test_quick_payment.py
```

## ✅ Verificación

Si ves este mensaje, todo funciona:
```
✅ ¡ÉXITO! Pago creado correctamente
🎉 MVP Día 1 completado: El endpoint devuelve el init_point exitosamente
```

## 🎯 Próximos Pasos

1. **Crear un pago:**
   ```bash
   curl -X POST http://localhost:8000/payments/create \
     -H "Authorization: Bearer tu_token_admin_123" \
     -H "Content-Type: application/json" \
     -d '{
       "customer_email": "test@example.com",
       "customer_name": "Test User",
       "ghl_contact_id": "ghl_123",
       "amount": 100,
       "description": "Test Payment",
       "created_by": "Admin"
     }'
   ```

2. **Aprobar el pago (desarrollo):**
   ```bash
   python scripts/force_approve_simple.py <preference_id>
   ```

3. **Verificar integración GHL:**
   ```bash
   python tests/test_webhook_ghl.py
   ```

## 📚 Documentación Completa

Ver [README.md](README.md) para documentación completa.

## 🆘 Problemas Comunes

### Error: "ADMIN_API_KEY no configurado"
**Solución:** Edita `.env` y agrega `ADMIN_API_KEY=tu_token`

### Error: "Base de datos no encontrada"
**Solución:** Ejecuta `python scripts/recreate_db.py`

### Error: "Module not found"
**Solución:** Ejecuta `pip install -r requirements.txt`

### Puerto 8000 en uso
**Solución:** Usa otro puerto: `uvicorn main:app --port 8001`

## 💡 Tips

- Usa `ENVIRONMENT=development` para testing sin APIs reales
- Revisa logs del servidor para debugging
- Usa `python tests/verify_payment.py <id>` para ver estado de pagos
- Consulta `/docs` para documentación detallada

---

¡Listo para empezar! 🎉