from miasm2.expression.expression import *
from miasm2.expression.simplifications import expr_simp
from miasm2.core import asmbloc
import logging


log_to_c_h = logging.getLogger("ir_helper")
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(levelname)-5s: %(message)s"))
log_to_c_h.addHandler(console_handler)
log_to_c_h.setLevel(logging.WARN)


def ExprInt_toC(self):
    return str(self)


def ExprId_toC(self):
    if isinstance(self.name, asmbloc.asm_label):
        return "0x%x" % self.name.offset
    return str(self)


def ExprAff_toC(self):
    return "%s = %s" % (self.dst.toC(), self.src.toC())


def ExprCond_toC(self):
    return "(%s?%s:%s)" % (self.cond.toC(), self.src1.toC(), self.src2.toC())


def ExprMem_toC(self):
    return "MEM_LOOKUP_%.2d(vm_mngr, %s)" % (self._size, self.arg.toC())


def ExprOp_toC(self):
    dct_shift = {'a>>': "right_arith",
                 '>>': "right_logic",
                 '<<': "left_logic",
                 'a<<': "left_logic",
                 }
    dct_rot = {'<<<': 'rot_left',
               '>>>': 'rot_right',
               }
    dct_div = {'div8': "div_op",
               'div16': "div_op",
               'div32': "div_op",
               'idiv32': "div_op",  # XXX to test
               'rem8': "rem_op",
               'rem16': "rem_op",
               'rem32': "rem_op",
               'irem32': "rem_op",  # XXX to test
               '<<<c_rez': 'rcl_rez_op',
               '<<<c_cf': 'rcl_cf_op',
               '>>>c_rez': 'rcr_rez_op',
               '>>>c_cf': 'rcr_cf_op',
               }
    if len(self.args) == 1:
        if self.op == 'parity':
            return "parity(%s&0x%x)" % (
                self.args[0].toC(), size2mask(self.args[0].size))
        elif self.op == '!':
            return "(~ %s)&0x%x" % (
                self.args[0].toC(), size2mask(self.args[0].size))
        elif self.op in ["hex2bcd", "bcd2hex"]:
            return "%s_%d(%s)" % (
                self.op, self.args[0].size, self.args[0].toC())
        elif (self.op.startswith("double_to_") or
              self.op.endswith("_to_double")   or
              self.op.startswith("access_")    or
              self.op.startswith("load_")      or
              self.op in ["-", "ftan", "frndint", "f2xm1",
                "fsin", "fsqrt", "fabs", "fcos"]):
            return "%s(%s)" % (self.op, self.args[0].toC())
        else:
            raise ValueError('unknown op: %r' % self.op)
    elif len(self.args) == 2:
        if self.op == "==":
            return '(((%s&0x%x) == (%s&0x%x))?1:0)' % (
                self.args[0].toC(), size2mask(self.args[0].size),
                self.args[1].toC(), size2mask(self.args[1].size))
        elif self.op in dct_shift:
            return 'shift_%s_%.2d(%s , %s)' % (dct_shift[self.op],
                                               self.args[0].size,
                                               self.args[0].toC(),
                                               self.args[1].toC())
        elif self.is_associative():
            o = ['(%s&0x%x)' % (a.toC(), size2mask(a.size)) for a in self.args]
            o = str(self.op).join(o)
            return "((%s)&0x%x)" % (o, size2mask(self.args[0].size))
        elif self.op in ["%", "/"]:
            o = ['(%s&0x%x)' % (a.toC(), size2mask(a.size)) for a in self.args]
            o = str(self.op).join(o)
            return "((%s)&0x%x)" % (o, size2mask(self.args[0].size))
        elif self.op in ['-']:
            return '(((%s&0x%x) %s (%s&0x%x))&0x%x)' % (
                self.args[0].toC(), size2mask(self.args[0].size),
                str(self.op),
                self.args[1].toC(), size2mask(self.args[1].size),
                size2mask(self.args[0].size))
        elif self.op in dct_rot:
            return '(%s(%s, %s, %s) &0x%x)' % (dct_rot[self.op],
                                               self.args[0].size,
                                               self.args[0].toC(),
                                               self.args[1].toC(),
                                               size2mask(self.args[0].size))
        elif self.op in ['bsr', 'bsf']:
            return 'my_%s(%s, %s)' % (self.op,
                                      self.args[0].toC(),
                                      self.args[1].toC())
        elif self.op.startswith('cpuid'):
            return "%s(%s, %s)" % (
                self.op, self.args[0].toC(), self.args[1].toC())
        elif self.op.startswith("fcom"):
            return "%s(%s, %s)" % (
                self.op, self.args[0].toC(), self.args[1].toC())
        elif self.op in ["fadd", "fsub", "fdiv", 'fmul', "fscale"]:
            return "%s(%s, %s)" % (
                self.op, self.args[0].toC(), self.args[1].toC())
        elif self.op == "segm":
            return "segm2addr(vmcpu, %s, %s)" % (
                self.args[0].toC(), self.args[1].toC())
        elif self.op in ['udiv', 'umod', 'idiv', 'imod']:
            return '%s%d(vmcpu, %s, %s)' % (self.op,
                                            self.args[0].size,
                                            self.args[0].toC(),
                                            self.args[1].toC())
        elif self.op in ["bcdadd", "bcdadd_cf"]:
            return "%s_%d(%s, %s)" % (self.op, self.args[0].size,
                                      self.args[0].toC(),
                                      self.args[1].toC())
        else:
            raise ValueError('unknown op: %r' % self.op)
    elif len(self.args) == 3 and self.op in dct_div:
        return '(%s(%s, %s, %s, %s) &0x%x)' % (dct_div[self.op],
                                               self.args[0].size,
                                               self.args[0].toC(),
                                               self.args[1].toC(),
                                               self.args[2].toC(),
                                               size2mask(self.args[0].size))
    elif len(self.args) >= 3 and self.is_associative():  # ?????
        o = ['(%s&0x%x)' % (a.toC(), size2mask(a.size)) for a in self.args]
        o = str(self.op).join(o)
        r = "((%s)&0x%x)" % (o, size2mask(self.args[0].size))
        return r
    else:
        raise NotImplementedError('unknown op: %s' % self)


