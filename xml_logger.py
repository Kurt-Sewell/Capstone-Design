import os, tempfile, xml.etree.ElementTree as ET
from datetime import datetime

def _indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for e in elem:
            _indent(e, level+1)
        if not e.tail or not e.tail.strip():
            e.tail = i
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = i


class XMLLogger:
    """
    Creates/update an XML log file. Writes atomically (safe even if program quits).
    Suitable for real-time logging.
    """
    def __init__(self, path="session_log.xml", session_meta=None, rotate_daily=True):
        self.base_path = path
        self.rotate_daily = rotate_daily
        self.session_date = datetime.now().strftime("%Y-%m-%d")
        self.path = self._current_path()

        self.root = ET.Element("FSAE_Torsion_Session", {
            "started": datetime.now().isoformat(timespec="seconds")
        })
        if session_meta:
            meta = ET.SubElement(self.root, "SessionMeta")
            for k, v in session_meta.items():
                ET.SubElement(meta, k).text = str(v)

        self.samples = ET.SubElement(self.root, "Samples")
        self.sample_count = 0
        self.flush_every = 20  # default, dashboard overrides to 1
        self._write_atomic()

    def _current_path(self):
        if self.rotate_daily:
            base, ext = os.path.splitext(self.base_path)
            return f"{base}.{self.session_date}{ext or '.xml'}"
        return self.base_path

    def _write_atomic(self):
        """Write XML using a temp file created in SAME DIRECTORY (prevents cross-device errors)."""
        _indent(self.root)
        tree = ET.ElementTree(self.root)

        target_dir = os.path.abspath(os.path.dirname(self.path) or ".")
        os.makedirs(target_dir, exist_ok=True)

        # Create temporary file in target directory (important!)
        fd, tmp = tempfile.mkstemp(prefix=".xmltmp_", suffix=".xml", dir=target_dir)
        os.close(fd)

        try:
            tree.write(tmp, encoding="utf-8", xml_declaration=True)
            os.replace(tmp, self.path)   # atomic if same filesystem
        finally:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except:
                    pass

    def add_sample(self, data: dict):
        # rotate log at midnight if enabled
        if self.rotate_daily:
            today = datetime.now().strftime("%Y-%m-%d")
            if today != self.session_date:
                self.session_date = today
                self.path = self._current_path()
                self.root = ET.Element("FSAE_Torsion_Session", {
                    "started": datetime.now().isoformat(timespec="seconds")
                })
                self.samples = ET.SubElement(self.root, "Samples")
                self.sample_count = 0

        # construct sample node
        sample = ET.SubElement(self.samples, "Sample", {
            "t": datetime.now().isoformat(timespec="milliseconds")
        })
        self._add_data(sample, data)
        self.sample_count += 1

        if self.sample_count % self.flush_every == 0:
            self._write_atomic()

    def _add_data(self, parent, data):
        """Recursive helper to store nested dicts cleanly."""
        for key, value in data.items():
            if isinstance(value, dict):
                node = ET.SubElement(parent, key)
                self._add_data(node, value)
            elif isinstance(value, (list, tuple)):
                node = ET.SubElement(parent, key)
                for i, v in enumerate(value):
                    sub = ET.SubElement(node, f"item_{i}")
                    sub.text = str(v)
            else:
                ET.SubElement(parent, key).text = str(value)

    def flush(self):
        self._write_atomic()

    def close(self):
        self._write_atomic()
