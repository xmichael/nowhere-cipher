# nowhere utils cipher

Python reimplementation of a DOS era cipher algorithm


## USAGE

**Usage:**
```bash
python recover.py -i encrypted.zip -o restored.zip -p 1234
```

`recover.py` :  This script perfectly recreates the original encryption/decryption routine, including all four bugs (see bellow). Because `CIPHER.COM` is a pure XOR stream cipher, this script can be used to both encrypt and decrypt files identically to the 1992 DOS binary.

## Background

Back in early 1990s, most people were not connected to WWW (except for BBSs and such I think) and there were lots of, popular at the time, utilities for doing things like file encryption.

This is a reimplementation from scratch of an encrypt/decrypt cipher which I think was part of "Nowhere Utils by Nowhere Man and [Nuke]" 1992. The original author's real name is unknown.

**The original algorithm has bugs and is useless for serious encryption. This is only useful for digital archiving purposes** i.e. in case you stumble upon a >30 year old encrypted file using that software and have no way to access it.

## Implementation details

The original CIPHER.COM is 6KB LZEXE self-compressed executable. When uncompressed it is a simple binary produced from Borland C.

The cipher algortithm itself is a simple XOR and 32bit ROL 8 , **except** that it has bugs that affect the actual encryption. Therefore, in order to make bit-perfect repropruction of the encryption/decryption , we need to emulate those bugs.

## Cryptographic bugs

### 1. The `atol()` String Parsing Bug

The program accepts a command-line password, which it parses using the standard C library `atol()` (ASCII to Long) function to generate a 32-bit key. 

`atol()` expects base-10 digits. If it encounters a non-numeric character, it immediately stops parsing. If a user inputs a text password (e.g., `"foobar"`, `"SECRET"`, `"PASSWORD"`), `atol()` returns `0`. 

* I.e. **Every single text-only password results in the exact same encryption key (`0`).**

### 2. The `srand()` Truncation Bug

The author attempted to mutate the 32-bit key by XORing it with a
hardcoded mask (`0xAE3FB9C2`) and performing a 32-bit left rotation
(ROL 8). The mutated 32-bit key is then passed to the C standard
library `srand()` function to seed the Pseudo-Random Number Generator
(PRNG).

However, In 16-bit Borland C, `srand()` only accepts a 16-bit
integer. The upper 16 bits of the meticulously mutated key are
entirely discarded.

Therefore, the encryption keyspace is permanently
reduced to a maximum of **65,536 possible keys**, which can be
brute-forced in milliseconds on modern hardware.

### 3. 50% of the encrypted file remains plaintext (!)

The core encryption loop processes the file in 4-byte (32-bit) blocks. The author attempted to generate a 32-bit random keystream block using logic similar to this:
```c
long random_val = (rand() << 16) | rand();
```

However `rand()` returns a 16-bit `int`. When shifting a 16-bit integer left by 16 (`<< 16`), the bits are pushed entirely out of the register, leaving `0`. The code essentially does `0 | rand()`.

Therefore, when the 4-byte block is XORed against the file, the first two bytes are encrypted with the random number, but **the last two bytes are XORed with `0x00`**. Exactly 50% of the file (every 3rd and 4th byte) is left completely unencrypted in plaintext!

### 4. Chunking Boundary Bug

This is very substle but completely changes the actual file.

The cipher reads and encrypts files in 16,380-byte (`0x3FFC`) chunks. To calculate how many 4-byte blocks to process per chunk, the author probably did something like:
```c
int blocks_to_process = (bytes_read / 4) + 1;
```

However, because of the unconditional `+ 1`, a full 16,380-byte chunk results in 4,096 loop iterations instead of 4,095. The program generates an extra PRNG number and XORs it into unallocated memory. It only writes the correct 16,380 bytes back to disk, hiding the memory corruption.

The result is that, because the PRNG silently advances by one extra block at every 16KB boundary, the keystream desynchronizes. If a modern script tries to decrypt a file >16KB without strictly emulating this off-by-one error, the end of the file will be corrupted.


## Disclaimer

This project is for educational purposes, historical software preservation, and cryptographic research. **Do not use to it for securing your files**.
