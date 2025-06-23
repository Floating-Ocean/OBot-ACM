import os
from pathlib import Path

import imgkit
import markdown2
from PIL import Image
from lxml import html
from lxml.etree import Element

from src.render.html.css import get_basic_css, load_css


def _fill_in_html(body: str, css: str, body_extra: str = "") -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
        <meta charset="utf-8">
        <style>
            {get_basic_css()}
            {css}
        </style>
    </head>
    <body>
        <div class="content-wrapper">
            <div class="content">
                {body}
                {body_extra}
            </div>
        </div>
    </body>
    </html>
    """


def md_to_html(markdown_path: str, css_path: str, extra_body: str = "", **kwargs) -> str:
    with open(markdown_path, "r", encoding="utf-8") as f:
        md_html = markdown2.markdown(f.read())

    md_dir = os.path.dirname(markdown_path)
    md_dir_path = Path(md_dir).resolve()

    tree = html.fromstring(md_html)
    prefix = md_dir_path.as_uri() + "/"

    for img in tree.xpath('//img'):
        src = img.get('src')
        if src and not src.startswith(('http://', 'https://', '/')):
            img.set('src', prefix + src)  # 替换相对路径为绝对路径

    for code in tree.xpath('//code'):  # 替换 <code> 为 <span class="code">
        new_span = Element("span")
        new_span.set("class", "code")
        new_span.text = code.text
        new_span.tail = code.tail
        for child in code:
            new_span.append(child)

        # 替换原节点
        code.getparent().replace(code, new_span)

    html_body = html.tostring(tree, encoding='unicode')
    html_css = load_css(css_path, **kwargs)

    return _fill_in_html(html_body, html_css, extra_body)


def render_md_html(markdown_path: str, css_path: str, output_path: str, extra_body: str = "", **kwargs):
    md_html = md_to_html(markdown_path, css_path, extra_body, **kwargs)
    options = {
        'enable-local-file-access': None,  # 允许本地文件访问
        'disable-smart-width': None,  # 禁用自动宽度调整
        'encoding': "UTF-8",
        'zoom': '2',
        'width': '2176',
        'quality': '100',
        'format': 'png'
    }
    tmp_large_img_path = output_path + ".large"
    imgkit.from_string(md_html, tmp_large_img_path, options=options)

    with Image.open(tmp_large_img_path) as img:
        width, height = img.size
        new_size = (int(width * 0.5), int(height * 0.5))
        resized_img = img.resize(new_size, Image.Resampling.LANCZOS)
        resized_img.save(output_path, "PNG", optimize=True, quality=100)

    os.remove(tmp_large_img_path)
