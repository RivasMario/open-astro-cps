import pefile, capstone, re

pe = pefile.PE(r"C:\Program Files (x86)\Motorola\ASTRO 25 Products\ASTRO 25 Portable Depot\PatPortDepot.exe")
image_base = pe.OPTIONAL_HEADER.ImageBase

for s in pe.sections:
    start = image_base + s.VirtualAddress
    end = start + s.Misc_VirtualSize
    if start <= 0x963000 < end:
        data = s.get_data()
        start_off = 0x962000 - start
        end_off = 0x963f00 - start
        cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        
        matrix = []
        for insn in cs.disasm(data[start_off:end_off], 0x962000):
            m = re.search(r'0x162[a-f0-9]{4}', insn.op_str)
            if m:
                addr = int(m.group(0), 16)
                str_rva = addr - image_base
                for s2 in pe.sections:
                    if s2.VirtualAddress <= str_rva < s2.VirtualAddress + s2.Misc_VirtualSize:
                        soff = str_rva - s2.VirtualAddress
                        sval = s2.get_data()[soff:soff+16].split(b'\x00')[0].decode('ascii', errors='replace')
                        matrix.append((hex(insn.address), insn.mnemonic + ' ' + insn.op_str, hex(addr), sval))
                        break
        
        print(f"Total options found: {len(matrix)}")
        for idx, (ia, iop, sa, sval) in enumerate(matrix):
            print(f"[{idx:2d}] {sval:12s} ({sa}) @ {ia}: {iop}")
        break
