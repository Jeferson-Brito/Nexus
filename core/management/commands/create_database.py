"""
Django management command to create the database if it doesn't exist.
"""
import os
from django.core.management.base import BaseCommand
from django.conf import settings
import psycopg
from psycopg import sql
from dotenv import load_dotenv

load_dotenv()


class Command(BaseCommand):
    help = 'Creates the database if it does not exist'

    def handle(self, *args, **options):
        db_name = os.getenv('DB_NAME', 'nexus')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', '')
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5433')

        try:
            # Connect to PostgreSQL server (not to a specific database)
            conn = psycopg.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                dbname='postgres'  # Connect to default postgres database
            )
            conn.autocommit = True
            cur = conn.cursor()

            # Check if database exists
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (db_name,)
            )
            exists = cur.fetchone()

            if not exists:
                # Create database
                cur.execute(
                    sql.SQL('CREATE DATABASE {}').format(
                        sql.Identifier(db_name)
                    )
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Banco de dados "{db_name}" criado com sucesso!'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'Banco de dados "{db_name}" já existe.'
                    )
                )

            cur.close()
            conn.close()

        except psycopg.OperationalError as e:
            self.stdout.write(
                self.style.ERROR(
                    f'ERRO ao conectar ao PostgreSQL: {e}'
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    '\nVerifique se:\n'
                    '- PostgreSQL está rodando\n'
                    '- Usuário e senha estão corretos no arquivo .env\n'
                    '- Porta está correta (padrão: 5433)'
                )
            )
            raise
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'ERRO: {e}')
            )
            raise

