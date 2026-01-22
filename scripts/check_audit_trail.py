#!/usr/bin/env python3
"""
Script de Trazabilidad - Monitoreo en Tiempo Real
Permite ver quién ha estado 'tocando' el sistema según documento oficial
"""
import os
import sys
import json
import time
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Agregar el directorio padre al path para importar modelos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import sessionmaker
from models import CriticalAuditLog
from services.critical_audit_service import CriticalAuditService
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mercadopago_enterprise.db")

class AuditTrailMonitor:
    """
    Monitor de trazabilidad de auditoría crítica
    Permite monitoreo en tiempo real de acciones críticas
    """
    
    def __init__(self):
        self.engine = create_engine(DATABASE_URL, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def get_recent_activity(self, minutes: int = 60, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Obtiene actividad reciente del sistema
        """
        try:
            db = self.SessionLocal()
            audit_service = CriticalAuditService(db)
            
            # Convertir minutos a horas para el servicio
            hours_back = max(1, minutes / 60)
            
            audit_logs = audit_service.get_audit_trail(
                limit=limit,
                hours_back=int(hours_back)
            )
            
            activity = []
            for log in audit_logs:
                activity.append({
                    "id": log.id,
                    "timestamp": log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "user": log.user_email,
                    "action": log.action,
                    "entity": log.entity or "N/A",
                    "entity_id": log.entity_id or "N/A",
                    "ip": log.ip_address,
                    "tenant": log.tenant_id or "system",
                    "details": json.loads(log.details) if log.details else {}
                })
            
            db.close()
            return activity
            
        except Exception as e:
            print(f"❌ Error obteniendo actividad reciente: {str(e)}")
            return []
    
    def get_user_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Obtiene resumen de actividad por usuario
        """
        try:
            db = self.SessionLocal()
            audit_service = CriticalAuditService(db)
            
            # Obtener estadísticas
            stats = audit_service.get_audit_stats(hours)
            
            # Obtener actividad por usuario
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            user_activity = db.query(CriticalAuditLog).filter(
                CriticalAuditLog.created_at >= cutoff_time
            ).all()
            
            # Agrupar por usuario
            users = {}
            for log in user_activity:
                user = log.user_email
                if user not in users:
                    users[user] = {
                        "total_actions": 0,
                        "actions": {},
                        "ips": set(),
                        "tenants": set(),
                        "first_activity": log.created_at,
                        "last_activity": log.created_at
                    }
                
                users[user]["total_actions"] += 1
                
                # Contar acciones por tipo
                action = log.action
                if action not in users[user]["actions"]:
                    users[user]["actions"][action] = 0
                users[user]["actions"][action] += 1
                
                # Agregar IPs y tenants
                users[user]["ips"].add(log.ip_address)
                if log.tenant_id:
                    users[user]["tenants"].add(log.tenant_id)
                
                # Actualizar timestamps
                if log.created_at < users[user]["first_activity"]:
                    users[user]["first_activity"] = log.created_at
                if log.created_at > users[user]["last_activity"]:
                    users[user]["last_activity"] = log.created_at
            
            # Convertir sets a listas para serialización
            for user_data in users.values():
                user_data["ips"] = list(user_data["ips"])
                user_data["tenants"] = list(user_data["tenants"])
                user_data["first_activity"] = user_data["first_activity"].strftime("%Y-%m-%d %H:%M:%S")
                user_data["last_activity"] = user_data["last_activity"].strftime("%Y-%m-%d %H:%M:%S")
            
            db.close()
            
            return {
                "time_range_hours": hours,
                "total_users": len(users),
                "users": users,
                "system_stats": stats
            }
            
        except Exception as e:
            print(f"❌ Error obteniendo resumen de usuarios: {str(e)}")
            return {}
    
    def detect_suspicious_activity(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Detecta actividad sospechosa en el sistema
        """
        try:
            db = self.SessionLocal()
            audit_service = CriticalAuditService(db)
            
            suspicious = audit_service.get_suspicious_activity(hours)
            
            db.close()
            return suspicious
            
        except Exception as e:
            print(f"❌ Error detectando actividad sospechosa: {str(e)}")
            return []
    
    def monitor_real_time(self, interval: int = 30):
        """
        Monitoreo en tiempo real con actualizaciones periódicas
        """
        print("🔍 Iniciando monitoreo en tiempo real de auditoría crítica...")
        print(f"⏱️  Actualizando cada {interval} segundos (Ctrl+C para salir)")
        print("="*80)
        
        last_check = datetime.utcnow()
        
        try:
            while True:
                # Limpiar pantalla (compatible con Windows y Unix)
                os.system('cls' if os.name == 'nt' else 'clear')
                
                print(f"🔐 MONITOREO DE AUDITORÍA CRÍTICA - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
                print("="*80)
                
                # Obtener actividad desde la última verificación
                minutes_since_last = max(1, int((datetime.utcnow() - last_check).total_seconds() / 60))
                recent_activity = self.get_recent_activity(minutes=minutes_since_last, limit=10)
                
                if recent_activity:
                    print(f"📊 ACTIVIDAD RECIENTE (últimos {minutes_since_last} minutos):")
                    print("-" * 80)
                    for activity in recent_activity[:10]:
                        print(f"🕐 {activity['timestamp']} | {activity['user']:<20} | {activity['action']:<20} | {activity['ip']}")
                        if activity['entity'] != "N/A":
                            print(f"   └─ {activity['entity']}: {activity['entity_id']}")
                else:
                    print("✅ Sin actividad reciente")
                
                print("\n" + "="*80)
                
                # Resumen de usuarios activos (última hora)
                user_summary = self.get_user_summary(hours=1)
                if user_summary.get("users"):
                    print("👥 USUARIOS ACTIVOS (última hora):")
                    print("-" * 80)
                    for user, data in list(user_summary["users"].items())[:5]:
                        print(f"👤 {user:<30} | {data['total_actions']:>3} acciones | IPs: {len(data['ips'])}")
                
                # Detectar actividad sospechosa
                suspicious = self.detect_suspicious_activity(hours=1)
                if suspicious:
                    print("\n🚨 ACTIVIDAD SOSPECHOSA DETECTADA:")
                    print("-" * 80)
                    for alert in suspicious:
                        print(f"⚠️  {alert['type']}: {alert.get('ip_address', 'N/A')} ({alert.get('failure_count', 0)} intentos)")
                
                print(f"\n⏱️  Próxima actualización en {interval} segundos... (Ctrl+C para salir)")
                
                last_check = datetime.utcnow()
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n👋 Monitoreo detenido por el usuario")
    
    def generate_report(self, hours: int = 24, output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Genera reporte completo de auditoría
        """
        try:
            print(f"📊 Generando reporte de auditoría (últimas {hours} horas)...")
            
            # Obtener datos
            recent_activity = self.get_recent_activity(minutes=hours*60, limit=1000)
            user_summary = self.get_user_summary(hours=hours)
            suspicious = self.detect_suspicious_activity(hours=hours)
            
            report = {
                "report_metadata": {
                    "generated_at": datetime.utcnow().isoformat(),
                    "time_range_hours": hours,
                    "total_events": len(recent_activity)
                },
                "recent_activity": recent_activity,
                "user_summary": user_summary,
                "suspicious_activity": suspicious,
                "summary": {
                    "total_events": len(recent_activity),
                    "unique_users": len(user_summary.get("users", {})),
                    "suspicious_alerts": len(suspicious),
                    "most_active_user": max(user_summary.get("users", {}).items(), 
                                          key=lambda x: x[1]["total_actions"])[0] if user_summary.get("users") else None
                }
            }
            
            # Guardar archivo si se especifica
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                print(f"💾 Reporte guardado en: {output_file}")
            
            return report
            
        except Exception as e:
            print(f"❌ Error generando reporte: {str(e)}")
            return {}

def main():
    """Función principal con argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        description="🔐 Monitor de Trazabilidad de Auditoría Crítica",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python scripts/check_audit_trail.py --recent 30        # Actividad de últimos 30 minutos
  python scripts/check_audit_trail.py --users 24         # Resumen de usuarios (24 horas)
  python scripts/check_audit_trail.py --monitor          # Monitoreo en tiempo real
  python scripts/check_audit_trail.py --report --output audit_report.json
  python scripts/check_audit_trail.py --suspicious       # Solo actividad sospechosa
        """
    )
    
    parser.add_argument("--recent", type=int, metavar="MINUTES", 
                       help="Mostrar actividad reciente (minutos)")
    parser.add_argument("--users", type=int, metavar="HOURS", 
                       help="Resumen de actividad por usuario (horas)")
    parser.add_argument("--monitor", action="store_true", 
                       help="Monitoreo en tiempo real")
    parser.add_argument("--report", action="store_true", 
                       help="Generar reporte completo")
    parser.add_argument("--suspicious", action="store_true", 
                       help="Mostrar solo actividad sospechosa")
    parser.add_argument("--output", type=str, metavar="FILE", 
                       help="Archivo de salida para reporte")
    parser.add_argument("--hours", type=int, default=24, 
                       help="Rango de tiempo en horas (default: 24)")
    parser.add_argument("--interval", type=int, default=30, 
                       help="Intervalo de actualización para monitoreo (segundos)")
    
    args = parser.parse_args()
    
    # Si no se especifica ninguna opción, mostrar ayuda
    if not any([args.recent, args.users, args.monitor, args.report, args.suspicious]):
        parser.print_help()
        return
    
    monitor = AuditTrailMonitor()
    
    try:
        if args.recent:
            print(f"📊 ACTIVIDAD RECIENTE (últimos {args.recent} minutos)")
            print("="*80)
            activity = monitor.get_recent_activity(minutes=args.recent)
            
            if activity:
                for item in activity:
                    print(f"🕐 {item['timestamp']} | {item['user']:<20} | {item['action']:<20} | {item['ip']}")
                    if item['entity'] != "N/A":
                        print(f"   └─ {item['entity']}: {item['entity_id']}")
                print(f"\n✅ Total: {len(activity)} eventos")
            else:
                print("✅ Sin actividad reciente")
        
        elif args.users:
            print(f"👥 RESUMEN DE USUARIOS (últimas {args.users} horas)")
            print("="*80)
            summary = monitor.get_user_summary(hours=args.users)
            
            if summary.get("users"):
                for user, data in summary["users"].items():
                    print(f"\n👤 {user}")
                    print(f"   📊 Total acciones: {data['total_actions']}")
                    print(f"   🌐 IPs únicas: {len(data['ips'])} ({', '.join(data['ips'])})")
                    print(f"   🏢 Tenants: {len(data['tenants'])} ({', '.join(data['tenants']) if data['tenants'] else 'system'})")
                    print(f"   ⏰ Período: {data['first_activity']} - {data['last_activity']}")
                    print(f"   🔧 Acciones: {', '.join([f'{k}({v})' for k, v in data['actions'].items()])}")
                
                print(f"\n✅ Total usuarios activos: {summary['total_users']}")
            else:
                print("✅ Sin actividad de usuarios")
        
        elif args.suspicious:
            print(f"🚨 ACTIVIDAD SOSPECHOSA (últimas {args.hours} horas)")
            print("="*80)
            suspicious = monitor.detect_suspicious_activity(hours=args.hours)
            
            if suspicious:
                for alert in suspicious:
                    print(f"⚠️  {alert['type'].upper()}")
                    print(f"   🌐 IP: {alert.get('ip_address', 'N/A')}")
                    print(f"   📊 Intentos: {alert.get('failure_count', 0)}")
                    print(f"   👥 Usuarios: {', '.join(alert.get('users_attempted', []))}")
                    print(f"   ⏰ Período: {alert.get('time_range', 'N/A')}")
                    print()
                
                print(f"✅ Total alertas: {len(suspicious)}")
            else:
                print("✅ Sin actividad sospechosa detectada")
        
        elif args.monitor:
            monitor.monitor_real_time(interval=args.interval)
        
        elif args.report:
            report = monitor.generate_report(hours=args.hours, output_file=args.output)
            
            if not args.output:
                print("\n📊 RESUMEN DEL REPORTE:")
                print("="*80)
                print(f"📅 Período: {report['report_metadata']['time_range_hours']} horas")
                print(f"📊 Total eventos: {report['summary']['total_events']}")
                print(f"👥 Usuarios únicos: {report['summary']['unique_users']}")
                print(f"🚨 Alertas sospechosas: {report['summary']['suspicious_alerts']}")
                if report['summary']['most_active_user']:
                    print(f"🏆 Usuario más activo: {report['summary']['most_active_user']}")
    
    except Exception as e:
        print(f"❌ Error ejecutando comando: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()