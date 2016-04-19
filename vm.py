import sys
from classproperty import classproperty
from compiler import ControlCodes

DEBUG = True
DEBUG_MEMORY = True

def log(*args, **kwargs):
    if DEBUG:
        print('--', *args, **kwargs)


class Instruction:
    def __init__(self, instruction):
        self.instruction = instruction


class Memory:
    def __init__(self):
        self.registers = [0] * 255

        self.registers[ControlCodes.Variable.ONE] = 1
        self.registers[ControlCodes.Variable.ZERO] = 0

    def set(self, register, value):
        self.registers[register] = value

    def get(self, register):
        return self.registers[register]

    def store(self, register, value):
        log('Memory.store register={} value={}'.format(register, value))
        self.registers[self.registers[register]] = value

    def load(self, register, dest):
        log('Memory.load register={} dest={}'.format(register, dest))
        val = self.registers[self.registers[register]]
        self.registers[dest] = val


class AMU:
    def __init__(self, memory):
        self.memory = memory

    def add(self, output, reg1, reg2):
        log('AMU.add output={} reg1={} reg2={}'.format(output, reg1, reg2))
        self.memory.set(output, self.memory.get(reg1) + self.memory.get(reg2))

    def add_immediate(self, output, reg1, reg2):
        log('AMU.addi output={} reg1={} reg2={}'.format(output, reg1, reg2))
        self.memory.set(output, self.memory.get(reg1) + reg2)

    def sub(self, output, reg1, reg2):
        log('AMU.sub output={} reg1={} reg2={}'.format(output, reg1, reg2))
        self.memory.set(output, self.memory.get(reg1) - self.memory.get(reg2))

    def sub_immediate(self, output, reg1, reg2):
        log('AMU.subi output={} reg1={} reg2={}'.format(output, reg1, reg2))
        self.memory.set(output, self.memory.get(reg1) - reg2)


class Robot:
    def move(self, ld, rd, ls, rs):
        log('Robot.move ld={} rd={} ls={} rs={}'.format(ld, rd, ls, rs))

    def move_immediate(self, ld, rd, ls, rs):
        log('Robot.movei ld={} rd={} ls={} rs={}'.format(ld, rd, ls, rs))

def skip_increment(func):
    func.skip_increment = True
    return func

class VM:
    def __init__(self, instructions):
        self.memory = Memory()
        self.amu = AMU(self.memory)
        self.robot = Robot()

        self.instructions = instructions

        self.current_idx = 0

        self.instruction_map = {
            ControlCodes.MOVE: {
                ControlCodes.Move.MOVE: self.robot.move,
                ControlCodes.Move.MOVE_I: self.robot.move_immediate,
            },
            ControlCodes.MATH: {
                ControlCodes.Math.ADD: self.amu.add,
                ControlCodes.Math.ADD_I: self.amu.add_immediate,
                ControlCodes.Math.SUB: self.amu.sub,
                ControlCodes.Math.SUB_I: self.amu.sub_immediate,
            },
            ControlCodes.CONTROL: {
                ControlCodes.Control.IF_I: self.if_immediate,
                ControlCodes.Control.JUMP: self.jump,
                ControlCodes.Control.JUMP_I: self.jump_immediate,
                ControlCodes.Control.JUMP_NOT_TRUE: self.jump_not_true,
            },
            ControlCodes.MEMORY: {
                ControlCodes.Memory.LOAD: self.memory.load,
                ControlCodes.Memory.STORE: self.memory.store
            }
        }

    def run(self):
        while self.current_idx < len(self.instructions):
            current_instruction = self.instructions[self.current_idx]
            log('VM.run {} {}'.format(self.current_idx, current_instruction))

            control = current_instruction[1]
            control_sub = current_instruction[2]
            instruction_args = current_instruction[3:]

            func = self.instruction_map[control][control_sub]
            func(*instruction_args)

            if not getattr(func, 'skip_increment', False):
                self.current_idx += 1

            if DEBUG_MEMORY:
                log('Memory {}'.format(self.memory.registers))

    def if_immediate(self, compare, var1, var2, result):
        log('VM.if_immediate compare={} var1={} var2={} result={}'.format(compare, var1, var2, result))
        var1 = self.memory.get(var1)
        var2 = self.memory.get(var2)

        if compare == ControlCodes.Compare.EQUAL:
            self.memory.set(result, var1 == var2)

    @skip_increment
    def jump(self, location):
        line = self.memory.get(location)
        log('VM.jump location={} mem_loc={}'.format(location, line))
        self.current_idx = line

    @skip_increment
    def jump_immediate(self, location):
        log('VM.jumpi location={}'.format(location))
        self.current_idx = location

    @skip_increment
    def jump_not_true(self, register, location):
        log('VM.jnt location={}'.format(location))
        if self.memory.get(register):
            self.current_idx = location

class StringParser:

    @staticmethod
    def byte(string):
        return int(string[:8], 2), string[8:]

    @staticmethod
    def parse(string):
        length, string = StringParser.byte(string)

        instruction = [length]
        while len(instruction) <= length:
            byte, string = StringParser.byte(string)
            instruction.append(byte)

        if len(string) > 0:
            return [instruction] + StringParser.parse(string)
        else:
            return [instruction]


print('Starting VM')

input_str = sys.stdin.read()
input_str = ''.join([i for i in input_str if i == '0' or i == '1'])
instructions = StringParser.parse(input_str)

vm = VM(instructions)
vm.run()
print(vm.memory.registers)