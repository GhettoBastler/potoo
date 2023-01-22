#! /bin/sh

REAL_SOURCE_DIRECTORY=""
MEDIA_DIRECTORY="output/media"

# Cleanup
echo "Cleaning output directory" &&
rm -rf output &&
mkdir output &&

# Since I'm afraid all my notes would be deleted if I messed up, we copy the source directory first
echo "Copying input directory" &&
rsync -r --delete --exclude=".*" $REAL_SOURCE_DIRECTORY . &&

# Generating pages
echo "Generating pages" &&
./generator.py &&

# Optimizing image size
echo "Optimizing image size" &&
mogrify -scale 800x\> -sampling-factor 4:2:0 -format jpg -strip -quality 80 -interlace line $MEDIA_DIRECTORY/*.jpg
