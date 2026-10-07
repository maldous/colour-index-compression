from benchmarks.ecoff_instruction_loss import schema


def test_all_opcode_schemas_cover_exactly_one_instruction():
    for opcode in range(64):
        for flag in (0,1):
            _,fields=schema(opcode,(opcode<<26)|(flag<<25))
            assert sum(n for _,n in fields)==26
    assert schema(0x29,0)[0]=='Mem'
    assert schema(0x34,0)[0]=='Mbr'
