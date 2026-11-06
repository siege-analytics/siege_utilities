"""Disk-backed Hadoop API doubles; no Spark, JVM or cluster required."""

import posixpath
import shutil
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit


class HadoopPath:
    def __init__(self, value, child=None):
        if child is not None:
            value = value.toString().rstrip("/") + "/" + child
        self.value = str(value)

    def toString(self):
        return self.value

    def toUri(self):
        return SimpleNamespace(getPath=lambda: urlsplit(self.value).path)

    def getName(self):
        return posixpath.basename(urlsplit(self.value).path)

    def getParent(self):
        uri = urlsplit(self.value)
        if uri.path == "/":
            return None
        parent = posixpath.dirname(uri.path)
        return HadoopPath(f"{uri.scheme}://{uri.netloc}{parent}")

    def equals(self, other):
        return self.value == other.value

    def getFileSystem(self, conf):
        uri = urlsplit(self.value)
        key = f"{uri.scheme}://{uri.netloc}" if uri.scheme else conf.default_fs
        return conf.filesystems[key]


class HadoopFileSystem:
    def __init__(self, uri, root=None):
        self.uri = uri
        self.root = root
        self.renames = []

    def getUri(self):
        return SimpleNamespace(toString=lambda: self.uri)

    def makeQualified(self, path):
        uri = urlsplit(path.toString())
        name = posixpath.normpath(posixpath.join("/user/test", uri.path))
        return HadoopPath(f"{self.uri}{name}")

    def local(self, path):
        if isinstance(path, str):
            path = HadoopPath(path)
        name = urlsplit(self.makeQualified(path).toString()).path
        return self.root / name.lstrip("/") if self.root else Path(name)

    def exists(self, path):
        return self.local(path).exists()

    def isDirectory(self, path):
        return self.local(path).is_dir()

    def mkdirs(self, path):
        self.local(path).mkdir(parents=True, exist_ok=True)
        return True

    def delete(self, path, recursive):
        local = self.local(path)
        if not local.exists():
            return False
        if local.is_dir():
            shutil.rmtree(local) if recursive else local.rmdir()
        else:
            local.unlink()
        return True

    def rename(self, source, destination):
        self.renames.append((source.toString(), destination.toString()))
        src, dst = self.local(source), self.local(destination)
        if not src.exists() or not dst.parent.is_dir():
            return False
        # Hadoop nests the source inside an existing destination directory.
        if dst.is_dir():
            dst /= src.name
        src.rename(dst)
        return True

    def listFiles(self, path, recursive):
        base = self.local(path)
        entries = sorted(base.rglob("*") if recursive else base.iterdir())
        statuses = []
        for entry in entries:
            if entry.is_file():
                child = HadoopPath(path, entry.relative_to(base).as_posix())
                statuses.append(SimpleNamespace(
                    getPath=lambda child=child: child,
                    getLen=lambda size=entry.stat().st_size: size,
                ))
        iterator = iter(statuses)
        remaining = len(statuses)

        def next_status():
            nonlocal remaining
            remaining -= 1
            return next(iterator)

        return SimpleNamespace(hasNext=lambda: remaining > 0, next=next_status)


def spark_session(*filesystems):
    """Build only the Spark attributes used to resolve Hadoop paths."""
    conf = SimpleNamespace(
        default_fs=filesystems[0].uri,
        filesystems={fs.uri: fs for fs in filesystems},
    )
    return SimpleNamespace(
        _jsc=SimpleNamespace(hadoopConfiguration=lambda: conf),
        _jvm=SimpleNamespace(org=SimpleNamespace(apache=SimpleNamespace(
            hadoop=SimpleNamespace(fs=SimpleNamespace(Path=HadoopPath)),
        ))),
    )


class HadoopWriter:
    def __init__(self, fs, files=None):
        self.fs = fs
        self.files = files if files is not None else {
            "part-00000.csv": "id,name\n1,Ada\n", "_SUCCESS": "",
        }
        self.calls = []

    def mode(self, value):
        self.calls.append(("mode", value))
        return self

    def format(self, value):
        self.calls.append(("format", value))
        return self

    def option(self, key, value):
        self.calls.append(("option", key, value))
        return self

    def save(self, destination):
        self.calls.append(("save", destination))
        base = self.fs.local(destination)
        base.mkdir(parents=True, exist_ok=True)
        for name, content in self.files.items():
            target = base / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)


def dataframe(fs, writer=None, *other_filesystems):
    return SimpleNamespace(
        write=writer if writer is not None else HadoopWriter(fs),
        sparkSession=spark_session(fs, *other_filesystems),
    )
