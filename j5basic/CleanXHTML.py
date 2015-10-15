import cssutils
from xml.sax import saxutils
from lxml.html import tostring, fromstring, clean
from lxml import etree

import logging

class Cleaner(clean.Cleaner):
    def clean_html(self, html):
        if not isinstance(html, unicode):
            raise ValueError('We only support cleaning unicode HTML fragments')

        #We wrap the content up in an extra div tag (otherwise lxml does wierd things to it - like adding in <p> tags and stuff)
        divnode = fromstring(u'<div>' + html + u'</div>')
        self(divnode)

        # Strip all class attributes
        etree.strip_attributes(divnode, 'class')

        # Drop all xml:lang and lang attributes, and handle the
        # stripping of any bad css styles
        # Also drop id and class attributes - these are not useful in RichTextEditor
        for node in divnode.xpath("//*"):
            for key, value in node.attrib.iteritems():
                if key.lower() in ('xml:lang', 'lang','id','class'):
                    node.attrib.pop(key, None)
                elif 'style' == key.lower():
                    try:
                        cssStyle = cssutils.parseStyle(value)
                    except Exception, e:
                        logging.info("Style %s failed to parse with error %s." % (value, e))
                        node.attrib.pop(key, None)
                        continue

                    # Set the line separator so that the style gets serialized
                    cssutils.ser.prefs.lineSeparator = ''
                    # Only allow valid style properties
                    cssutils.ser.prefs.validOnly = True

                    new_style = cssStyle.cssText
                    if not new_style.strip():
                        node.attrib.pop(key, None)
                    else:
                        node.attrib[key] = new_style
            # Drop all empty span tags
            if node.tag == 'span' and not node.keys():
                node.drop_tag()

        # if there is only a single paragraph, and no line breaks, then don't save that for rendering
        if len(divnode.xpath('//p')) == 1 and len(divnode.xpath('//br')) == 0 and not (divnode.text or divnode.tail):
            node = divnode.getchildren()[0]
            if node.tag == 'p' and not node.keys():
                node.drop_tag()

        #Now unwrap the divnode (i.e. just serialize the children of our extra div node)
        cleaned = saxutils.escape(divnode.text) if divnode.text else ''

        for n in divnode:
            cleaned += tostring(n, encoding = unicode, method = 'xml')
        return cleaned

# We need safe_attrs_only set to False, otherwise it strips out style attributes completely
cleaner = Cleaner(safe_attrs_only=False)
clean_html = cleaner.clean_html
