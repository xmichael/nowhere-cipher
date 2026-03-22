#!/usr/bin/env python3
import sys
import argparse
import os

def process_file(input_path, output_path, password_string):
    """
    Symmetrically processes (encrypts/decrypts) a file using the reverse-engineered
    logic of the 1992 DOS CIPHER.COM utility, including all of its original bugs.
    """
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found.")
        sys.exit(1)

    # 1. Parse password as decimal (The C atol() bug)
    try:
        key = int(password_string) & 0xFFFFFFFF
    except ValueError:
        key = 0  # Non-numeric strings fail parsing and become 0

    # 2. Mutate Key (XOR and ROL 8)
    key ^= 0xAE3FB9C2
    key = ((key << 8) & 0xFFFFFFFF) | (key >> 24)
    
    # 3. Truncate to 16-bit seed (The srand() 16bit bug)
    seed = key & 0xFFFF

    print(f"Processing '{input_path}'...")
    print(f"Effective 16-bit PRNG seed: 0x{seed:04X}")

    with open(input_path, "rb") as f:
        data = bytearray(f.read())

    # The buffer chunk size from the original assembly (0x3FFC)
    CHUNK_SIZE = 16380 

    # 4. Process exactly as the binary's chunking loop does
    for chunk_start in range(0, len(data), CHUNK_SIZE):
        chunk_end = min(chunk_start + CHUNK_SIZE, len(data))
        bytes_read = chunk_end - chunk_start
        
        # The block math bug: (bytes_read / 4) + 1
        blocks_to_run = (bytes_read // 4) + 1
        
        for si in range(blocks_to_run):
            # First rand() is generated and discarded (The 32-bit shift bug)
            seed = (seed * 0x015A4E35 + 1) & 0xFFFFFFFF
            
            # Second rand() actually becomes the XOR key
            seed = (seed * 0x015A4E35 + 1) & 0xFFFFFFFF
            rand_val = (seed >> 16) & 0x7FFF

            # Only XOR into the file if we are within the actual bytes read
            # (Simulates the program over-processing memory but not writing the overflow to disk)
            offset = chunk_start + (si * 4)
            if offset < chunk_end:
                data[offset] ^= (rand_val & 0xFF)
            if offset + 1 < chunk_end:
                data[offset + 1] ^= ((rand_val >> 8) & 0xFF)
            # Bytes offset+2 and offset+3 are untouched (XORed with 0)

    try:
        with open(output_path, "wb") as f:
            f.write(data)
        print(f"[+] Success! File written to '{output_path}'")
    except IOError as e:
        print(f"Error writing to output file: {e}")
        sys.exit(1)


def main():
    epilog_text = """
VULNERABILITY NOTICE:
This tool perfectly emulates the 4 programming errors found in the original 
1992 DOS CIPHER.COM binary:

  1. The original program parsed passwords using the C standard
     library atol() function. Because atol() stops at the first
     non-numeric character, ANY password that is purely text (e.g.,
     "foobar", "HELLO", "SECRET") silently evaluates to 0.  Therefore, all
     text-only passwords produce the exact same encryption key!

  2. Despite attempts to mutate a 32-bit key, the author passed the
    result to a 16-bit srand() function, thus discarding half
    the key's entropy.

  3. A bug in 32-bit bit-shifting causes the first random number to be
     discarded entirely and the second half of the 4-byte block to be
     XORed with 0.  Exactly 50% of the file (every 3rd and 4th byte)
     is completely unencrypted.

  4. Chunking Bug: The file is processed in 16,380 byte chunks. Due to an off-by-one 
     error in the loop math ((bytes/4) + 1), the PRNG advances by an extra block at every 
     chunk boundary, permanently misaligning the keystream if not strictly emulated.
    """

    parser = argparse.ArgumentParser(
        description="Decryptor/Encryptor for the 1992 DOS CIPHER.COM utility.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog_text
    )

    parser.add_argument("-i", "--input", required=True, help="Path to the input file to process")
    parser.add_argument("-o", "--output", required=True, help="Path to save the output file")
    parser.add_argument("-p", "--password", required=True, help="The password/key used to cipher the file")

    args = parser.parse_args()

    process_file(args.input, args.output, args.password)

if __name__ == "__main__":
    main()
