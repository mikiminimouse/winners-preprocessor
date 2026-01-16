#!/bin/bash
#
# Скрипт для создания тестовых UNIT в Ready2Docling
#

set -e

BASE_DIR="/root/winners_preprocessor/final_preprocessing/Data/2025-12-20"
INPUT_DIR="$BASE_DIR/Input"
READY_DIR="$BASE_DIR/Ready2Docling"

echo "===== Создание тестовых UNIT в Ready2Docling ====="
echo ""

# Функция для создания contract
create_contract() {
    local unit_id=$1
    local route=$2
    local file_name=$3
    local file_type=$4
    local target_dir=$5

    cat > "$target_dir/docprep.contract.json" << EOF
{
  "contract_version": "1.0",
  "unit_id": "$unit_id",
  "routing": {
    "docling_route": "$route",
    "source_state": "READY_FOR_DOCLING"
  },
  "metadata": {
    "language_hint": "ru",
    "original_format": "$file_type"
  },
  "files": [
    {
      "name": "$file_name",
      "type": "$file_type",
      "route": "$route"
    }
  ]
}
EOF
}

# PDF UNIT (уже создан первый, создаем остальные 2)
echo "📄 Обработка PDF UNIT..."
cp -r "$INPUT_DIR/UNIT_a33f26bc93a54a08" "$READY_DIR/pdf/text/"
create_contract "UNIT_a33f26bc93a54a08" "pdf_text" "Протокол подведения итогов №32515512513-01.pdf" "pdf" "$READY_DIR/pdf/text/UNIT_a33f26bc93a54a08"
echo "✅ UNIT_a33f26bc93a54a08 (PDF)"

cp -r "$INPUT_DIR/UNIT_d91e0294ed8b49fa" "$READY_DIR/pdf/text/"
create_contract "UNIT_d91e0294ed8b49fa" "pdf_text" "Протокол подведения итогов № 4.pdf" "pdf" "$READY_DIR/pdf/text/UNIT_d91e0294ed8b49fa"
echo "✅ UNIT_d91e0294ed8b49fa (PDF)"

# DOCX UNIT
echo ""
echo "📝 Обработка DOCX UNIT..."
cp -r "$INPUT_DIR/UNIT_55f7134445ff4da9" "$READY_DIR/docx/"
create_contract "UNIT_55f7134445ff4da9" "docx" "Протокол_рассмотрения_предложений_МСПЭМП_(системный).docx" "docx" "$READY_DIR/docx/UNIT_55f7134445ff4da9"
echo "✅ UNIT_55f7134445ff4da9 (DOCX)"

cp -r "$INPUT_DIR/UNIT_83f2344b40e54e3c" "$READY_DIR/docx/"
create_contract "UNIT_83f2344b40e54e3c" "docx" ". Протокол_2 итг.docx" "docx" "$READY_DIR/docx/UNIT_83f2344b40e54e3c"
echo "✅ UNIT_83f2344b40e54e3c (DOCX)"

cp -r "$INPUT_DIR/UNIT_5a8e6dbc7962444f" "$READY_DIR/docx/"
create_contract "UNIT_5a8e6dbc7962444f" "docx" "1. Протокол_ТЛЦ_БР.docx" "docx" "$READY_DIR/docx/UNIT_5a8e6dbc7962444f"
echo "✅ UNIT_5a8e6dbc7962444f (DOCX)"

# RTF UNIT
echo ""
echo "📑 Обработка RTF UNIT..."
cp -r "$INPUT_DIR/UNIT_abbee37bdabd4169" "$READY_DIR/rtf/"
create_contract "UNIT_abbee37bdabd4169" "rtf" "HappenedRetrade_32515415134.rtf" "rtf" "$READY_DIR/rtf/UNIT_abbee37bdabd4169"
echo "✅ UNIT_abbee37bdabd4169 (RTF)"

cp -r "$INPUT_DIR/UNIT_c07c12d2137648b5" "$READY_DIR/rtf/"
create_contract "UNIT_c07c12d2137648b5" "rtf" "Протокол_подведеня_итогов.rtf" "rtf" "$READY_DIR/rtf/UNIT_c07c12d2137648b5"
echo "✅ UNIT_c07c12d2137648b5 (RTF)"

# DOC UNIT (обрабатываем как DOCX)
echo ""
echo "📋 Обработка DOC UNIT..."
cp -r "$INPUT_DIR/UNIT_534048d632de4e0d" "$READY_DIR/docx/"
create_contract "UNIT_534048d632de4e0d" "docx" "Протокол ЗМИ.doc" "doc" "$READY_DIR/docx/UNIT_534048d632de4e0d"
echo "✅ UNIT_534048d632de4e0d (DOC)"

echo ""
echo "===== Завершено ====="
echo ""
echo "Проверка созданных UNIT:"
contract_count=$(find "$READY_DIR" -name "docprep.contract.json" | wc -l)
echo "✅ Создано contracts: $contract_count"
echo ""
echo "Детали по типам:"
echo "  PDF:  $(find "$READY_DIR/pdf/text" -name "docprep.contract.json" | wc -l) units"
echo "  DOCX: $(find "$READY_DIR/docx" -name "docprep.contract.json" | wc -l) units"
echo "  RTF:  $(find "$READY_DIR/rtf" -name "docprep.contract.json" | wc -l) units"
