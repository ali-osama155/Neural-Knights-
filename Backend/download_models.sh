#!/bin/bash
echo "=== Starting ML Models Download ==="

mkdir -p app/ml/saved_model
mkdir -p cv_module/models

echo "Downloading best_model.pt..."
curl -L --retry 3 -o app/ml/saved_model/best_model.pt \
  "https://drive.google.com/uc?id=1FPzxR1xfZr4BfDKtlMJUDyoUsBiJg_T6&export=download"

echo "Downloading fer_raf_combined_final.keras..."
curl -L --retry 3 -o cv_module/models/fer_raf_combined_final.keras \
  "https://drive.google.com/uc?id=1z_BQ2JTyAy6zkZqd6G58P-DvYqXWUIPp&export=download"

echo "=== Models Download Completed ==="
