#!/usr/bin/env python3
"""
Script de Reconciliación Diaria - MercadoPago Enterprise
Ejecuta reconciliación automática de pagos pendientes con MercadoPago API

Uso:
    python scripts/daily_reconcile.py [opciones]

Opciones:
    --hours-back N          Horas hacia atrás para buscar pagos (default: 24)
    --dry-run              Solo mostrar qué se haría, sin aplicar cambios
    --no-auto-correction   Deshabilitar corrección automática
    --batch-size N         Tamaño de lote para procesamiento (default: 50)
    --verbose              Mostrar información detallada
    --config-fil
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

from services import ReconciliationService, ReconciliationConfig
from models import Base

# Configurar logging para script
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/daily_reconcile.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("daily_reconcile_script")

class ReconciliationScript:
    """
    Script enterprise para reconciliación diaria
    Diseñado para ejecución por cron con manejo robusto de errores
    """
    
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./mercadopago_enterprise.db")
        self.engine = create_engine(self.database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Crear directorio de logs si no existe
        os.makedirs("logs", exist_ok=True)
        
        logger.info("ReconciliationScript initialized")
    
    def execute_reconciliation(
        self,
        hours_back: int = 24,
        enable_auto_correction: bool = True,
        dry_run: bool = False,
        batch_size: int = 50,
        include_pending: bool = False
    ) -> int:
        """
        Ejecuta el proceso de reconciliación
        Retorna código de salida: 0=éxito, 1=advertencias, 2=errores críticos
        """
        start_time = datetime.utcnow()
        logger.info(f"Starting daily reconciliation - Hours back: {hours_back}, Auto-correction: {enable_auto_correction}")
        
        try:
            # Crear sesión de base de datos
            db = self.SessionLocal()
            
            try:
                # Configurar reconciliación
                config = ReconciliationConfig(
                    hours_back=hours_back,
                    max_retries=3,
                    retry_delay_seconds=5,
                    batch_size=batch_size,
                    enable_auto_correction=enable_auto_correction,
                    dry_run=dry_run,
                    include_pending_payments=include_pending,
                    ghl_tag_prefix="MP_PAGADO",
                    report_formats=["json", "csv"],
                    notification_webhooks=[]
                )
                
                # Crear y ejecutar servicio
                service = ReconciliationService(db, config)
                result = service.execute_reconciliation()
                
                # Determinar código de salida
                exit_code = self._determine_exit_code(result)
                
                # Log resultado
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.info(f"Reconciliation completed - Status: {result['status']}, Duration: {duration:.2f}s, Exit code: {exit_code}")
                
                # Imprimir resumen
                self._print_summary(result)
                
                return exit_code
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Critical error in reconciliation script: {str(e)}")
            print(f"CRITICAL ERROR: {str(e)}", file=sys.stderr)
            return 2
    
    def _determine_exit_code(self, result) -> int:
        """Determina código de salida basado en el resultado"""
        if result["status"] == "success":
            return 0
        elif result["status"] in ["warning"]:
            return 1
        else:  # error, critical
            return 2
    
    def _print_summary(self, result) -> None:
        """Imprime resumen del resultado para logs de cron"""
        print("\n" + "="*80)
        print("DAILY RECONCILIATION SUMMARY")
        print("="*80)
        print(f"Execution ID: {result['execution_id']}")
        print(f"Status: {result['status'].upper()}")
        print(f"Duration: {result['duration_seconds']:.2f} seconds")
        print(f"Payments Checked: {result['total_payments_checked']}")
        print(f"Discrepancies Found: {len(result['discrepancies'])}")
        print(f"Corrections Applied: {result['corrections_applied']}")
        print(f"MP API Calls: {result['mp_api_calls']}")
        print(f"GHL API Calls: {result['ghl_api_calls']}")
        
        if result["summary"]:
            print("\nDISCREPANCIES BY TYPE:")
            for disc_type, count in result["summary"].get("by_type", {}).items():
                print(f"  {disc_type}: {count}")
            
            print("\nDISCREPANCIES BY SEVERITY:")
            for severity, count in result["summary"].get("by_severity", {}).items():
                print(f"  {severity}: {count}")
        
        if result["errors"]:
            print(f"\nERRORS ({len(result['errors'])}):")
            for error in result["errors"][:5]:  # Mostrar solo los primeros 5
                print(f"  - {error}")
            if len(result["errors"]) > 5:
                print(f"  ... and {len(result['errors']) - 5} more errors")
        
        if result["warnings"]:
            print(f"\nWARNINGS ({len(result['warnings'])}):")
            for warning in result["warnings"][:3]:  # Mostrar solo las primeras 3
                print(f"  - {warning}")
            if len(result["warnings"]) > 3:
                print(f"  ... and {len(result['warnings']) - 3} more warnings")
        
        print("="*80)
        
        # Información de reportes
        reports_dir = "reports"
        if os.path.exists(reports_dir):
            report_files = [f for f in os.listdir(reports_dir) if result['execution_id'] in f]
            if report_files:
                print(f"REPORTS GENERATED ({len(report_files)}):")
                for report_file in report_files:
                    file_path = os.path.join(reports_dir, report_file)
                    file_size = os.path.getsize(file_path)
                    print(f"  - {report_file} ({file_size} bytes)")
        
        print("="*80 + "\n")

def main():
    """Función principal del script"""
    parser = argparse.ArgumentParser(
        description="Daily Reconciliation Script for MercadoPago Enterprise",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--hours-back",
        type=int,
        default=24,
        help="Number of hours back to check for payments"
    )
    
    parser.add_argument(
        "--no-auto-correction",
        action="store_true",
        help="Disable automatic corrections"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (no actual changes)"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for processing payments"
    )
    
    parser.add_argument(
        "--include-pending",
        action="store_true",
        help="Include pending payments in reconciliation"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress output (except errors)"
    )
    
    args = parser.parse_args()
    
    # Configurar nivel de logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    
    # Validar argumentos
    if args.hours_back <= 0:
        print("ERROR: --hours-back must be positive", file=sys.stderr)
        return 2
    
    if args.batch_size <= 0:
        print("ERROR: --batch-size must be positive", file=sys.stderr)
        return 2
    
    # Mostrar configuración si no está en modo quiet
    if not args.quiet:
        print(f"Daily Reconciliation Script - {datetime.utcnow().isoformat()}")
        print(f"Configuration:")
        print(f"  Hours back: {args.hours_back}")
        print(f"  Auto-correction: {not args.no_auto_correction}")
        print(f"  Dry run: {args.dry_run}")
        print(f"  Batch size: {args.batch_size}")
        print(f"  Include pending: {args.include_pending}")
        print()
    
    # Ejecutar reconciliación
    try:
        script = ReconciliationScript()
        exit_code = script.execute_reconciliation(
            hours_back=args.hours_back,
            enable_auto_correction=not args.no_auto_correction,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
            include_pending=args.include_pending
        )
        
        return exit_code
        
    except KeyboardInterrupt:
        print("\nReconciliation interrupted by user", file=sys.stderr)
        return 130  # Standard exit code for SIGINT
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        print(f"UNEXPECTED ERROR: {str(e)}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)