def ExprSlice_toC(self):
    # XXX check mask for 64 bit & 32 bit compat
    return "((%s>>%d) & 0x%X)" % (self.arg.toC(),
                                  self.start,
                                  (1 << (self.stop - self.start)) - 1)


def ExprCompose_toC(self):
    out = []
    # XXX check mask for 64 bit & 32 bit compat
    dst_cast = "uint%d_t" % self.size
    for x in self.args:
        out.append("(((%s)(%s & 0x%X)) << %d)" % (dst_cast,
                                                  x[0].toC(),
                  (1 << (x[2] - x[1])) - 1,
            x[1]))
    out = ' | '.join(out)
    return '(' + out + ')'


ExprInt.toC = ExprInt_toC
ExprId.toC = ExprId_toC
ExprAff.toC = ExprAff_toC
ExprCond.toC = ExprCond_toC
ExprMem.toC = ExprMem_toC
ExprOp.toC = ExprOp_toC
ExprSlice.toC = ExprSlice_toC
ExprCompose.toC = ExprCompose_toC

prefetch_id = []
prefetch_id_size = {}
for size in [8, 16, 32, 64]:
    prefetch_id_size[size] = []
    for i in xrange(20):
        name = 'pfmem%.2d_%d' % (size, i)
        c = ExprId(name, size)
        globals()[name] = c
        prefetch_id.append(c)
        prefetch_id_size[size].append(c)


reg_float_st0 = 'float_st0'
reg_float_st1 = 'float_st1'
reg_float_st2 = 'float_st2'
reg_float_st3 = 'float_st3'
reg_float_st4 = 'float_st4'
reg_float_st5 = 'float_st5'
reg_float_st6 = 'float_st6'
reg_float_st7 = 'float_st7'


float_st0 = ExprId(reg_float_st0, 64)
float_st1 = ExprId(reg_float_st1, 64)
float_st2 = ExprId(reg_float_st2, 64)
float_st3 = ExprId(reg_float_st3, 64)
float_st4 = ExprId(reg_float_st4, 64)
float_st5 = ExprId(reg_float_st5, 64)
float_st6 = ExprId(reg_float_st6, 64)
float_st7 = ExprId(reg_float_st7, 64)

fltregs32_str = ["ST(%d)" % i for i in xrange(8)]
fltregs32_expr = [ExprId(x, 64) for x in fltregs32_str]


float_id_e = [
    float_st0,
    float_st1,
    float_st2,
    float_st3,
    float_st4,
    float_st5,
    float_st6,
    float_st7,
] + fltregs32_expr


