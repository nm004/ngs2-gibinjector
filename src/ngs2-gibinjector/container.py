from abc import ABC, abstractmethod

class AbstractChunk(ABC):
    # Commit operations and update the underlying data.
    # It is implementation-defined if the underlying
    # data is mutable or not before and after calling commit().
    @abstractmethod
    def commit(self):
        pass

    @property
    @abstractmethod
    def data(self):
        pass

    def __bool__(self):
        return bool(self.data)

class Chunk(AbstractChunk):
    def __init__(self, data):
        self._data = memoryview(data)

    def commit(self):
        pass

    @property
    def data(self):
        return self._data

class BaseContainer(Chunk, MutableSequence):
    def count(self, val):
        return self._chunks.count(val)

    def index(self, val):
        return self._chunks.index(val)

    def insert(self, key, val):
        self._chunks.insert(key, val)

    def append(self, val):
        self._chunks.append(val)

    def clear(self):
        self._chunks.clear()

    def extend(self, other):
        self._chunks.extend(other)

    def pop(self, key=0):
        self._chunks.pop(key)

    def remove(self, val):
        self._chunks.remove(val)

    def reverse(self):
        self._chunks.reverse()

    def __len__(self):
        return len(self._chunks)

    def __getitem__(self, key):
        return self._chunks[key]

    def __setitem__(self, key, val):
        self._chunks[key] = val

    def __delitem__(self, key):
        del self._chunks[key]

    def __iter__(self):
        return iter(self._chunks)

    def __reversed__(self):
        return reversed(self._chunks)

    def __add__(self, other):
        return self._chunks + other

    def __radd__(self, other):
        return other + self._chunks

    def __iadd__(self, other):
        self._chunks += other

    def __mul__(self, other):
        return self._chunks * other

    def __rmul__(self, other):
        return other * self._chunks

    def __imul__(self, other):
        self._chunks *= other
