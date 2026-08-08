# Copyright 2026 Jetperch LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pyjoulescope_driver import Driver
import html
import json
import os


_FORMATS = ['json', 'yaml', 'html']
_EXTENSIONS = {
    '.json': 'json',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.html': 'html',
    '.htm': 'html',
}
_COLUMN_ORDER = ['dtype', 'brief', 'detail', 'default', 'options', 'range', 'format', 'flags']
_COLUMNS_HIDDEN = ['detail']


def parser_config(p):
    """Display device metadata."""
    p.add_argument('--format',
                   type=str.lower,
                   choices=_FORMATS,
                   help='The output format.  When omitted, infer from the --out '
                        + 'file extension, defaulting to json.')
    p.add_argument('--device',
                   help='The target device path.  Optional when only one device is connected.')
    p.add_argument('--out',
                   help='The output file path.  When omitted, write to stdout.')
    p.add_argument('--open', '-o',
                   choices=['defaults', 'restore'],
                   default='restore',
                   help='The device open mode.  Defaults to "restore".')
    return on_cmd


def format_resolve(fmt, out_path):
    """Resolve the output format.

    :param fmt: The explicit format or None.
    :param out_path: The output file path or None.
    :return: One of 'json', 'yaml', 'html'.
    """
    if fmt is not None:
        return fmt
    if out_path is not None:
        ext = os.path.splitext(out_path)[1].lower()
        if ext in _EXTENSIONS:
            return _EXTENSIONS[ext]
    return 'json'


def device_select(device_paths, device):
    """Select the target device.

    :param device_paths: The list of connected device paths.
    :param device: The requested device path or None.
    :return: The selected device path.
    :raise ValueError: If the selection is empty or ambiguous.
    """
    if not device_paths:
        raise ValueError('No connected Joulescopes found')
    if device is None:
        if len(device_paths) == 1:
            return device_paths[0]
        raise ValueError('Multiple devices found, specify one with --device:\n  '
                         + '\n  '.join(device_paths))
    if device not in device_paths:
        raise ValueError(f'Device {device} not found.  Connected devices:\n  '
                         + '\n  '.join(device_paths))
    return device


def metadata_load(driver, device_path):
    """Load the retained metadata snapshot for an open device.

    :param driver: The active Driver instance.
    :param device_path: The open device path.
    :return: The dict mapping device-relative subtopic to metadata dict.
    """
    meta = {}
    prefix_len = len(device_path) + 1

    def on_metadata(topic, value):
        if topic[-1] == '$':
            topic = topic[:-1]
        meta[topic[prefix_len:]] = value

    driver.subscribe(device_path, 'metadata_rsp_retain', on_metadata)
    driver.unsubscribe(device_path, on_metadata)
    return meta


def to_json(meta):
    return json.dumps(meta, indent=2) + '\n'


def to_yaml(meta):
    import yaml
    return yaml.safe_dump(meta, sort_keys=True, allow_unicode=True)


def _columns(meta):
    keys = set()
    for value in meta.values():
        if value is not None:  # devices publish null metadata for command topics
            keys.update(value.keys())
    columns = [k for k in _COLUMN_ORDER if k in keys]
    columns += sorted(keys - set(_COLUMN_ORDER))
    return columns


def _cell(column, value):
    if value is None:
        return ''
    if column == 'options':
        parts = []
        for option in value:
            text = str(option[0])
            if len(option) > 1:
                text += f': {option[1]}'
            if len(option) > 2:
                text += ' (' + ', '.join(str(a) for a in option[2:]) + ')'
            parts.append(html.escape(text))
        return '<br>'.join(parts)
    if column == 'flags':
        return html.escape(', '.join(str(f) for f in value))
    return html.escape(str(value))


_HTML_STYLE = """\
  body { font-family: sans-serif; margin: 1em; }
  #cols { margin-bottom: 1em; }
  #cols label { margin-right: 1em; white-space: nowrap; }
  table { border-collapse: collapse; }
  th, td { border: 1px solid #999; padding: 0.25em 0.5em;
           text-align: left; vertical-align: top; }
  th { position: sticky; top: 0; background: #ddd; }
  tr:nth-child(even) { background: #eee; }
  td.topic { font-family: monospace; white-space: nowrap; }
  .hide { display: none; }
"""

_HTML_SCRIPT = """\
  document.querySelectorAll('#cols input').forEach((cb) => {
    cb.addEventListener('change', () => {
      document.querySelectorAll('.col-' + cb.dataset.col).forEach((el) => {
        el.classList.toggle('hide', !cb.checked);
      });
    });
  });
"""


def to_html(meta, title):
    columns = _columns(meta)
    title = html.escape(title)
    parts = [
        '<!DOCTYPE html>',
        '<html lang="en">',
        '<head>',
        '<meta charset="utf-8">',
        f'<title>{title}</title>',
        f'<style>\n{_HTML_STYLE}</style>',
        '</head>',
        '<body>',
        f'<h1>{title}</h1>',
        '<div id="cols">Columns:',
    ]
    for idx, column in enumerate(columns):
        checked = '' if column in _COLUMNS_HIDDEN else ' checked'
        parts.append(f'<label><input type="checkbox" data-col="{idx}"{checked}>'
                     + f'{html.escape(column)}</label>')
    parts += ['</div>', '<table>', '<thead>', '<tr>', '<th>topic</th>']
    for idx, column in enumerate(columns):
        hide = ' hide' if column in _COLUMNS_HIDDEN else ''
        parts.append(f'<th class="col-{idx}{hide}">{html.escape(column)}</th>')
    parts += ['</tr>', '</thead>', '<tbody>']
    for topic in sorted(meta.keys()):
        entry = meta[topic] if meta[topic] is not None else {}
        parts += ['<tr>', f'<td class="topic">{html.escape(topic)}</td>']
        for idx, column in enumerate(columns):
            hide = ' hide' if column in _COLUMNS_HIDDEN else ''
            parts.append(f'<td class="col-{idx}{hide}">{_cell(column, entry.get(column))}</td>')
        parts.append('</tr>')
    parts += ['</tbody>', '</table>',
              f'<script>\n{_HTML_SCRIPT}</script>',
              '</body>', '</html>', '']
    return '\n'.join(parts)


def on_cmd(args):
    fmt = format_resolve(args.format, args.out)
    if fmt == 'yaml':
        try:
            import yaml
        except ImportError:
            print('YAML output requires pyyaml: pip install pyyaml')
            return 1
    with Driver() as d:
        d.log_level = args.jsdrv_log_level
        try:
            device_path = device_select(d.device_paths(), args.device)
        except ValueError as ex:
            print(ex)
            return 1
        d.open(device_path, mode=args.open)
        try:
            meta = metadata_load(d, device_path)
        finally:
            d.close(device_path)
    if fmt == 'json':
        out = to_json(meta)
    elif fmt == 'yaml':
        out = to_yaml(meta)
    else:
        out = to_html(meta, f'{device_path} metadata')
    if args.out is None:
        print(out, end='')
    else:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(out)
    return 0
