#!/usr/bin/env bash
# This script launches multiple batches of Blender renders in parallel.
# Each batch is executed via Blender calling the generate-batch.py script,
# and its output (rendered images and metadata CSV) is stored in a subfolder.
#
# Usage:
#   ./generate_batches.sh --model_path /path/to/model.glb \
#       [--num_batches 1] [--num_images_per_batch 1] [--jobs <number>] [--output_dir <directory>]
#
# Default values:
#   --num_batches: 1
#   --num_images_per_batch: 1
#   --jobs: 0 (as much as possible)
#   --output_dir: batches (in the current directory)
#   --blender: path to blender executable (default: blender)

set -euo pipefail

usage() {
    echo "Usage: $0 --model_path <path> [--num_batches <number>] [--num_images_per_batch <number>] [--jobs <number>] [--output_dir <directory>] [--blender <path>]"
    exit 1
}

NUM_BATCHES=1
NUM_IMAGES_PER_BATCH=1
OUTPUT_DIR="batches"
JOBS=0
MODEL_PATH=""
BLENDER_PATH="blender"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --num_batches)
            NUM_BATCHES="$2"
            shift 2
            ;;
        --num_images_per_batch)
            NUM_IMAGES_PER_BATCH="$2"
            shift 2
            ;;
        --jobs)
            JOBS="$2"
            shift 2
            ;;
        --model_path)
            MODEL_PATH="$2"
            shift 2
            ;;
        --output_dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --blender)
            BLENDER_PATH="$2"
            shift 2
            ;;
        *)
            echo "Unknown parameter: $1"
            usage
            ;;
    esac
done

if [[ -z "$MODEL_PATH" ]]; then
    echo "Error: --model_path is required."
    usage
fi

if [[ -z "$BLENDER_PATH" ]]; then
    echo "Error: --blender is required."
    usage
fi

mkdir -p "$OUTPUT_DIR"

COMMANDS_FILE=$(mktemp)

# For each batch, create a batch subfolder and write a command to the temporary file.
for (( i=1; i<=NUM_BATCHES; i++ )); do
    # Create a batch folder named batchXX
    BATCH_DIR=$(printf "%s/batch%02d" "$OUTPUT_DIR" "$i")
    mkdir -p "$BATCH_DIR"

    # Construct the command:
    # Note: The generate-batch.py script must be accessible and handle these parameters.
    CMD="\"$BLENDER_PATH\" --background --python generate-batch.py -- --model_path \"$MODEL_PATH\" --num_images $NUM_IMAGES_PER_BATCH --output_dir \"$BATCH_DIR\""
    echo "$CMD" >> "$COMMANDS_FILE"
done

echo "Launching $NUM_BATCHES batches with $JOBS workers..."
cat "$COMMANDS_FILE" | xargs -I {} -P "$JOBS" bash -c '{}'

# Clean up temporary file.
rm "$COMMANDS_FILE"

echo "All batches completed. Results are stored in $OUTPUT_DIR"
