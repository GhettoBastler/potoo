#!/usr/bin/env python

import re
import pathlib
import markdown
import shutil
import warnings
from itertools import chain
from CustomMDExtension import Obsidian
from CustomExceptions import SameNameError, UnknownLocalLinkWarning
import config


CHAR_WHITELIST = 'a-z0-9-_'


def urlize(text):
    """
    Replaces all non-whitelisted characters with an underscore
    """
    return re.sub(f'[^{CHAR_WHITELIST}]', '_', text.lower())


def parse_input_directory(path):
    """
    Takes a pathlib.Path object. Returns 3 objects:
        - a pages dictionary: keys are page names (str), values are 2-tuples:
                - path_to_markdown_file (Path object)
                - path_to_output_file (Path object)

        - a navigation dictionary: keys are page names (str), and values
          are 2-tuples:
            - parent page name (str or None)
            - children pages names (list of str, can be an empty list)

        - a list of media file to copy as-is. 2-tuples:
            (source Path object, dest Path object)
    """

    pages = {}
    navigation = {}
    media = []

    navigation[''] = [None, []]

    for item in chain([path], path.glob('**/*')):

        # Skipping hidden directories and files
        if any(part.startswith('.') for part in item.parts):
            continue

        if item.is_file():
            if item.suffix == '.md':
                if item.stem == item.parent.stem:
                    # This is a category descriptor. Don't add it yet
                    continue

                else:
                    # This is a note, add it to the list of pages to convert
                    output_path = pathlib.Path(urlize(item.stem) + '.html')
                    pages[item.stem] = (item, output_path)

            else:
                # This is a media file
                output_path = pathlib.Path(
                    config.MEDIA_DIRECTORY,
                    urlize(item.stem) + item.suffix
                )
                media.append((item, output_path))
                continue

        else:
            # This is a directory
            # Check if it's the root
            is_root = len(item.parts) == 1

            # Check if there is a description file inside
            description_file = item / (item.stem + '.md')
            if not description_file.exists():
                description_file = None

            if is_root:
                output_path = pathlib.Path('index.html')
            else:
                output_path = pathlib.Path(urlize(item.stem) + '.html')

            pages[item.stem] = (description_file, output_path)

        navigation[item.parent.stem][1].append(item.stem)

        if item.stem in navigation:
            raise SameNameError(item.stem)

        navigation[item.stem] = [item.parent.stem, []]

    return pages, navigation, media


def parse_markdown(markdown_path, md_parser):
    """
    Parse a Markdown file, returning the generated HTML as a string,
    and a dictionary containing the metadata stored at the top of the file
    """

    html = ''
    meta = []
    if markdown_path:
        with markdown_path.open(mode='r') as f:
            html = md_parser.reset().convert(f.read())
            meta = md_parser.Meta
    return html, meta


def reorder_children(children, meta):
    """
    Reorder a list of children based on the "children" entry in the
    metadata dictionary
    """

    res = children
    if 'children' in meta:
        parsed_children = meta['children']
        rest = set(children).difference(set(parsed_children))
        new_order = []
        for child in parsed_children:
            if child in children:
                new_order.append(child)
        new_order += list(rest)
        res = new_order
    return res


def make_navbar(name, meta, navigation, links):
    """
    Create the HTML code for the navbar
    """
    html = ''
    parent = navigation[name][0]
    children = navigation[name][1]
    ancestors = []
    siblings = []

    if parent:
        # Generating a list of siblings
        siblings = navigation[parent][1]

        # Generate a list of ancestors
        curr_ancestor = parent
        while curr_ancestor and curr_ancestor != config.INPUT_DIRECTORY:
            curr_ancestor_siblings = []
            grandparent = navigation[curr_ancestor][0]
            if grandparent:
                for parent_sibling in navigation[grandparent][1]:
                    active = parent_sibling == curr_ancestor
                    curr_ancestor_siblings.append((parent_sibling, active))
            ancestors.insert(0, curr_ancestor_siblings)
            curr_ancestor = grandparent

    # Generating a list of chlidren (if any)
    if children:
        children = reorder_children(children, meta)
        # Update the list of children
        navigation[name][1] = children

    # Generating HTML
    nav_html = '<div id="navtree">'
    if ancestors:
        for i, curr_level in enumerate(ancestors):
            nav_html += '<ul>\n'
            for ancestor, active in curr_level:
                nav_html += f'\t<li><a href={links[ancestor]}'
                if active:
                    nav_html += ' class="active"'
                nav_html += f'>{ancestor}</a></li>\n'
            nav_html += '</ul>\n'

    if siblings:
        nav_html += '<ul>\n'
        for sibling in siblings:
            nav_html += f'\t<li><a href={links[sibling]}'
            if sibling == name:
                nav_html += ' class="active"'
            nav_html += f'>{sibling}</a></li>\n'
        nav_html += '</ul>\n'

    if children:
        nav_html += '<ul>\n'
        for child in children:
            nav_html += f'\t<li><a href={links[child]}>{child}</a></li>\n'
        nav_html += '</ul>\n'

    nav_html += '</div>\n'
    return nav_html


