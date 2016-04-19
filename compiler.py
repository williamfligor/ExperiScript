import sys
from classproperty import classproperty

def log(*args):
    def fix(val):
        if isinstance(val, Register):
            return 'Register {}'.format(val.register)
        elif isinstance(val, JumpMarker):
            return 'JumpMarker {}'.format(val.register)
        elif isinstance(val, Function):
            return 'Function {}'.format(val.func_num)

        return val

    return map(fix, args)


class Instruction:
    def __init__(self, instruction, desc):
        self.instruction = instruction
        self.description = desc

        self.final_line = None

class LogInstruction:
    def __init__(self, desc):
        self.description = desc


class ControlCodes:

    VARIABLE = 0x00
    MOVE = 0x01
    CONTROL = 0x02
    MATH = 0x03
    MEMORY = 0x04

    class Variable:
        ONE = 251
        ZERO = 252

    class Move:
        MOVE = 0x00
        MOVE_I = 0x01

    class Math:
        ADD = 0x00
        ADD_I = 0x01

        SUB = 0x02
        SUB_I = 0x03

    class Memory:
        LOAD = 0x00
        STORE = 0x01

    class Control:
        IF_I = 0x00
        JUMP = 0x03
        JUMP_I = 0x05
        JUMP_NOT_TRUE = 0x06

    class Compare:
        EQUAL = 0x00


class Register:
    # Available registers
    _registers = [None] * 255

    def __init__(self, script, register=None):
        self.script = script

        if register is None:
            self.register = self.registers[self.start:].index(None) + self.start
        else:
            self.register = register

        self.registers[self.register] = self

    def set(self, value):
        instruction = LogInstruction('Set {} to {}'.format(*log(self, log(value))))
        self.script.add(self, self.script.zero, value)

    def free(self):
        self.registers[self.register] = None

    @classproperty
    def start(cls):
        raise Exception('Must be subclassed')

    @classproperty
    def registers(cls):
        return cls._registers


class VariableRegister(Register):
    @classproperty
    def start(cls):
        return 50


class GlobalRegister(Register):
    @classproperty
    def start(cls):
        return 100


class SystemRegister(Register):
    @classproperty
    def start(cls):
        return 125


class StaticRegister(GlobalRegister):
    def __init__(self, script, register, value=None):
        super(StaticRegister, self).__init__(script, register=register)

        if value is not None:
            super(StaticRegister, self).set(value)

    def set(value):
        raise Exception('Illegal set on zero register')

    @classproperty
    def start(cls):
        return 240


class StackPointer(GlobalRegister):
    def __init__(self, script, mem_start, force=None):
        super(StackPointer, self).__init__(script, register=force)

        if force is None:
            self.set(mem_start)

    def push(self, value):
        instruction = LogInstruction('Push {} to Stack {}'.format(*log(value, self)))
        self.script.bytecode.append(instruction)

        new_idx = self.script.VariableRegister()
        self.script.add(self, self, 1)

        self.store(value)

    def pop(self, variable):
        instruction = LogInstruction('Pop Stack {}'.format(*log(self)))
        self.script.bytecode.append(instruction)

        self.load(variable)
        self.script.sub(self, self, 1)

    def load(self, variable):
        instruction = Instruction([
            ControlCodes.MEMORY,
            ControlCodes.Memory.LOAD,
            self,
            variable
        ], 'Stack Load Mem {} Into {}'.format(*log(self, variable)))

        self.script.bytecode.append(instruction)

    def store(self, value):
        instruction = Instruction([
            ControlCodes.MEMORY,
            ControlCodes.Memory.STORE,
            self,
            value
        ], 'Stack Store {} Into Mem {}'.format(*log(value, self)))

        self.script.bytecode.append(instruction)

    @classproperty
    def start(cls):
        return 250


class JumpMarker:
    _jump_marker = 0

    def __init__(self):
        self.register = self.add_jump_marker()
        self.line = None

    @classmethod
    def add_jump_marker(cls):
        cls._jump_marker += 1
        return cls._jump_marker

