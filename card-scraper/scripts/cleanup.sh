#!/bin/bash

set -e

find scratch -type f -delete || true
find . -name ".DS_Store" -delete

echo "Cleanup complete"
