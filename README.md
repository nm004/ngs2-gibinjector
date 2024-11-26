NGS2 gib injector
=================
Author: Nozomi Miyamori

NGS2 gib injector is a modding tool for NINJA GAIDEN SIGMA 2 PC.
It injects missing gib mesh objects and gib textures to TMC files, thus the
gib splatter effect in the game works correctly.

Requirements
------------

- Python 3 (3.13 or later)

### How to use

```
cd src
mkdir mods
test -e databin && test -e e_nin_c_05.dds && python -m gibinjector
```

License
-------

CC0
