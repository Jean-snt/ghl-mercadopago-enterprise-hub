#!/usr/bin/env python3
"""
Script para archivar logs de alertas y auditoría en Amazon S3
Permite backup manual y automático con retención a largo plazo
"""
import sys
import os
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Agregar el directorio raíz al path para imports
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from services.s3_archive_service import S3ArchiveService, S3Config

def setup_database():
    """Configura conexión a la base de datos"""
    database_url = os.getenv("DATABASE_URL", "sqlite:///./mercadopago_enterprise.db")
    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def parse_date(date_str: str) -> datetime:
    """Parsea fecha en formato YYYY-MM-DD"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")

def format_bytes(bytes_count: int) -> str:
    """Formatea bytes en unidades legibles"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} TB"

def archive_logs_for_period(
    db_session, 
    start_date: datetime, 
    end_date: datetime,
    compress: bool = True,
    dry_run: bool = False
):
    """Archiva logs para un período específico"""
    
    print(f"🗄️  Archivando logs desde {start_date.strftime('%Y-%m-%d')} hasta {end_date.strftime('%Y-%m-%d')}")
    print("=" * 80)
    
    # Inicializar servicio S3
    s3_service = S3ArchiveService(db_session)
    
    if dry_run:
        print("🧪 MODO DRY RUN - No se subirán archivos a S3")
        
        # Obtener resumen de lo que se archivaría
        summary = s3_service.get_archive_summary(start_date, end_date)
        
        print("\n📊 RESUMEN DE ARCHIVADO:")
        print(f"   Período: {summary['period']['days']} días")
        print(f"   Logs de auditoría: {summary['records_to_archive']['audit_logs']:,}")
        print(f"   Alertas de seguridad: {summary['records_to_archive']['security_alerts']:,}")
        print(f"   Eventos de webhook: {summary['records_to_archive']['webhook_events']:,}")
        print(f"   Total de registros: {summary['records_to_archive']['total']:,}")
        print(f"\n🪣 Destino S3:")
        print(f"   Bucket: {summary['s3_config']['bucket']}")
        print(f"   Prefijo: {summary['s3_config']['prefix']}")
        print(f"   Región: {summary['s3_config']['region']}")
        print(f"   Clase de almacenamiento: {summary['s3_config']['storage_class']}")
        
        return True
    
    # Ejecutar archivado real
    results = s3_service.archive_all_logs_for_date_range(start_date, end_date, compress)
    
    print("\n📤 RESULTADOS DEL ARCHIVADO:")
    print("-" * 80)
    
    total_files = 0
    total_records = 0
    total_bytes = 0
    
    for log_type, result in results.items():
        status = "✅ Éxito" if result.success else "❌ Error"
        print(f"\n📋 {log_type.replace('_', ' ').title()}:")
        print(f"   Estado: {status}")
        print(f"   Archivos subidos: {result.files_uploaded}")
        print(f"   Registros archivados: {result.total_records:,}")
        
        if result.success and result.s3_keys:
            print(f"   Bytes subidos: {format_bytes(result.bytes_uploaded)}")
            print(f"   Archivos S3:")
            for key in result.s3_keys:
                print(f"     - s3://{s3_service.config.bucket_name}/{key}")
        
        if result.error_message:
            print(f"   Error: {result.error_message}")
        
        total_files += result.files_uploaded
        total_records += result.total_records
        total_bytes += result.bytes_uploaded
    
    print(f"\n🎉 RESUMEN TOTAL:")
    print(f"   Archivos subidos: {total_files}")
    print(f"   Registros archivados: {total_records:,}")
    print(f"   Datos transferidos: {format_bytes(total_bytes)}")
    
    return all(result.success for result in results.values())

def archive_last_month(db_session, compress: bool = True, dry_run: bool = False):
    """Archiva logs del mes pasado"""
    today = datetime.now()
    
    # Primer día del mes pasado
    if today.month == 1:
        start_date = datetime(today.year - 1, 12, 1)
        end_date = datetime(today.year, 1, 1) - timedelta(days=1)
    else:
        start_date = datetime(today.year, today.month - 1, 1)
        end_date = datetime(today.year, today.month, 1) - timedelta(days=1)
    
    print(f"📅 Archivando logs del mes pasado: {start_date.strftime('%B %Y')}")
    
    return archive_logs_for_period(db_session, start_date, end_date, compress, dry_run)

def archive_older_than_days(db_session, days: int, compress: bool = True, dry_run: bool = False):
    """Archiva logs más antiguos que X días"""
    end_date = datetime.now() - timedelta(days=days)
    start_date = datetime(2020, 1, 1)  # Fecha muy antigua para incluir todo
    
    print(f"📅 Archivando logs más antiguos que {days} días (antes del {end_date.strftime('%Y-%m-%d')})")
    
    return archive_logs_for_period(db_session, start_date, end_date, compress, dry_run)

