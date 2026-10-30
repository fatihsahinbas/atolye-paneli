#!/usr/bin/env bash
# Günlük yedek (Checklist #20). Cron örneği:
#   15 3 * * * /srv/atolye-paneli/scripts/backup.sh >> /var/log/atolye-backup.log 2>&1
# Gerekli: BACKUP_PASSPHRASE ortam değişkeni (yedekler şifreli saklanır).
# Yedekleri sunucu dışına (ör. rclone ile başka bir depolamaya) kopyalamayı unutmayın.
set -euo pipefail
cd "$(dirname "$0")/.."

: "${BACKUP_PASSPHRASE:?BACKUP_PASSPHRASE gerekli}"
STAMP=$(date +%Y%m%d-%H%M)
OUT=backups
mkdir -p "$OUT"

docker compose exec -T db pg_dump -U atolye -Fc atolye \
  | gpg --batch --yes --symmetric --cipher-algo AES256 --passphrase "$BACKUP_PASSPHRASE" \
  > "$OUT/db-$STAMP.dump.gpg"

docker compose run --rm -T --entrypoint tar app czf - -C /srv/var media \
  | gpg --batch --yes --symmetric --cipher-algo AES256 --passphrase "$BACKUP_PASSPHRASE" \
  > "$OUT/media-$STAMP.tgz.gpg"

# 14 günden eski yedekleri sil
find "$OUT" -name '*.gpg' -mtime +14 -delete
echo "Yedek tamam: $STAMP"
