#!/usr/bin/env python3
import os, struct, time, zipfile
from xml.sax.saxutils import escape

FILE_NAME="replay_main_11-09-2026_00-00.bin"
action_time_offset=30







FOLDER = os.path.dirname(os.path.abspath(__file__))
HEADERS = ("Index", "Elapsed (s)", "Wall clock", "Delta (ms)", "Length (bytes)", "Text", "Hex")

MANIFEST = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">'
    '<manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.spreadsheet"/>'
    '<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>'
    '</manifest:manifest>'
)

CONTENT_OPEN = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<office:document-content'
    ' xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
    ' xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"'
    ' xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"'
    ' office:version="1.2"><office:body><office:spreadsheet><table:table table:name="Replay">'
)
CONTENT_CLOSE = '</table:table></office:spreadsheet></office:body></office:document-content>'


def read_replay(path):
    with open(path, "rb") as file:
        data = file.read()
    if data[:4] != b"RPL1":
        raise ValueError(f"{path} is not a replay file")
    start_time = struct.unpack_from("<d", data, 4)[0]
    offset = 12
    elapsed_ms = 0
    records = []
    while offset + 6 <= len(data):
        delta, length = struct.unpack_from("<IH", data, offset)
        offset += 6
        payload = data[offset:offset + length]
        if len(payload) < length:
            break
        offset += length
        elapsed_ms += delta
        records.append((elapsed_ms, delta, payload))
    return start_time, records


def string_cell(value):
    return f'<table:table-cell office:value-type="string"><text:p>{escape(str(value))}</text:p></table:table-cell>'


def number_cell(value):
    return f'<table:table-cell office:value-type="float" office:value="{value}"><text:p>{value}</text:p></table:table-cell>'


def wall_clock(timestamp):
    return time.strftime("%m-%d-%Y %H:%M:%S", time.localtime(timestamp)) + f".{int((timestamp % 1) * 1000):03d}"


def build_content(start_time, records):
    rows = ["<table:table-row>" + "".join(string_cell(header) for header in HEADERS) + "</table:table-row>"]
    for index, (elapsed_ms, delta, payload) in enumerate(records, 1):
        if index > 1 and delta >= action_time_offset * 1000:
            rows.extend(["<table:table-row><table:table-cell/></table:table-row>"] * 3)
        cells = (
            number_cell(index),
            number_cell(round(elapsed_ms / 1000, 3)),
            string_cell(wall_clock(start_time + elapsed_ms / 1000)),
            number_cell(delta),
            number_cell(len(payload)),
            string_cell(repr(payload)[2:-1]),
            string_cell(payload.hex(" ")),
        )
        rows.append("<table:table-row>" + "".join(cells) + "</table:table-row>")
    return CONTENT_OPEN + "".join(rows) + CONTENT_CLOSE


def write_ods(path, content):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/vnd.oasis.opendocument.spreadsheet", compress_type=zipfile.ZIP_STORED)
        archive.writestr("META-INF/manifest.xml", MANIFEST, compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("content.xml", content, compress_type=zipfile.ZIP_DEFLATED)


def main():
    source = os.path.join(FOLDER, FILE_NAME)
    output = os.path.splitext(source)[0] + ".ods"
    start_time, records = read_replay(source)
    write_ods(output, build_content(start_time, records))
    print(f"Wrote {len(records)} commands to {output}")


if __name__ == "__main__":
    main()