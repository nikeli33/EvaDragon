#!/bin/sh

# Указываем папки, как они видны ВНУТРИ контейнера whisper
AUDIO_DIR="/home/node/audio"
TRANSCRIPTIONS_DIR="/transcriptions"
PROCESSED_DIR="/home/node/audio/processed"

# Создаем папку для уже обработанных файлов, если ее нет
mkdir -p "$PROCESSED_DIR"

echo "Whisper is watching for files in $AUDIO_DIR..."

# Бесконечный цикл
while true; do
  # Ищем любой файл в папке (кроме тех, что в sub-директориях)
  for file in "$AUDIO_DIR"/*; do
    # Если найден файл
    if [ -f "$file" ]; then
      filename=$(basename "$file")
      echo "Processing file: $filename"
      
      # Запускаем транскрибацию
      whisper "$file" --model medium --language Russian --output_dir "$TRANSCRIPTIONS_DIR"
      
      echo "Transcription complete. Moving file to processed."
      
      # Перемещаем обработанный файл, чтобы не транскрибировать его снова
      mv "$file" "$PROCESSED_DIR/$filename"
    fi
  done
  
  # Ждем 5 секунд перед следующей проверкой
  sleep 5
done
