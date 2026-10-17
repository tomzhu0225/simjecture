"""Spool complete command output while rotating the live console view."""

import gzip
import shutil
import threading


class ConsoleLog:
    def __init__(self, source, output, root, *, segment_bytes=64 * 1024**2):
        self.source, self.output, self.root = source, output, root
        self.segment_bytes = segment_bytes
        self.error = None
        self.thread = threading.Thread(target=self.capture, daemon=True)
        self.thread.start()

    def capture(self):
        try:
            count = max(
                (
                    int(p.name.split(".")[1])
                    for p in self.root.glob("output.[0-9][0-9][0-9][0-9][0-9][0-9].log.gz")
                ),
                default=0,
            )
            read = getattr(self.source, "read1", self.source.read)
            while block := read(64 * 1024):
                view = memoryview(block)
                while view:
                    room = self.segment_bytes - self.output.tell()
                    if room <= 0:
                        count += 1
                        self.output.flush()
                        self.output.seek(0)
                        target = self.root / f"output.{count:06d}.log.gz"
                        temporary = target.with_name("." + target.name)
                        with gzip.open(temporary, "wb", compresslevel=1) as archive:
                            shutil.copyfileobj(self.output, archive)
                        temporary.replace(target)
                        self.output.seek(0)
                        self.output.truncate()
                        room = self.segment_bytes
                    self.output.write(view[:room])
                    self.output.flush()
                    view = view[room:]
        except OSError as error:
            self.error = error
        finally:
            self.source.close()

    def join(self):
        self.thread.join()
