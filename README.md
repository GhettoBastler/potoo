# Potoo

A haphazardly made static site generator.

## Disclamer

This program was written specifically for my use case and might not work for yours. I'm sharing it here for others to learn from it, but you shouldn't expect it to work *out of the box*.

It wasn't made with customization in mind, so changing the look of the website means editing `template.html` and `generator.py` directly.

**Several directories are deleted/overwritten without prompting the user for confirmation**, so always keep a backup of your source files.

## Requirements

- Python 3.10
- Markdown module

## Usage

Before running, `build.sh` should be edited to enter the path of the actual source directory. This directory will be copied so that nothing important gets be deleted if we mess up.
`config.py` should also be edited to add the name this directory in the 'INPUT_DIRECTORY' variable.

Then run `build.sh`. By default the website will be built in the `output` directory.

## Licensing

The code for this project is licensed under the terms of the GNU GPLv3 license.