class GenericScript:

    def __init__(self, parent_script=None):
        self.bytecode = []

        if parent_script is None:
            self.zero = StaticRegister(self, ControlCodes.Variable.ZERO)
            self.one = StaticRegister(self, ControlCodes.Variable.ONE)
            self.function_return_pointer = StackPointer(self, 150)
        else:
            self.zero = parent_script.zero
            self.one = parent_script.one
            self.function_return_pointer = StackPointer(self, 150, force=parent_script.function_return_pointer.register)

        def make_variable_register(*args, **kwargs):
            return VariableRegister(self, *args, **kwargs)
        self.VariableRegister = make_variable_register

        def make_stack_register(*args, **kwargs):
            return StaticRegister(self, *args, **kwargs)
        self.StaticRegister = make_stack_register

        def make_stack_pointer(*args, **kwargs):
            return StaticPointer(self, *args, **kwargs)
        self.StaticPointer = make_stack_pointer

        def make_system_register(*args, **kwargs):
            return SystemRegister(self, *args, **kwargs)
        self.SystemRegister = make_system_register

        def make_global_register(*args, **kwargs):
            return GlobalRegister(self, *args, **kwargs)
        self.GlobalRegister = make_global_register

    def move(self, ldir, rdir, lspeed, rspeed):
        register = False
        if isinstance(ldir, VariableRegister):
            register = True
        elif isinstance(rdir, VariableRegister):
            register = True
        elif isinstance(lspeed, VariableRegister):
            register = True
        elif isinstance(rspeed, VariableRegister):
            register = True

        if register:
            rldir = rdir
            rrdir = rdir
            rrspeed = rspeed
            rlspeed = lspeed

            if not isinstance(ldir, VariableRegister):
                rldir = self.SystemRegister()
                rldir.set(ldir)
            if not isinstance(rdir, VariableRegister):
                rrdir = self.SystemRegister()
                rrdir.set(rdir)
            if not isinstance(lspeed, VariableRegister):
                rlspeed = self.SystemRegister()
                rlspeed.set(lspeed)
            if not isinstance(rspeed, VariableRegister):
                rrspeed = self.SystemRegister()
                rrspeed.set(rspeed)

            instruction = Instruction([
                ControlCodes.MOVE,
                ControlCodes.Move.MOVE_I,
                rldir,
                rrdir,
                rlspeed,
                rrspeed
            ], 'Move with register values ld-{} rd-{} ls-{} rs-{}'.format(*log(rldir, rrdir, rlspeed, rrspeed))) 
            self.bytecode.append(instruction)

            rldir.free()
            rrdir.free()
            rlspeed.free()
            rrspeed.free()
        else:
            instruction = Instruction([
                ControlCodes.MOVE,
                ControlCodes.Move.MOVE,
                ldir,
                rdir,
                lspeed,
                rspeed
            ], 'Move with register values ld-{} rd-{} ls-{} rs-{}'.format(*log(ldir, rdir, lspeed, rspeed)))

            self.bytecode.append(instruction)

    def add_if(self, compare, var1, var2, function):
        self.bytecode.append(LogInstruction(None))
        self.bytecode.append(LogInstruction('If compare {} with {} and {} then jump to {}'.format(*log(compare, var1, var2, function))))

        result = self.SystemRegister()

        instruction = Instruction([
            ControlCodes.CONTROL,
            ControlCodes.Control.IF_I,
            compare,
            var1,
            var2,
            result
        ], 'Set register to 0 if false, 1 if true')
        self.bytecode.append(instruction)

        jump_marker = JumpMarker()

        instruction = Instruction([
            ControlCodes.CONTROL,
            ControlCodes.Control.JUMP_NOT_TRUE,
            result,
            jump_marker
        ], 'Jump if not true to {}'.format(*log(jump_marker)))
        self.bytecode.append(instruction)

        self.function_return_pointer.push(jump_marker)
        self.jump(function)

        self.bytecode.append(jump_marker)
        self.bytecode.append(LogInstruction('End If'))
        self.bytecode.append(LogInstruction(None))

    def call(self, function):
        jump_marker = JumpMarker()

        self.function_return_pointer.push(jump_marker)
        self.jump(function)

        self.bytecode.append(jump_marker)

    def jump(self, loc):
        if isinstance(loc, VariableRegister):
            instruction = Instruction([
                ControlCodes.CONTROL,
                ControlCodes.Control.JUMP,
                loc
            ], 'Jump to {}'.format(*log(loc)))
        elif isinstance(loc, Function):
            instruction = Instruction([
                ControlCodes.CONTROL,
                ControlCodes.Control.JUMP_I,
                loc.start_jump_marker
            ], 'Jumpi to {}'.format(*log(loc)))
        else:
            instruction = Instruction([
                ControlCodes.CONTROL,
                ControlCodes.Control.JUMP_I,
                loc
            ], 'Jumpi to {}'.format(*log(loc)))

        self.bytecode.append(instruction)

    def add(self, output, in1, in2):
        if isinstance(in2, VariableRegister):
            inst = Instruction([
                ControlCodes.MATH,
                ControlCodes.Math.ADD,
                output,
                in1,
                in2
            ], 'Add {} to {} output to {}'.format(*log(in1, in2, output)))
        else:
            inst = Instruction([
                ControlCodes.MATH,
                ControlCodes.Math.ADD_I,
                output,
                in1,
                in2
            ], 'Add {} to num {} output to {}'.format(*log(in1, in2, output)))

        self.bytecode.append(inst)

    def sub(self, output, in1, in2):
        if isinstance(in2, VariableRegister):
            inst = Instruction([
                ControlCodes.MATH,
                ControlCodes.Math.SUB,
                output,
                in1,
                in2
            ], 'Subtract {} to {} output to {}'.format(*log(in1, in2, output)))
        else:
            inst = Instruction([
                ControlCodes.MATH,
                ControlCodes.Math.SUB_I,
                output,
                in1,
                in2
            ], 'Subtract {} to num {} output to {}'.format(*log(in1, in2, output)))

        self.bytecode.append(inst)

    def build(self):
        final = []
        instruction_count = 0

        for instruction in self.bytecode:
            if isinstance(instruction, Instruction):
                final.append(instruction)
                instruction.final_line = instruction_count
                instruction_count += 1
            elif isinstance(instruction, JumpMarker):
                instruction.line = instruction_count
                final.append(LogInstruction('{}'.format(*log(instruction))))
            elif isinstance(instruction, LogInstruction):
                final.append(instruction)

        return final


