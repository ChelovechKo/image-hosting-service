# Скрипт для резервного копирования базы данных PostgreSQL
TIMESTAMP=$(date +"%Y-%m-%d_%H%M%S")
docker exec -t project2-db-1 pg_dump -U postgres images_db > backups/backup_$TIMESTAMP.sql
echo "Резервная копия сохранена в backups/backup_$TIMESTAMP.sql"