def list_archived_files(db_session):
    """Lista archivos ya archivados en S3"""
    s3_service = S3ArchiveService(db_session)
    
    print("📂 ARCHIVOS ARCHIVADOS EN S3:")
    print("=" * 80)
    
    files = s3_service.list_archived_files()
    
    if not files:
        print("   No hay archivos archivados en S3")
        return
    
    # Agrupar por tipo
    file_groups = {}
    for file_info in files:
        key_parts = file_info['key'].split('/')
        if len(key_parts) >= 2:
            file_type = key_parts[1]  # audit_logs, security_alerts, etc.
            if file_type not in file_groups:
                file_groups[file_type] = []
            file_groups[file_type].append(file_info)
    
    total_size = 0
    total_files = 0
    
    for file_type, type_files in file_groups.items():
        print(f"\n📋 {file_type.replace('_', ' ').title()}:")
        type_size = 0
        
        for file_info in sorted(type_files, key=lambda x: x['last_modified'], reverse=True):
            filename = file_info['key'].split('/')[-1]
            size_str = format_bytes(file_info['size'])
            date_str = datetime.fromisoformat(file_info['last_modified'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')
            storage_class = file_info.get('storage_class', 'STANDARD')
            
            print(f"   📄 {filename}")
            print(f"      Tamaño: {size_str} | Fecha: {date_str} | Clase: {storage_class}")
            
            type_size += file_info['size']
            total_size += file_info['size']
            total_files += 1
        
        print(f"   Subtotal: {len(type_files)} archivos, {format_bytes(type_size)}")
    
    print(f"\n🎯 TOTAL: {total_files} archivos, {format_bytes(total_size)}")

def main():
    """Función principal del script"""
    parser = argparse.ArgumentParser(
        description="Archiva logs de MercadoPago Enterprise en Amazon S3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:

  # Archivar logs del mes pasado
  python archive_logs_to_s3.py --last-month

  # Archivar logs más antiguos que 90 días
  python archive_logs_to_s3.py --older-than 90

  # Archivar período específico
  python archive_logs_to_s3.py --start-date 2024-01-01 --end-date 2024-01-31

  # Modo dry-run (no sube archivos)
  python archive_logs_to_s3.py --last-month --dry-run

  # Listar archivos ya archivados
  python archive_logs_to_s3.py --list

Variables de entorno requeridas:
  AWS_ACCESS_KEY_ID       - Clave de acceso de AWS
  AWS_SECRET_ACCESS_KEY   - Clave secreta de AWS
  AWS_REGION              - Región de AWS (default: us-east-1)
  S3_BUCKET_NAME          - Nombre del bucket S3
  S3_LOG_PREFIX           - Prefijo para organizar logs (default: mercadopago-enterprise-logs)
        """
    )
    
    # Opciones de período
    period_group = parser.add_mutually_exclusive_group(required=True)
    period_group.add_argument(
        "--last-month",
        action="store_true",
        help="Archivar logs del mes pasado"
    )
    period_group.add_argument(
        "--older-than",
        type=int,
        metavar="DAYS",
        help="Archivar logs más antiguos que X días"
    )
    period_group.add_argument(
        "--date-range",
        action="store_true",
        help="Archivar período específico (requiere --start-date y --end-date)"
    )
    period_group.add_argument(
        "--list",
        action="store_true",
        help="Listar archivos ya archivados en S3"
    )
    
    # Fechas para período específico
    parser.add_argument(
        "--start-date",
        type=str,
        help="Fecha de inicio (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date", 
        type=str,
        help="Fecha de fin (YYYY-MM-DD)"
    )
    
    # Opciones adicionales
    parser.add_argument(
        "--no-compress",
        action="store_true",
        help="No comprimir archivos (por defecto se comprimen con gzip)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Modo dry-run: mostrar qué se archivaría sin subir archivos"
    )
    
    args = parser.parse_args()
    
    # Validar argumentos
    if args.date_range and (not args.start_date or not args.end_date):
        parser.error("--date-range requiere --start-date y --end-date")
    
    print("🗄️  MercadoPago Enterprise - Archivado de Logs en S3")
    print("=" * 60)
    
    # Verificar configuración de AWS
    required_env_vars = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "S3_BUCKET_NAME"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars and not args.list:
        print("❌ Variables de entorno faltantes:")
        for var in missing_vars:
            print(f"   {var}")
        print("\nConfigura estas variables en tu archivo .env")
        return 1
    
    # Configurar base de datos
    try:
        db_session = setup_database()
    except Exception as e:
        print(f"❌ Error conectando a la base de datos: {str(e)}")
        return 1
    
    try:
        # Ejecutar acción solicitada
        if args.list:
            list_archived_files(db_session)
            return 0
        
        compress = not args.no_compress
        
        if args.last_month:
            success = archive_last_month(db_session, compress, args.dry_run)
        
        elif args.older_than:
            success = archive_older_than_days(db_session, args.older_than, compress, args.dry_run)
        
        elif args.date_range:
            start_date = parse_date(args.start_date)
            end_date = parse_date(args.end_date)
            
            if start_date >= end_date:
                print("❌ La fecha de inicio debe ser anterior a la fecha de fin")
                return 1
            
            success = archive_logs_for_period(db_session, start_date, end_date, compress, args.dry_run)
        
        if success:
            print("\n🎉 Archivado completado exitosamente")
            return 0
        else:
            print("\n❌ Archivado completado con errores")
            return 1
            
    except Exception as e:
        print(f"\n❌ Error durante el archivado: {str(e)}")
        return 1
    
    finally:
        db_session.close()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)