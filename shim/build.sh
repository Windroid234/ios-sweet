#!/bin/bash
# Build the shim and wrap it in a boot.img v4 for Nothing Phone (2) (SM8475 / pong).
set -euo pipefail
cd "$(dirname "$0")"

if command -v aarch64-linux-gnu-gcc >/dev/null 2>&1; then
	CC=aarch64-linux-gnu-gcc
	OBJCOPY=aarch64-linux-gnu-objcopy
	READELF=aarch64-linux-gnu-readelf
	NM=aarch64-linux-gnu-nm
	LD="aarch64-linux-gnu-gcc"
	LDFLAGS="-static -T shim.ld -Wl,--build-id=none -Wl,--no-warn-rwx-segments -Wl,-N"
else
	CC="clang --target=aarch64-linux-gnu"
	OBJCOPY=llvm-objcopy
	READELF=llvm-readelf
	NM=llvm-nm
	LD="ld.lld"
	LDFLAGS="-T shim.ld --build-id=none --image-base=0"
fi

CFLAGS="-O2 -ffreestanding -nostdlib -fno-pic -fno-jump-tables -mgeneral-regs-only -mstrict-align -fno-stack-protector -Wall -Wextra"
mkdir -p out
for f in start.S shim.c console.c mmu.c fdt.c loader.c ufs.c; do
	$CC $CFLAGS -c $f -o out/${f%.*}.o
done

# The image runs wherever ABL puts it with no relocation pass: only the
# header's image_size (start.o, linked at 0) may be an absolute address.
abs=$($READELF -r out/shim.o out/console.o out/mmu.o out/fdt.o out/loader.o out/ufs.o | grep -c ABS64 || true)
[ "$abs" = 0 ] || { echo "error: $abs absolute relocations in C objects" >&2; exit 1; }

if [ "$LD" = "ld.lld" ]; then
	$LD $LDFLAGS out/start.o out/shim.o out/console.o out/mmu.o out/fdt.o out/loader.o out/ufs.o -o out/shim.elf
else
	$LD $CFLAGS $LDFLAGS out/start.o out/shim.o out/console.o out/mmu.o out/fdt.o out/loader.o out/ufs.o -o out/shim.elf
fi

$OBJCOPY -O binary out/shim.elf out/Image
# ABL copies the file; pad to image_size so .bss/stacks exist as zeroed bytes.
size=$($NM out/shim.elf | awk '$3=="_end"{print strtonum("0x"$1)}')
truncate -s "$size" out/Image

# Ramdisk: an xnu payload (tools/mkpayload.py) if given as $1, else an empty
# newc cpio (ABL dislikes a zero-size ramdisk on some builds) -> diagnostics.
if [ -n "${1:-}" ]; then
	cp "$1" out/ramdisk.bin
else
	(cd out && rm -rf rd && mkdir rd && cd rd && find . | cpio -o -H newc --quiet | gzip -9 > ../ramdisk.bin)
fi

# Build Android Boot Image Header Version 4 (Nothing Phone 2 GKI)
mkbootimg --header_version 4 --kernel out/Image --ramdisk out/ramdisk.bin \
	--os_version 17.0.0 --os_patch_level 2035-06 \
	-o out/shim-boot.img

# Host render of the console layout
gcc -O1 -Wall -o out/host_test console.c host_test.c && ./out/host_test
ls -l out/Image out/shim-boot.img
