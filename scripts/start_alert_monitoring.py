#!/usr/bin/env python3
"""
Script para iniciar monitoreo automático de alertas
Ejecuta verificaciones periódicas del sistema de alertas
"""
import sys
import os
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# Agregar el directorio raíz al path para imports
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

from services import AlertService

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/alert_monitoring.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("alert_monitoring")

class AlertMonitor:
    """Monitor automático de alertas para ejecución continua"""
    
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./mercadopago_enterprise.db")
        self.engine = create_engine(self.database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Crear directorio de logs si no existe
        os.makedirs("logs", exist_ok=True)
        
        logger.info("AlertMonitor initialized")
    
    async def start_monitoring(self, check_interval_seconds: int = 300):
        """
        Inicia monitoreo continuo de alertas
        
        Args:
            check_interval_seconds: Intervalo entre verificaciones (default: 5 minutos)
        """
        logger.info(f"Starting alert monitoring - Check interval: {check_interval_seconds}s")
        
        while True:
            try:
                await self.run_alert_check()
                
                # Esperar hasta la próxima verificación
                await asyncio.sleep(check_interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("Alert monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in alert monitoring loop: {str(e)}")
                # Esperar un poco antes de reintentar
                await asyncio.sleep(60)
    
    async def run_alert_check(self):
        """Ejecuta una verificación de alertas"""
        start_time = datetime.utcnow()
        
        try:
            db = self.SessionLocal()
            
            try:
                alert_service = AlertService(db)
                alerts_generated = alert_service.check_all_alerts()
                
                duration = (datetime.utcnow() - start_time).total_seconds()
                
                if alerts_generated:
                    logger.warning(f"Alert check completed - {len(alerts_generated)} alerts generated in {duration:.2f}s")
                    
                    # Log detalles de alertas críticas
                    critical_alerts = [a for a in alerts_generated if a.level.value == "critical"]
                    if critical_alerts:
                        logger.critical(f"CRITICAL ALERTS DETECTED: {len(critical_alerts)} critical alerts require immediate attention")
                else:
                    logger.info(f"Alert check completed - No alerts generated in {duration:.2f}s")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in alert check: {str(e)}")
    
    def run_single_check(self):
        """Ejecuta una sola verificación de alertas (modo síncrono)"""
        try:
            db = self.SessionLocal()
            
            try:
                alert_service = AlertService(db)
                alerts_generated = alert_service.check_all_alerts()
                
                print(f"\n{'='*60}")
                print(f"ALERT CHECK RESULTS - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*60}")
                
                if alerts_generated:
                    print(f"🚨 {len(alerts_generated)} alerts generated:")
                    
                    for alert in alerts_generated:
                        level_icon = "🔥" if alert.level.value == "critical" else "⚠️" if alert.level.value == "warning" else "ℹ️"
                        print(f"{level_icon} [{alert.level.value.upper()}] {alert.title}")
                        print(f"   {alert.message}")
                        print(f"   Value: {alert.current_value} | Threshold: {alert.threshold_value}")
                        print()
                else:
                    print("✅ No alerts generated - System operating normally")
                
                print(f"{'='*60}\n")
                
                return len(alerts_generated)
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in single alert check: {str(e)}")
            print(f"❌ Error checking alerts: {str(e)}")
            return -1

def main():
    """Función principal del script"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Alert Monitoring System for MercadoPago Enterprise",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--mode",
        choices=["continuous", "single"],
        default="single",
        help="Monitoring mode: continuous (daemon) or single check"
    )
    
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Check interval in seconds (continuous mode only)"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configurar nivel de logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validar argumentos
    if args.interval <= 0:
        print("ERROR: --interval must be positive", file=sys.stderr)
        return 2
    
    print(f"Alert Monitoring System - {datetime.utcnow().isoformat()}")
    print(f"Mode: {args.mode}")
    if args.mode == "continuous":
        print(f"Check interval: {args.interval} seconds")
    print()
    
    try:
        monitor = AlertMonitor()
        
        if args.mode == "continuous":
            # Modo continuo (daemon)
            print("Starting continuous monitoring... (Press Ctrl+C to stop)")
            asyncio.run(monitor.start_monitoring(args.interval))
            return 0
        else:
            # Modo single check
            alert_count = monitor.run_single_check()
            
            # Código de salida basado en alertas
            if alert_count == -1:
                return 2  # Error
            elif alert_count > 0:
                return 1  # Alertas encontradas
            else:
                return 0  # Sin alertas
        
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
        return 130  # Standard exit code for SIGINT
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        print(f"UNEXPECTED ERROR: {str(e)}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)