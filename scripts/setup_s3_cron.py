#!/usr/bin/env python3
"""
Script para configurar cron jobs automáticos de archivado S3
Configura tareas programadas para backup automático de logs
"""
import os
import sys
from pathlib import Path
from datetime import datetime

def get_project_path():
    """Obtiene la ruta absoluta del proyecto"""
    return str(Path(__file__).parent.parent.absolute())

def create_cron_script():
    """Crea script wrapper para cron"""
    project_path = get_project_path()
    
    cron_script_content = f"""#!/bin/bash
# Script wrapper para archivado automático S3
# Generado automáticamente el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# Configurar entorno
cd {project_path}
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"

# Cargar variables de entorno si existe .env
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Ejecutar archivado
python3 scripts/archive_logs_to_s3.py --older-than 90 >> logs/s3_archive.log 2>&1

# Log del resultado
echo "$(date): S3 archive cron job completed" >> logs/s3_archive.log
"""
    
    script_path = os.path.join(project_path, "scripts", "s3_archive_cron.sh")
    
    with open(script_path, 'w') as f:
        f.write(cron_script_content)
    
    # Hacer ejecutable
    os.chmod(script_path, 0o755)
    
    return script_path

def generate_crontab_entries(script_path):
    """Genera entradas de crontab sugeridas"""
    
    entries = {
        "weekly": f"0 2 * * 0 {script_path}  # Archivado semanal (domingos 2 AM)",
        "monthly": f"0 3 1 * * {script_path}  # Archivado mensual (día 1, 3 AM)", 
        "daily": f"0 1 * * * {script_path}  # Archivado diario (1 AM)"
    }
    
    return entries

def show_installation_instructions(script_path, cron_entries):
    """Muestra instrucciones de instalación"""
    
    print("🔧 CONFIGURACIÓN DE ARCHIVADO AUTOMÁTICO S3")
    print("=" * 60)
    print()
    print("📁 Script creado en:")
    print(f"   {script_path}")
    print()
    print("📅 OPCIONES DE PROGRAMACIÓN:")
    print()
    
    for frequency, entry in cron_entries.items():
        print(f"🕐 {frequency.upper()}:")
        print(f"   {entry}")
        print()
    
    print("⚙️  INSTALACIÓN MANUAL:")
    print()
    print("1. Editar crontab:")
    print("   crontab -e")
    print()
    print("2. Agregar una de las líneas de arriba (recomendado: semanal)")
    print()
    print("3. Verificar crontab:")
    print("   crontab -l")
    print()
    print("📋 INSTALACIÓN AUTOMÁTICA (SEMANAL):")
    print()
    print("   # Instalar cron job semanal automáticamente")
    print(f"   (crontab -l 2>/dev/null; echo '{cron_entries['weekly']}') | crontab -")
    print()
    print("🗂️  LOGS:")
    print(f"   Los logs se guardarán en: {os.path.join(os.path.dirname(script_path), '..', 'logs', 's3_archive.log')}")
    print()
    print("🔍 VERIFICAR FUNCIONAMIENTO:")
    print(f"   # Ejecutar manualmente para probar")
    print(f"   {script_path}")
    print()
    print("   # Ver logs")
    print(f"   tail -f {os.path.join(os.path.dirname(script_path), '..', 'logs', 's3_archive.log')}")

def install_cron_job_automatically(script_path, frequency="weekly"):
    """Instala cron job automáticamente"""
    
    cron_entries = generate_crontab_entries(script_path)
    
    if frequency not in cron_entries:
        print(f"❌ Frecuencia inválida: {frequency}")
        print(f"   Opciones disponibles: {', '.join(cron_entries.keys())}")
        return False
    
    try:
        import subprocess
        
        # Obtener crontab actual
        try:
            current_crontab = subprocess.check_output(['crontab', '-l'], stderr=subprocess.DEVNULL).decode('utf-8')
        except subprocess.CalledProcessError:
            current_crontab = ""
        
        # Verificar si ya existe
        if script_path in current_crontab:
            print("⚠️  Ya existe un cron job para este script")
            return False
        
        # Agregar nueva entrada
        new_entry = cron_entries[frequency].split('#')[0].strip()  # Remover comentario
        new_crontab = current_crontab.rstrip() + "\n" + new_entry + "\n"
        
        # Instalar nueva crontab
        process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE)
        process.communicate(input=new_crontab.encode('utf-8'))
        
        if process.returncode == 0:
            print(f"✅ Cron job {frequency} instalado exitosamente")
            print(f"   Comando: {new_entry}")
            return True
        else:
            print("❌ Error instalando cron job")
            return False
            
    except Exception as e:
        print(f"❌ Error instalando cron job: {str(e)}")
        return False

def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Configura archivado automático de logs en S3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:

  # Solo crear script (instalación manual)
  python setup_s3_cron.py

  # Crear script e instalar cron job semanal
  python setup_s3_cron.py --install weekly

  # Crear script e instalar cron job mensual
  python setup_s3_cron.py --install monthly

Frecuencias disponibles:
  - weekly: Domingos a las 2 AM
  - monthly: Día 1 de cada mes a las 3 AM  
  - daily: Todos los días a la 1 AM
        """
    )
    
    parser.add_argument(
        "--install",
        choices=["weekly", "monthly", "daily"],
        help="Instalar cron job automáticamente con la frecuencia especificada"
    )
    
    args = parser.parse_args()
    
    print("🗄️  Setup de Archivado Automático S3 - MercadoPago Enterprise")
    print("=" * 70)
    print()
    
    # Verificar que estamos en el directorio correcto
    project_path = get_project_path()
    if not os.path.exists(os.path.join(project_path, "scripts", "archive_logs_to_s3.py")):
        print("❌ Error: No se encuentra archive_logs_to_s3.py")
        print(f"   Asegúrate de ejecutar este script desde el directorio del proyecto")
        return 1
    
    # Crear directorio de logs si no existe
    logs_dir = os.path.join(project_path, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Crear script de cron
    print("📝 Creando script wrapper para cron...")
    script_path = create_cron_script()
    print(f"   ✅ Script creado: {script_path}")
    print()
    
    # Generar entradas de crontab
    cron_entries = generate_crontab_entries(script_path)
    
    if args.install:
        # Instalación automática
        print(f"🤖 Instalando cron job automáticamente ({args.install})...")
        success = install_cron_job_automatically(script_path, args.install)
        
        if success:
            print()
            print("🎉 ¡Archivado automático configurado exitosamente!")
            print()
            print("📋 PRÓXIMOS PASOS:")
            print("1. Configurar credenciales AWS en .env:")
            print("   AWS_ACCESS_KEY_ID=tu_access_key")
            print("   AWS_SECRET_ACCESS_KEY=tu_secret_key")
            print("   S3_BUCKET_NAME=tu_bucket")
            print()
            print("2. Verificar funcionamiento:")
            print(f"   {script_path}")
            print()
            print("3. Monitorear logs:")
            print(f"   tail -f {os.path.join(logs_dir, 's3_archive.log')}")
        else:
            print()
            print("⚠️  Instalación automática falló. Usa instalación manual:")
            show_installation_instructions(script_path, cron_entries)
    else:
        # Solo mostrar instrucciones
        show_installation_instructions(script_path, cron_entries)
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)