def make_children_listing(children_meta, links):
    """
    Generates the HTML for the children listing.
    children_meta should be a list of 3-tuple:
        - title (str)
        - description (str, can be None)
        - header (source filename of the header image, can be None)
    """
    html = '<section id="category-listing">\n'
    for name, title, description, header in children_meta:
        entry = f'<div class="entry">\n'
        entry += f'<a href="{links[name]}">\n'
        if header:
            entry += f'<img src={links[header]}>\n'
        entry += f'<div class="entry-text">\n'
        entry += f'<p class="entry-title">{title}</p>\n'
        if description:
            entry += f'<p class="entry-description">{description}</p>\n'
        entry += '</div>\n'  # Closing entry-text
        entry += '</a>\n'
        entry += '</div>\n'  # Closing entry
        html += entry
    html += '</section>\n'

    return html


def generate_page(name, template, pages, navigation, links, md_parser):
    print(f'Generating {name}')
    markdown_path = pages[name][0]

    fields = {
        'SITE_NAME': config.SITE_NAME,
        'SITE_URL': config.SITE_URL,
        'PAGE_TITLE': name,
        'PAGE_DESCRIPTION': '',
        'NAV_HTML': '',
        'HEADER_IMG_HTML': '',
        'CONTENT_HTML': '',
        'CHILDREN_HTML': '',
    }

    # If this is the index page, change the title to "home"
    if links[name].name == 'index.html':
        fields['PAGE_TITLE'] = 'home'

    # Parsing Markdown
    content_html = ''
    meta = {}
    if markdown_path:
        content_html, meta = parse_markdown(markdown_path, md_parser)
    fields['CONTENT_HTML'] = content_html

    # Creating header image (if any)
    if 'header' in meta:
        header_img_html = '<img id="header-img" src="'
        header_img_html += str(links[meta['header'][0]])
        header_img_html += '">\n'

        # Creating header caption (if any)
        if 'header-caption' in meta:
            header_img_html += '<figcaption>'
            header_img_html += meta['header-caption'][0]
            header_img_html += '</figcaption>'

        fields['HEADER_IMG_HTML'] = header_img_html

    # Updating page title
    if 'title' in meta:
        fields['PAGE_TITLE'] = meta['title'][0]

    # Generating navbar
    nav_html = make_navbar(name, meta, navigation, links)
    fields['NAV_HTML'] = nav_html

    # Recursive calls to get children's meta data
    children = reorder_children(navigation[name][1], meta)
    if children:
        children_meta = []
        for child in children:
            child_meta = generate_page(child, template, pages, navigation,
                                       links, md_parser)
            children_meta.append(child_meta)

        # Generate the children listing
        fields['CHILDREN_HTML'] = make_children_listing(children_meta, links)

    # Checking for description
    description = ''
    if 'description' in meta:
        description = meta['description'][0]
    fields['PAGE_DESCRIPTION'] = description

    # Apply template
    res = template.format(**fields)

    # Generating HTML file
    write_html(res, pages[name][1])

    # Return page's meta data
    title = fields['PAGE_TITLE']
    header = ''
    if 'header' in meta:
        header = meta['header'][0]

    return (name, title, description, header)


def write_html(html, dst_path):
    output_path = pathlib.Path(config.OUTPUT_DIRECTORY) / dst_path
    with output_path.open('w') as f:
        f.write(html)


def make_links(pages, media):
    """
    Generates a the translation dictionary.
    Keys are page name/media filename, values are output path
    """
    links = dict((name, pages[name][1]) for name in pages)
    # Add media links
    for src, dst in media:
        links[src.name] = dst
    return links


def main(input_path):
    print('Parsing input directory...')
    pages, navigation, media = parse_input_directory(input_path)
    print(f'Found {len(pages)} pages to generate,'
          f' and {len(media)} non-markdown files to copy')
    links = make_links(pages, media)

    md_parser = markdown.Markdown(extensions=[
        Obsidian(links=links),
        'fenced_code',
        'meta',
        'tables',
    ])

    with open(config.TEMPLATE_FILE, 'r') as f:
        template = f.read()

    root_page = [name for name in pages if pages[name][1].stem == 'index'][0]

    print()
    print('Generating pages...')
    generate_page(root_page, template, pages, navigation, links, md_parser)

    print()
    print('Copying media files')
    output_media_dir = pathlib.Path(config.OUTPUT_DIRECTORY,
                                    config.MEDIA_DIRECTORY)
    output_media_dir.mkdir()
    for src_path, dst_path in media:
        shutil.copy(src_path, pathlib.Path(config.OUTPUT_DIRECTORY) / dst_path)

    print()
    print('Copying static files')
    shutil.copytree(config.STATIC_DIRECTORY, config.OUTPUT_DIRECTORY,
                    dirs_exist_ok=True)

    print('Done.')


if __name__ == '__main__':
    if config.STRICT:
        warnings.simplefilter("error", UnknownLocalLinkWarning)
    else:
        warnings.simplefilter("default", UnknownLocalLinkWarning)

    main(pathlib.Path(config.INPUT_DIRECTORY))
