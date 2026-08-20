"""ed2k 哈希（vendored from web-mount-packs python-module/ed2k，已去 filewrap 依赖）。

115 盘算法：MD4_BLOCK_SIZE(9728000B = 1024*9500) 分块 → 每块 MD4 → 拼接全部块哈希
→ 若文件大小是块大小的整数倍则补 MD4 空哈希 → 整体再做一次 MD4 → hex。
MD4 由 pycryptodome 提供（/app/vendor，启动时 sys.path 注入）。
"""

from typing import Iterator, Union

from Crypto.Hash.MD4 import MD4Hash

__all__ = ["Ed2kHash", "ed2k_hash"]
__version__ = (0, 0, 2)

MD4_BLOCK_SIZE: int = 1024 * 9500
MD4_EMPTY_HASH: bytes = b"\x31\xd6\xcf\xe0\xd1\x6a\xe9\x31\xb7\x3c\x59\xd7\xe0\xc0\x89\xc0"

Buffer = Union[bytes, bytearray, memoryview]


def ensure_bytes(b: Buffer) -> bytes:
    if isinstance(b, (bytes, bytearray, memoryview)):
        return b
    return memoryview(b)


def bytes_to_chunk_iter(b: Buffer, chunksize: int) -> Iterator[Buffer]:
    m = memoryview(b)
    for i in range(0, len(m), chunksize):
        yield m[i:i + chunksize]


def bio_chunk_iter(f, chunksize: int) -> Iterator[bytes]:
    """文件对象分块读取（替代 filewrap.bio_chunk_iter）。"""
    while True:
        chunk = f.read(chunksize)
        if not chunk:
            break
        yield chunk


class Ed2kHash:
    """流式 ed2k（增量 update + digest）。"""

    def __init__(self, b: Buffer = b""):
        self.block_hashes = bytearray()
        self._last_hashobj = MD4Hash()
        self._remainder = 0
        self.update(b)

    def update(self, b: Buffer):
        size = len(b)
        if not size:
            return
        block_hashes = self.block_hashes
        remainder = self._remainder
        last_hashobj = self._last_hashobj
        m = memoryview(b)
        start = 0
        if remainder:
            start = MD4_BLOCK_SIZE - remainder
            last_hashobj.update(m[:start])
            block_hashes[-16:] = last_hashobj.digest()
        if start < size:
            for start in range(start, size, MD4_BLOCK_SIZE):
                last_hashobj = MD4Hash(m[start:start + MD4_BLOCK_SIZE])
                block_hashes += last_hashobj.digest()
        self._remainder = (size - start) % MD4_BLOCK_SIZE
        self._last_hashobj = last_hashobj

    def digest(self) -> bytes:
        block_hashes = self.block_hashes
        if not self._remainder:
            block_hashes = block_hashes + MD4_EMPTY_HASH
        return MD4Hash(block_hashes).digest()

    def hexdigest(self) -> str:
        return self.digest().hex()


def ed2k_hash(file) -> tuple:
    """计算文件 ed2k。file 可为 bytes/bytearray/memoryview 或支持 read() 的文件对象。

    返回 (filesize, ed2k_hex)。
    """
    if hasattr(file, "getbuffer"):
        file = file.getbuffer()
    if isinstance(file, Buffer):
        chunk_iter = bytes_to_chunk_iter(file, MD4_BLOCK_SIZE)
    else:
        chunk_iter = bio_chunk_iter(file, MD4_BLOCK_SIZE)
    block_hashes = bytearray()
    filesize = 0
    for chunk in map(ensure_bytes, chunk_iter):
        block_hashes += MD4Hash(chunk).digest()
        filesize += len(chunk)
    if not filesize % MD4_BLOCK_SIZE:
        block_hashes += MD4_EMPTY_HASH
    return filesize, MD4Hash(block_hashes).hexdigest()
