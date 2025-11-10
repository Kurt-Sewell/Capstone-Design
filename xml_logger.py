# xml_logger.py
# Saves samples to XML inside "xml files" next to this script.
# Atomic writes in the same directory (Pi/Windows safe). Supports events.

import os, datetime, tempfile, xml.etree.ElementTree as ET

class XMLLogger:
    def __init__(self, path, session_meta=None, rotate_daily=True, subdir_name="xml files"):
        filename = os.path.basename(path)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        target_dir = os.path.join(base_dir, subdir_name) if subdir_name else base_dir
        os.makedirs(target_dir, exist_ok=True)

        self.path = os.path.join(target_dir, filename)
        self.rotate_daily = rotate_daily
        self.flush_every = 1
        self.sample_count = 0
        self._last_day = datetime.date.today()

        self.root = ET.Element("Session")
        if session_meta:
            for k, v in session_meta.items():
                self.root.set(k, str(v))
        self.events = ET.SubElement(self.root, "Events")
        self.samples = ET.SubElement(self.root, "Samples")

        self._write_atomic()

    # --- public ---
    def add_sample(self, data: dict):
        s = ET.SubElement(self.samples, "Sample", {"t": self._now()})
        self._dict_to_xml(s, data)
        self.sample_count += 1
        self._maybe_rotate()
        if self.sample_count % self.flush_every == 0:
            self.flush()

    def add_event(self, etype: str, meta: dict | None = None):
        e = ET.SubElement(self.events, "Event", {"t": self._now(), "type": etype})
        if meta:
            self._dict_to_xml(e, meta)
        self.flush()

    def flush(self):
        self._write_atomic()

    def close(self):
        self.flush()

    # --- helpers ---
    def _dict_to_xml(self, parent, d: dict):
        for k, v in d.items():
            if isinstance(v, dict):
                child = ET.SubElement(parent, k)
                self._dict_to_xml(child, v)
            else:
                ET.SubElement(parent, k).text = str(v)

    def _write_atomic(self):
        dirpath = os.path.dirname(self.path)
        fd, tmp = tempfile.mkstemp(prefix="xmltmp_", suffix=".xml", dir=dirpath)
        try:
            with os.fdopen(fd, "wb") as f:
                ET.ElementTree(self.root).write(f, encoding="utf-8", xml_declaration=True)
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp) and tmp != self.path:
                try: os.remove(tmp)
                except: pass

    def _maybe_rotate(self):
        if not self.rotate_daily:
            return
        today = datetime.date.today()
        if today != self._last_day:
            base, ext = os.path.splitext(self.path)
            rotated = f"{base}.{self._last_day.isoformat()}{ext}"
            try: os.replace(self.path, rotated)
            except FileNotFoundError: pass
            self._last_day = today

    def _now(self):
        return datetime.datetime.now().isoformat(timespec="milliseconds")