def init_arch_C(arch):
    arch.id2Cid = {}
    for x in arch.regs.all_regs_ids + prefetch_id:
        arch.id2Cid[x] = ExprId('vmcpu->' + str(x), x.size)
    for i in xrange(8):
        arch.id2Cid[ExprId('ST(%d)' % i, 64)] = ExprId(
            'vmcpu->' + "float_st%d" % i, 64)

    arch.id2newCid = {}

    for x in arch.regs.all_regs_ids + prefetch_id:
        arch.id2newCid[x] = ExprId('vmcpu->%s_new' % x, x.size)

    for i in xrange(8):
        arch.id2newCid[ExprId('ST(%d)' % i, 64)] = ExprId(
            'vmcpu->' + "float_st%d_new" % i, 64)


def patch_c_id(arch, e):
    return e.replace_expr(arch.id2Cid)


def patch_c_new_id(arch, e):
    return e.replace_expr(arch.id2newCid)


mask_int = 0xffffffffffffffff


pre_instr_test_exception = r"""
// pre instruction test exception
if (vm_mngr->exception_flags) {
    %s;
    RETURN_PC;
}
"""


code_exception_fetch_mem_at_instr = r"""
// except fetch mem at instr
if (vm_mngr->exception_flags & EXCEPT_DO_NOT_UPDATE_PC) {
    %s;
    RETURN_PC;
}
"""
code_exception_fetch_mem_post_instr = r"""
// except fetch mem post instr
if (vm_mngr->exception_flags) {
    %s;
    RETURN_PC;
}
"""


code_exception_fetch_mem_at_instr_noautomod = r"""
// except fetch mem at instr noauto
if ((vm_mngr->exception_flags & ~EXCEPT_CODE_AUTOMOD) & EXCEPT_DO_NOT_UPDATE_PC) {
    %s;
    RETURN_PC;
}
"""
code_exception_fetch_mem_post_instr_noautomod = r"""
// except post instr noauto
if (vm_mngr->exception_flags & ~EXCEPT_CODE_AUTOMOD) {
    %s;
    RETURN_PC;
}
"""


code_exception_at_instr = r"""
// except at instr
if (vmcpu->exception_flags && vmcpu->exception_flags > EXCEPT_NUM_UPDT_EIP) {
    %s;
    RETURN_PC;
}
"""

code_exception_post_instr = r"""
// except post instr
if (vmcpu->exception_flags) {
    if (vmcpu->exception_flags > EXCEPT_NUM_UPDT_EIP)
      %s;
    else
      %s;
    RETURN_PC;
}
"""


code_exception_at_instr_noautomod = r"""
if ((vmcpu->exception_flags & ~EXCEPT_CODE_AUTOMOD) && vmcpu->exception_flags > EXCEPT_NUM_UPDT_EIP) {
    %s;
    RETURN_PC;
}
"""

code_exception_post_instr_noautomod = r"""
if (vmcpu->exception_flags & ~EXCEPT_CODE_AUTOMOD) {
    if (vmcpu->exception_flags > EXCEPT_NUM_UPDT_EIP)
      %s;
    else
      %s;
    RETURN_PC;
}
"""


my_size_mask = {1: 1, 2: 3, 3: 7, 7: 0x7f,
                8: 0xFF,
                16: 0xFFFF,
                32: 0xFFFFFFFF,
                64: 0xFFFFFFFFFFFFFFFFL}

exception_flags = ExprId('exception_flags', 32)


def set_pc(my_ir, src):
    dst = my_ir.jit_pc
    if not isinstance(src, Expr):
        src = ExprInt_from(dst, src)
    e = ExprAff(dst, src.zeroExtend(dst.size))
    return e


