#!/usr/bin/env python

import re
import warnings
from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern
import xml.etree.ElementTree as etree
from markdown.treeprocessors import Treeprocessor
from CustomExceptions import UnknownLocalLinkWarning


# [[local_url|text]]
OBSIDIAN_LINK_RE = r'(?<!\!)\[\[(?P<url>[^\]\|]+)(\|?\s*(?P<name>[^\]]+))?\]\]'

# ![[local_url|name]]
OBSIDIAN_EMBED_RE = r'\!\[\[(?P<url>[^\]\|]+)(\|?\s*(?P<name>[^\]]+))?\]\]'

IMAGE_EXTENSIONS = [
    'jpg',
    'jpeg',
    'png',
    'gif',
    'bmp',
]

VIDEO_EXTENSIONS = [
    'mp4',
]

VIDEO_TYPES = {
    'mp4': 'video/mp4',
}


class Obsidian(Extension):
    def __init__(self, **kwargs):
        self.config = {
            'links': [{}, 'Dictionary of source paths -> final paths']
        }
        super(Obsidian, self).__init__(**kwargs)

    def extendMarkdown(self, md):
        md.inlinePatterns.register(ObsidianLinkPattern(), 'obsidianlink', 145)
        md.inlinePatterns.register(ObsidianImagePattern(), 'obsidianimage',
                                   155)
        md.treeprocessors.register(
            ObsidianLinkProcessor(md, links=self.getConfig('links')),
            'obsidianlinkprocessor',
            15
        )


class ObsidianLinkPattern(Pattern):
    def __init__(self):
        super().__init__(OBSIDIAN_LINK_RE)

    def handleMatch(self, m):
        el = etree.Element('a')
        url = m.group('url').strip()
        name = m.group('name')
        if name:
            el.text = name.strip()
        else:
            el.text = url
        el.attrib['href'] = url
        return el


class ObsidianImagePattern(Pattern):
    def __init__(self):
        super().__init__(OBSIDIAN_EMBED_RE)

    def handleMatch(self, m):
        url = m.group('url').strip()
        name = m.group('name')
        extension = url.split('.')[-1]
        if not extension:
            raise ValueError(f'{url}: has no extension.')

        if extension in IMAGE_EXTENSIONS:
            el = etree.Element('img')
            el.attrib['src'] = url
        elif extension in VIDEO_EXTENSIONS:
            el = etree.Element('video')
            el.attrib['controls'] = ''

            # Adding video source
            source = etree.Element('source')
            source.attrib['src'] = url
            source.attrib['type'] = VIDEO_TYPES[extension]
            el.append(source)
        else:
            raise ValueError(f'{extension}: unknown file type')

        return el


class ObsidianLinkProcessor(Treeprocessor):
    def __init__(self, md, links):
        self.md = md
        self.links = links

    def run(self, root):
        for parent in root.iter():
            # Dirty workaround to remove a link:
            # keep track of the parent node
            idx = 0
            while idx < len(parent):
                element = parent[idx]
                if element.tag == 'a':
                    # Process link
                    href = element.attrib['href']
                    if not href.startswith('http'):
                        # Translate local links into final URLs
                        if href in self.links:
                            element.attrib['href'] = str(self.links[href])
                        else:
                            warnings.warn(href, UnknownLocalLinkWarning)
                            print('\tremoving link')
                            text = element.text
                            if element.tail:
                                text += element.tail

                            if idx == 0:  # First child
                                # Add text after parent's text
                                if not parent.text:
                                    parent.text = ''
                                parent.text += text
                            else:
                                # Add text as the tail of the previous sibling
                                previous = parent[idx-1]
                                if not previous.tail:
                                    previous.tail = ''
                                previous.tail += text

                            parent.remove(element)
                            idx -= 1
                    else:
                        # Set the class to "outgoing"
                        element.attrib['class'] = 'outgoing'
                elif element.tag == 'img':
                    # Process image
                    src = element.attrib['src']
                    if not src.startswith('http'):
                        # Translate image path into final image path
                        if src in self.links:
                            element.attrib['src'] = str(self.links[src])
                        else:
                            warnings.warn(src, UnknownLocalLinkWarning)
                            print('\tremoving image')
                            parent.remove(element)
                            idx -= 1

                elif element.tag == 'video':
                    # Process video
                    for source in element:
                        src = source.attrib['src']
                        if not src.startswith('http'):
                            # Translate video path into final video path
                            if src in self.links:
                                source.attrib['src'] = str(self.links[src])
                            else:
                                warnings.warn(src, UnknownLocalLinkWarning)
                                print('\tremoving video')
                                parent.remove(element)
                                idx -= 1
                idx += 1