class Function(GenericScript):
    _func_counter = 0

    def __init__(self, script):
        super(Function, self).__init__(parent_script=script)
        self.script = script
        self.start_jump_marker = JumpMarker()

        self.func_num = self.add_function_number()

        self.bytecode.append(LogInstruction('{} begin'.format(*log(self))))
        self.bytecode.append(self.start_jump_marker)

    def end(self):
        self.bytecode.append(LogInstruction('{} return'.format(*log(self))))

        pop_pointer = self.SystemRegister()
        self.function_return_pointer.pop(pop_pointer)
        self.jump(pop_pointer)

        pop_pointer.free()

        self.bytecode.append(LogInstruction('{} end'.format(*log(self))))

        self.script.functions.append(self)
        self.bytecode.append(LogInstruction(None))

    @classmethod
    def add_function_number(cls):
        cls._func_counter += 1
        return cls._func_counter


class Script(GenericScript):
    def __init__(self):
        super(Script, self).__init__()
        self.functions = []
        self.start_jump_marker = JumpMarker()

        self.jump(self.start_jump_marker)
        self.start_bytecode = self.bytecode
        self.bytecode = []

        self.bytecode.append(self.start_jump_marker)
        self.bytecode.append(LogInstruction('Main'))

    def build(self):
        functions = []

        for function in self.functions:
            functions += function.bytecode

        self.bytecode = self.start_bytecode + functions + self.bytecode

        functions = super(Script, self).build()

        return functions

    def link(self, instructions):
        run_again = False

        for instruction in instructions:
            if isinstance(instruction, Instruction):
                for arg_idx, arg in enumerate(instruction.instruction):
                    if isinstance(arg, Register):
                        arg = arg.register
                    elif isinstance(arg, JumpMarker):
                        arg = arg.line
                    elif isinstance(arg, Function):
                        arg = arg.instruction

                    instruction.instruction[arg_idx] = arg

                instruction.instruction = [len(instruction.instruction)] + instruction.instruction

        return instructions

    def string(self, instructions, show_log=False):
        final = ''

        last_line_num = 0
        for instruction in instructions:
            description = '# {} \n'.format(instruction.description) if instruction.description is not None else '\n'

            if isinstance(instruction, Instruction):
                last_line_num = instruction.final_line
                final += '{0:03d}: '.format(last_line_num) + str(instruction.instruction) + '    ' + description
            elif isinstance(instruction, LogInstruction) and show_log:
                final += 'LLL ' + description


        return final

    def construct(self, instructions):
        final = ''
        for instruction in instructions:
            if isinstance(instruction, Instruction):
                final += ''.join(list(map(lambda x: format(x, '08b'), instruction.instruction)))

        return final


script = Script()
var2 = script.GlobalRegister()

if1 = Function(script)
if1.add(var2, script.zero, 50)
if1.end()

if2 = Function(script)
if1.add(var2, script.zero, 40)
if2.end()

if3 = Function(script)
if1.add(var2, script.zero, 30)
if3.end()

script.call(if1)

var_eq = script.VariableRegister()
var_eq.set(0)

script.add_if(ControlCodes.Compare.EQUAL, var2, var_eq, if1)

var_eq.set(50)

script.add_if(ControlCodes.Compare.EQUAL, var2, var_eq, if2)

script.call(if2)
script.call(if3)


build = script.build()
build = script.link(build)

if len(sys.argv) > 1:
    print(script.string(build, show_log=True))
else:
    print(script.construct(build))