def Expr2C(my_ir, l, exprs, gen_exception_code=False):
    id_to_update = []
    out = ["// %s" % (l)]
    out_pc = []

    dst_dict = {}
    src_mem = {}

    prefect_index = {8: 0, 16: 0, 32: 0, 64: 0}
    new_expr = []

    e = set_pc(my_ir, l.offset & mask_int)
    #out.append("%s;" % patch_c_id(my_ir.arch, e).toC())

    pc_is_dst = False
    fetch_mem = False
    set_exception_flags = False
    for e in exprs:
        assert(isinstance(e, ExprAff))
        assert(not isinstance(e.dst, ExprOp))
        if isinstance(e.dst, ExprId):
            if not e.dst in dst_dict:
                dst_dict[e.dst] = []
            dst_dict[e.dst].append(e)
        else:
            new_expr.append(e)
        # test exception flags
        ops = get_expr_ops(e)
        if set(['umod', 'udiv']).intersection(ops):
            set_exception_flags = True
        if e.dst == exception_flags:
            set_exception_flags = True
            # TODO XXX test function whose set exception_flags

        # search mem lookup for generate mem read prefetch
        rs = e.src.get_r(mem_read=True)
        for r in rs:
            if (not isinstance(r, ExprMem)) or r in src_mem:
                continue
            fetch_mem = True
            index = prefect_index[r.size]
            prefect_index[r.size] += 1
            pfmem = prefetch_id_size[r.size][index]
            src_mem[r] = pfmem

    for dst, exs in dst_dict.items():
        if len(exs) == 1:
            new_expr += exs
            continue
        exs = [expr_simp(x) for x in exs]
        log_to_c_h.debug('warning: detected multi dst to same id')
        log_to_c_h.debug('\t'.join([str(x) for x in exs]))
        new_expr += exs
    out_mem = []

    # first, generate mem prefetch
    mem_k = src_mem.keys()
    mem_k.sort()
    for k in mem_k:
        str_src = patch_c_id(my_ir.arch, k).toC()
        str_dst = patch_c_id(my_ir.arch, src_mem[k]).toC()
        out.append('%s = %s;' % (str_dst, str_src))
    src_w_len = {}
    for k, v in src_mem.items():
        src_w_len[k] = v
    for e in new_expr:
        src, dst = e.src, e.dst
        # reload src using prefetch
        src = src.replace_expr(src_w_len)
        str_src = patch_c_id(my_ir.arch, src).toC()
        str_dst = patch_c_id(my_ir.arch, dst).toC()
        if isinstance(dst, ExprId):
            id_to_update.append(dst)
            str_dst = patch_c_new_id(my_ir.arch, dst)
            if dst in float_id_e:
                # dont mask float affectation
                out.append('%s = (%s);' % (str_dst, str_src))
            else:
                out.append('%s = (%s)&0x%X;' % (str_dst, str_src,
                                                my_size_mask[src.size]))
        elif isinstance(dst, ExprMem):
            fetch_mem = True
            str_dst = str_dst.replace('MEM_LOOKUP', 'MEM_WRITE')
            out_mem.append('%s, %s);' % (str_dst[:-1], str_src))

        if e.dst == my_ir.arch.pc[my_ir.attrib]:
            pc_is_dst = True
            out_pc += ["RETURN_PC;"]

    # if len(id_to_update) != len(set(id_to_update)):
    # raise ValueError('Not implemented: multi dst to same id!', str([str(x)
    # for x in exprs]))
    out += out_mem

    if gen_exception_code:
        if fetch_mem:
            e = set_pc(my_ir, l.offset & mask_int)
            s1 = "%s" % patch_c_id(my_ir.arch, e).toC()
            out.append(code_exception_fetch_mem_at_instr_noautomod % s1)
        if set_exception_flags:
            e = set_pc(my_ir, l.offset & mask_int)
            s1 = "%s" % patch_c_id(my_ir.arch, e).toC()
            out.append(code_exception_at_instr_noautomod % s1)

    for i in id_to_update:
        out.append('%s = %s;' %
                   (patch_c_id(my_ir.arch, i), patch_c_new_id(my_ir.arch, i)))

    post_instr = []
    # test stop exec ####
    if gen_exception_code:
        if set_exception_flags:
            if pc_is_dst:
                post_instr.append("if (vm_mngr->exception_flags) { " +
                    "/*pc = 0x%X; */RETURN_PC; }" % (l.offset))
            else:
                e = set_pc(my_ir, l.offset & mask_int)
                s1 = "%s" % patch_c_id(my_ir.arch, e).toC()
                e = set_pc(my_ir, (l.offset + l.l) & mask_int)
                s2 = "%s" % patch_c_id(my_ir.arch, e).toC()
                post_instr.append(
                    code_exception_post_instr_noautomod % (s1, s2))

        if fetch_mem:
            if l.additional_info.except_on_instr:
                offset = l.offset
            else:
                offset = l.offset + l.l

            e = set_pc(my_ir, offset & mask_int)
            s1 = "%s" % patch_c_id(my_ir.arch, e).toC()
            post_instr.append(
                code_exception_fetch_mem_post_instr_noautomod % (s1))

    # pc manip after all modifications
    return out, post_instr, post_instr + out_pc


