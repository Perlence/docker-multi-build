import re

import attr


def parse(lines):
    return [Instruction(token.instruction, token.arguments)
            for token in tokenize(lines)]


def tokenize(lines):
    instructions = []
    lineno = -1
    insnre = re.compile(r'^\s*(\w+)\s+(.*)$')  # matched group is insn
    contre = re.compile(r'^.*\\\s*$')          # line continues?
    commentre = re.compile(r'^\s*#')           # line is a comment?
    in_continuation = False
    current_instruction = None
    for line in lines:
        lineno += 1
        if commentre.match(line):
            continue
        if not in_continuation:
            m = insnre.match(line)
            if not m:
                continue
            current_instruction = Token(instruction=m.groups()[0].upper(),
                                        startline=lineno,
                                        endline=lineno,
                                        content=line,
                                        arguments=_rstrip_backslash(m.groups()[1]))
        else:
            current_instruction.content += line
            current_instruction.endline = lineno
            if current_instruction.arguments:
                current_instruction.arguments += _rstrip_backslash(line)
            else:
                current_instruction.arguments = _rstrip_backslash(line.lstrip())

        in_continuation = contre.match(line)
        if not in_continuation and current_instruction is not None:
            instructions.append(current_instruction)

    return instructions


def _rstrip_backslash(l):
    l = l.rstrip()
    if l.endswith('\\'):
        return l[:-1]
    return l


@attr.s
class Token:
    instruction = attr.ib()
    startline = attr.ib()
    endline = attr.ib()
    content = attr.ib()
    arguments = attr.ib()


@attr.s
class Instruction:
    name = attr.ib()
    arguments = attr.ib()