def label2offset(e):
    if not isinstance(e, ExprId):
        return e
    if not isinstance(e.name, asmbloc.asm_label):
        return e
    return ExprInt_from(e, e.name.offset)


def expr2pyobj(arch, e):
    if isinstance(e, ExprId):
        if isinstance(e.name, asmbloc.asm_label):
            src_c = 'PyString_FromStringAndSize("%s", %d)' % (
                e.name.name, len(e.name.name))
        else:
            src_c = 'PyLong_FromUnsignedLongLong(%s)' % patch_c_id(arch, e)
    else:
        raise NotImplementedError('unknown type for e: %s' % type(e))
    return src_c


def ir2C(my_ir, irbloc, lbl_done,
    gen_exception_code=False, log_mn=False, log_regs=False):
    out = []
    # print "TRANS"
    # print irbloc
    out.append(["%s:" % irbloc.label.name])
    assert(len(irbloc.irs) == len(irbloc.lines))
    for l, exprs in zip(irbloc.lines, irbloc.irs):
        if l.offset not in lbl_done:
            e = set_pc(my_ir, l.offset & mask_int)
            s1 = "%s" % patch_c_id(my_ir.arch, e).toC()
            out.append([pre_instr_test_exception % (s1)])
            lbl_done.add(l.offset)

            if log_regs:
                out.append([r'dump_gpregs(vmcpu);'])

                if log_mn:
                    out.append(['printf("%.8X %s\\n");' % (l.offset, str(l))])
        # print l
        # gen pc update
        post_instr = ""
        c_code, post_instr, _ = Expr2C(my_ir, l, exprs, gen_exception_code)
        out.append(c_code + post_instr)
    return out


def irblocs2C(my_ir, resolvers, label, irblocs,
    gen_exception_code=False, log_mn=False, log_regs=False):
    out = []
    out.append("goto %s;" % label.name)
    bloc_labels = [x.label for x in irblocs]
    assert(label in bloc_labels)

    lbl_done = set([None])

    for irbloc in irblocs:
        # XXXX TEST
        if irbloc.label.offset is None:
            b_out = ir2C(my_ir, irbloc, lbl_done, gen_exception_code)
        else:
            b_out = ir2C(
                my_ir, irbloc, lbl_done, gen_exception_code, log_mn, log_regs)
        for exprs in b_out:
            for l in exprs:
                out.append(l)
        dst = irbloc.dst
        out.append("")
        if asmbloc.expr_is_label(dst):
            if dst.name in bloc_labels:
                out.append("goto %s;" % dst.name.name)
            else:
                resolver = resolvers.get_resolver(dst.name.offset)

                e = set_pc(my_ir, dst.name.offset & mask_int)
                #out.append("%s;" % patch_c_id(my_ir.arch, e).toC())
                out.append(resolver.ret())
        elif isinstance(dst, ExprSlice) and isinstance(dst.arg, ExprId):
            e = set_pc(my_ir, dst)
            #out.append("%s;" % patch_c_id(my_ir.arch, e).toC())

            e = patch_c_id(my_ir.arch, dst).toC()
            out.append("return PyLong_FromUnsignedLongLong(%s);" % e)

        elif isinstance(dst, ExprId):
            e = set_pc(my_ir, dst)
            #out.append("%s;" % patch_c_id(my_ir.arch, e).toC())

            e = patch_c_id(my_ir.arch, dst).toC()
            out.append("return PyLong_FromUnsignedLongLong(%s);" % e)
        elif isinstance(dst, ExprCond):
            dst_cond_c = patch_c_id(my_ir.arch, dst.cond).toC()
            out.append("if (%s)" % dst_cond_c)

            if dst.src1.name in bloc_labels:
                out.append("    goto %s;" % dst.src1.name.name)
            else:
                resolver = resolvers.get_resolver(dst.src1.name.offset)
                out.append(resolver.ret())

            out.append("else")

            if dst.src2.name in bloc_labels:
                out.append("    goto %s;" % dst.src2.name.name)
            else:
                resolver = resolvers.get_resolver(dst.src2.name.offset)
                out.append(resolver.ret())

        else:
            raise NotImplementedError('unknown type for dst: %s' % type(dst))
    #print '\n'.join(out)
    return out

