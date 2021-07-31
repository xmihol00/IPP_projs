
#=========================================================================================================
# File:        interpret.py
# Case:        VUT, FIT, IPP, project
# Date:        21. 3. 2021
# Author:      David Mihola
# Contac:      xmihol00@stud.fit.vutbr.cz
# Interpreted: Python 3.8.5
# Description: Interpret script of the XML representation of the IPPcode21 languge.
#==========================================================================================================

import sys
import os
import getopt
import xml.etree.ElementTree as ET
import re
from enum import Enum

class Error(Enum):
    ARG_ERR = 10
    IN_FILE_ERR = 11
    OUT_FILE_ERR = 12
    FORMAT_ERR = 31
    XML_STRUCTURE_ERR = 32
    SEMANTIC_ERR = 52
    OPERAND_TYPE_ERR = 53
    VAR_EXIST_ERR = 54
    FRAME_ERR = 55
    MISSING_VALUE_ERR = 56
    OPERAND_VALUE_ERR = 57
    STRING_ERR = 58

class Frames:
    def __init__(self):
        self.global_frame = {}      # dictonary of variables in global frame {name: [type, value], ...}
        self.local_frame = []       # list of local frame dictonaries
        self.temporary_frame = {}   # dictonary of variables in temporary frame {name: [type, value], ...}
        self.current_frame = {}     # dictonary of variables in current local frame {name: [type, value], ...}
        self.LF = 0                 # immersion of local frame
        self.TF = False             # activation of temporary frame

class Program:
    def __init__(self):
        self.labels = {}            # dicotnary of labels and corresponding IP values {label: value, ...}
        self.jumps = []             # list of jumps to be checked, if corresponding label exists
        self.data_stack = []        # list of values represented as [type, value]
        self.return_stack = []      # list of retrun IP values
        self.IP = 0                 # instruction pointer
        self.IC = 0                 # instruction counter

IN_BUFFER = None
FRAMES = Frames()
PROGRAM = Program()

# =========================================== functions ==============================================

def parse_prog_arguments():
    global IN_BUFFER
    try:
        opts, rest = getopt.getopt(sys.argv[1:], '', ["source=", "input=", "help"])
        if len(opts) > 1 and ("--help", '') in opts or len(rest):
            os._exit(Error.ARG_ERR.value)
    except:
        os._exit(Error.ARG_ERR.value)
    
    if ("--help", '') in opts:
        print(
"""Usage: interpret.py [option] ...
Options:
--help              Display help message.
--source=<file>     Uses the <file> as the source of the interpreted program.
--input=<file>      Uses the <file> as the input of the interpreted program.

Either source file or input file must be specified.""")
        os._exit(0)

    inpt = None
    source = None
    for tpl in opts:
        if tpl[0] == "--source":
            source = tpl[1]
        elif tpl[0] == "--input":
            inpt = tpl[1]
    
    if inpt == None and source == None:
        os._exit(Error.ARG_ERR.value)
    
    if source == None:
        source = sys.stdin

    if inpt != None:
        try:
            f = open(inpt, "r")
            IN_BUFFER = f.read().split("\n")
        except:
            os._exit(Error.IN_FILE_ERR.value)
        finally:
            f.close()
    
    return source

def parse_XML_input(xml_input):
    """
    Parses the XML representation of the source code. Terminates the execution with an error when the XML file 
    is not well-formated (31) or the XML structure does not meet the specification (32).

    Parameters
    ----------
    xml_input : string
        The name and path to a file containing the source code, can be also sys.stdin
    
    Return
    -------
    program : dict
        A dictonary cointaining all loaded instructions with integer keys representing their order
        {key: [OPCODE, arguments...]}
    """
    inst_counts = {"MOVE" : 2, "CREATEFRAME" : 0, "PUSHFRAME" : 0, "POPFRAME" : 0, "DEFVAR" : 1,
                   "CALL" : 1, "RETURN" : 0, "PUSHS" : 1, "POPS" : 1, "ADD" : 3, "SUB" : 3, "DIV": 3,
                   "MUL" : 3, "IDIV" : 3, "LT" : 3, "GT" : 3, "EQ" : 3, "AND" : 3, "OR" : 3,
                   "NOT" : 2, "INT2CHAR" : 2, "STRI2INT" : 3, "READ" : 2, "WRITE" : 1, "CONCAT" : 3,
                   "GETCHAR" : 3, "SETCHAR" : 3, "TYPE" : 2, "LABEL": 1, "JUMP" : 1, "JUMPIFEQ": 3,
                   "JUMPIFNEQ" : 3, "EXIT" : 1, "DPRINT": 1, "BREAK" : 0, "STRLEN" : 2, "ADDS": 0,
                   "SUBS": 0, "MULS": 0, "DIVS": 0, "IDIVS": 0, "GTS": 0, "LTS": 0, "EQS": 0,
                   "ANDS": 0, "ORS": 0, "NOTS": 0, "INT2CHARS": 0, "STRI2INTS": 0, "JUMPIFEQS": 1,
                   "JUMPIFNEQS": 1, "FLOAT2INTS": 0, "INT2FLOATS": 0, "CLEARS": 0, "INT2FLOAT": 2,
                   "FLOAT2INT": 2}
    program = []

    try:
        xml = ET.parse(xml_input)
    except:
        os._exit(Error.FORMAT_ERR.value)

    root = xml.getroot()
    if root.tag != "program":
        os._exit(Error.XML_STRUCTURE_ERR.value)
    
    att = 1

    if  "language" in root.attrib:
        if root.attrib["language"] != "IPPcode21":
            os._exit(Error.XML_STRUCTURE_ERR.value)
    else:
        os._exit(Error.XML_STRUCTURE_ERR.value)
    
    if "name" in root.attrib:
        att += 1
    if "description" in root.attrib:
        att += 1
    
    if att != len(root.attrib):
        os._exit(Error.XML_STRUCTURE_ERR.value)

    ints_max = 0
    for inst in root:
        if inst.tag != "instruction":
            os._exit(Error.XML_STRUCTURE_ERR.value)
        
        if "order" not in inst.attrib or "opcode" not in inst.attrib or len(inst.attrib) != 2:
            os._exit(Error.XML_STRUCTURE_ERR.value) # wrong instruction element

        inst.attrib["opcode"] = inst.attrib["opcode"].upper()
        if inst.attrib["order"] in program or inst.attrib["opcode"] not in inst_counts:
            os._exit(Error.XML_STRUCTURE_ERR.value) # duplicit instruction with the same order or not existing opcode
            
        try:
            order = int(inst.attrib["order"])
            if order <= 0:
                os._exit(Error.XML_STRUCTURE_ERR.value) # order not a natural number
            order -= 1
            while order >= ints_max:
                program.append(["NOP"])
                ints_max += 1
        except:
            os._exit(Error.XML_STRUCTURE_ERR.value) # order in not an inteeger format

        arg_num = inst_counts[inst.attrib["opcode"]]
        arg_arr = [inst.attrib["opcode"]]
        arg_count = 1
        inst[:] = sorted(inst, key= lambda arg: arg.tag) 
        for arg in inst:
            if arg_num == 0:
                os._exit(Error.XML_STRUCTURE_ERR.value) # more arguments than required by an instruction

            if re.match("^arg" + str(arg_count) + "$", arg.tag) == None:
                os._exit(Error.XML_STRUCTURE_ERR.value)

            arg_count += 1
            arg_num -= 1
            if len(arg.attrib) != 1 or "type" not in arg.attrib or re.match("^(int|bool|string|nil|label|type|var|float)$", arg.attrib["type"]) == None:
                os._exit(Error.XML_STRUCTURE_ERR.value) # invalid type of an instruction argument

            if inst.attrib["opcode"] == "LABEL":
                if arg.text in PROGRAM.labels:
                    os._exit(Error.SEMANTIC_ERR.value)
                PROGRAM.labels[arg.text] = order

            arg.text = check_arg_text(arg.text, arg.attrib["type"])
            arg_arr.append(arg.attrib["type"])
            arg_arr.append(arg.text)

        if arg_num != 0:
            os._exit(Error.XML_STRUCTURE_ERR.value) # invalid number of arguments

        if re.match("^(CALL|JUMPIFEQ|JUMPIFNEQ|JUMP)$", inst.attrib["opcode"]):
            PROGRAM.jumps.append(arg_arr[2])

        if program[order][0] != "NOP":
            os._exit(Error.XML_STRUCTURE_ERR.value)
        program[order] = arg_arr
   
    for jump in PROGRAM.jumps:
        if jump not in PROGRAM.labels:
            os._exit(Error.SEMANTIC_ERR.value)
    
    return program

def check_arg_text(text, typ):
    """
    Checks if an instruction argument is in the right format based on its type. Terminates the execution with an error (32) 
    if not.

    Parameters
    -----------
    text: string
        The text of the instruction argument.
    typ: {"var", "int", "nil", "bool", "label", "type", "string"}
        The type of the instruction argument.
    
    Return
    -------
    string
        The checked and formated text of the instruction argument.
    """

    regexes = {"var" : r"^(GF|LF|TF)@[A-Za-z_\-$&%*!?][A-Za-z_\-$&%*!?0-9]*$", 
               "label" : r"^[A-Za-z_\-$&%*!?][A-Za-z_\-$&%*!?0-9]*$", "type" : "^(int|string|bool|float)$"}

    if typ == "string":
        if text == None:
            return ""
        i = 0
        while i < len(text):
            if ord(text[i]) <= 32:
                os._exit(Error.XML_STRUCTURE_ERR.value) # wrong string format
            elif text[i] == '#':
                os._exit(Error.XML_STRUCTURE_ERR.value) # wrong string format
            elif text[i] == '\\':
                if re.match("^[0-9][0-9][0-9]$", text[i+1:i+4]) == None:
                    os._exit(Error.XML_STRUCTURE_ERR.value) # wrong string format
                text = text[:i] + chr(int(text[i+1:i+4])) + text[i+4:]
            i += 1
    elif typ == "int":
        try:
            text = int(text)
        except:
            os._exit(Error.XML_STRUCTURE_ERR.value)
    elif typ == "float":
        try:
            text = float.fromhex(text)
        except:
            os._exit(Error.XML_STRUCTURE_ERR.value)
    elif typ == "bool":
        if text == "true":
            text = True
        elif text == "false":
            text = False
        else:
            os._exit(Error.XML_STRUCTURE_ERR.value)
    elif typ == "nil":
        if text == "nil":
            text = None
        else:
            os._exit(Error.XML_STRUCTURE_ERR.value)
    else:
        if text == None:
            os._exit(Error.XML_STRUCTURE_ERR.value)
        if re.match(regexes[typ], text) == None:
            os._exit(Error.XML_STRUCTURE_ERR.value)
    
    return text

def assign_var_value(var, typ, value):
    """
    Assigns a variable with a given value. Terminates with an error if the variable does not exist (54) or 
    when the assigned frame does not exist (55).

    Parameters
    ----------
    var: string
        The variable name
    typ: {"int", "nil", "bool", "string"}
        The type of the assigned variable
    value: int, string, bool, None
        The value to be assigned
    """
    global FRAMES
    if var[:2] == "GF" and var in FRAMES.global_frame:
        FRAMES.global_frame[var] = [typ, value]
        return
    elif var[:2] == "LF" and var in FRAMES.current_frame:
        FRAMES.current_frame[var] = [typ, value]
        return
    elif var[:2] == "TF" and var in FRAMES.temporary_frame:
        FRAMES.temporary_frame[var] = [typ, value]
        return

    if (not FRAMES.TF and var[:2] == "TF") or (not FRAMES.LF and var[:2] == "LF"):
        os._exit(Error.FRAME_ERR.value)
    else:
        os._exit(Error.VAR_EXIST_ERR.value)

def get_var_type(var):
    """
    Retrieves the type of a variable. Terminates with an error if the variable does not exist (54) or 
    when the assigned frame does not exist (55).

    Parameters
    ----------
    var: string
        The name of a variable, which type is to be retrieved.
    
    Return
    -------
    {"int", "nil", "bool", "string"}
    """
    global FRAMES
    if var[:2] == "GF" and var in FRAMES.global_frame:
        return FRAMES.global_frame[var][0]
    elif var[:2] == "LF" and var in FRAMES.current_frame:
        return FRAMES.current_frame[var][0]
    elif var[:2] == "TF" and var in FRAMES.temporary_frame:
        return FRAMES.temporary_frame[var][0]
    
    if var[:2] == "GF" or (var[:2] == "LF" and FRAMES.LF) or (var[:2] == "TF" and FRAMES.TF):
        os._exit(Error.VAR_EXIST_ERR.value)
    else:
        os._exit(Error.FRAME_ERR.value)

def get_var_value(var):
    """
    Retrieves the value of a given variable. Terminates with an error if the variable does not exist (54) or 
    when the assigned frame does not exist (55).

    Parameters
    ----------
    var: string
        The name of a variable, which value is to be retrieved.
    
    Return
    -------
    [{"int", "nil", "bool", "string"}, <value based on the type>]
    """
    global FRAMES
    if var[:2] == "GF" and var in FRAMES.global_frame:
        if FRAMES.global_frame[var][0] == "":
            os._exit(Error.MISSING_VALUE_ERR.value)
        return FRAMES.global_frame[var]
    elif var[:2] == "LF" and var in FRAMES.current_frame:
        if FRAMES.current_frame[var][0] == "":
            os._exit(Error.MISSING_VALUE_ERR.value)
        return FRAMES.current_frame[var]
    elif var[:2] == "TF" and var in FRAMES.temporary_frame:
        if FRAMES.temporary_frame[var][0] == "":
            os._exit(Error.MISSING_VALUE_ERR.value)
        return FRAMES.temporary_frame[var]
    
    if var[:2] == "GF" or (var[:2] == "LF" and FRAMES.LF) or (var[:2] == "TF" and FRAMES.TF):
        os._exit(Error.VAR_EXIST_ERR.value)
    else:
        os._exit(Error.FRAME_ERR.value)

def get_values_math(operands):
    """
    Retrieves the values of operands of a given instruction. Terminates with an error (57) if the operands are not of a type 
    used in mathematical instructions or there is a type missmatch 

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    
    Return
    -------
        List of the operand values with the first element being their data type.
    """

    if operands[1] != "var":
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    if operands[3] == "var":
        value1 = get_var_value(operands[4])
    else:
        value1 = [operands[3], operands[4]]
    
    if operands[5] == "var":
        value2 = get_var_value(operands[6])
    else:
        value2 = [operands[5], operands[6]]
    
    if value1[0] != value2[0] or (value1[0] != "int" and value1[0] != "float"):
        os._exit(Error.OPERAND_TYPE_ERR.value)
       
    return [value1[0], value1[1], value2[1]]

def get_values_logic(operands, eq = False, typ = "var"):
    """
    Retrieves the values of operands of a given instruction. Terminates with an error (57) if there is a type missmatch.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    eq: bool
        True when the instruction uses equality comparison
    typ: string
        The type of the first operand.
    Return
    -------
        List of the operand values with the first element being their data type.
    """

    if operands[1] != typ:
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    if operands[3] == "var":
        value1 = get_var_value(operands[4])
    elif operands[3] == "int" or operands[3] == "float" or operands[3] == "string" or operands[3] == "bool":
        value1 = [operands[3], operands[4]]
    elif operands[3] == "nil" and eq:
        value1 = [operands[3], None]
    else:
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    if operands[5] == "var":
        value2 = get_var_value(operands[6])
    elif operands[5] == "int" or operands[5] == "float" or operands[5] == "string" or operands[5] == "bool":
        value2 = [operands[5], operands[6]]
    elif operands[5] == "nil" and eq:
        value2 = [operands[5], None]
    else:
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    if value1[0] != value2[0] and value1[0] != "nil" and value2[0] != "nil":
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    return [value1[1], value2[1]]

def get_values_bool(operands):
    """
    Retrieves the values of operands of a given instruction. Terminates with an error (57) if any of the operands is not
    of a boolean type.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    Return
    -------
        List of boolean values.
    """

    if operands[1] != "var":
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    if operands[3] == "var":
        value1 = get_var_value(operands[4])
    else:
        value1 = [operands[3], operands[4]]
    
    if operands[5] == "var":
        value2 = get_var_value(operands[6])
    else:
        value2 = [operands[5], operands[6]]
    
    if value1[0] != value2[0] or value1[0] != "bool":
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    return [value1[1], value2[1]]

def get_stack_values_math():
    global PROGRAM
    if len(PROGRAM.data_stack) < 2:
        os._exit(Error.MISSING_VALUE_ERR.value)
    
    val2 = PROGRAM.data_stack.pop()
    val1 = PROGRAM.data_stack.pop()
    if val1[0] != val2[0] or (val1[0] != "int" and val1[0] != "float"):
        os._exit(Error.OPERAND_TYPE_ERR.value)

    return [val1[0], val1[1], val2[1]]

def get_satack_values_logic(eq = False):
    global PROGRAM
    if len(PROGRAM.data_stack) < 2:
        os._exit(Error.MISSING_VALUE_ERR.value)
    
    val2 = PROGRAM.data_stack.pop()
    val1 = PROGRAM.data_stack.pop()
    if eq:
        if val1[0] != val2[0] and val1[0] != "nil" and val2[0] != "nil":
            os._exit(Error.OPERAND_TYPE_ERR.value)
    else:
        if val1[0] != val2[0] or val1[0] == "nil":
            os._exit(Error.OPERAND_TYPE_ERR.value)
    
    return [val1[1], val2[1]]

def get_satack_values_bool():
    global PROGRAM
    if len(PROGRAM.data_stack) < 2:
        os._exit(Error.MISSING_VALUE_ERR.value)
    
    val2 = PROGRAM.data_stack.pop()
    val1 = PROGRAM.data_stack.pop()
    if val1[0] != "bool" or val2[0] != "bool":
        os._exit(Error.OPERAND_TYPE_ERR.value)

    return [val1[1], val2[1]]

def CREATEFRAME(operands):
    """
    Interprets the CREATEFRAME instruction.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    global FRAMES
    FRAMES.temporary_frame.clear()
    FRAMES.TF = True

def PUSHFRAME(operands):
    """
    Interprets the PUSHFRAME instruction. Terminates with an error (31), when there is no frame to be pushed.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    global FRAMES
    if not FRAMES.TF:
        os._exit(Error.FRAME_ERR.value)

    copy_dict = {}
    for key, value in FRAMES.current_frame.items():
        copy_dict[key] = value

    FRAMES.local_frame.append(copy_dict)
    FRAMES.current_frame.clear()

    for key, value in FRAMES.temporary_frame.items():
        key = 'L' + key[1:]
        FRAMES.current_frame[key] = value
    
    FRAMES.temporary_frame.clear()
    FRAMES.TF = False
    FRAMES.LF += 1

def POPFRAME(operands):
    """
    Interprets the POPFRAME instruction. Terminates with an error (55), when there is no frame to be popped.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    global FRAMES
    if not FRAMES.LF:
        os._exit(Error.FRAME_ERR.value)
    
    FRAMES.temporary_frame.clear()
    FRAMES.TF = True
    for key, value in FRAMES.current_frame.items():
        key = 'T' + key[1:]
        FRAMES.temporary_frame[key] = value
    
    FRAMES.current_frame.clear()
    FRAMES.LF -= 1
    FRAMES.current_frame.update(FRAMES.local_frame.pop())

def PUSHS(operands):
    """
    Interprets the PUSHS instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """

    if operands[1] == "var":
        value = get_var_value(operands[2])
    else:
        value = [operands[1], operands[2]]

    PROGRAM.data_stack.append(value)

def POPS(operands):
    """
    Interprets the POPS instructiion. Terminates with an error when there is no value on the stack (56) or when
    the operand is not a variable (53)

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """

    if operands[1] != "var":
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    try:
        value = PROGRAM.data_stack.pop()
    except:
        os._exit(Error.MISSING_VALUE_ERR.value)
    
    assign_var_value(operands[2], value[0], value[1])

def LABEL(operands):
    """
    Dummy function to "interpret" the label instruction, which is interpreted at load time.
    """

def CALL(operands):
    """
    Interprets the CALL instructiion. Terminates with an error when the operand type is not a label (53).

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    global PROGRAM
    if operands[1] != "label":
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    PROGRAM.return_stack.append(PROGRAM.IP)
    PROGRAM.IP = PROGRAM.labels[operands[2]]

def RETURN(operands):
    """
    Interprets the RETURN instructiion. Terminates with an error when there is no label to return to - i.e. CALL insturction 
    did not precede (56).

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    global PROGRAM

    try:
        PROGRAM.IP = PROGRAM.return_stack.pop()
    except:
        os._exit(Error.MISSING_VALUE_ERR.value)

def JUMP(operands):
    """
    Interprets the JUMP instructiion. Terminates with an error when the operand type is not a label (53).

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    global PROGRAM

    if operands[1] != "label":
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    PROGRAM.IP = PROGRAM.labels[operands[2]]

def JUMPIFEQ(operands):
    """
    Interprets the JUMPIFEQ instructiion. Terminates with an error when the first operand type is not a label (53).

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """

    if operands[1] != "label":
        os._exit(Error.OPERAND_TYPE_ERR.value)
    global PROGRAM

    values = get_values_logic(operands, True, "label")

    if values[0] == values[1]:
        PROGRAM.IP = PROGRAM.labels[operands[2]]


def JUMPIFNEQ(operands):
    """
    Interprets the JUMPIFNEQ instructiion. Terminates with an error when the first operand type is not a label (53).

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    global PROGRAM

    if operands[1] != "label":
        os._exit(Error.OPERAND_TYPE_ERR.value)

    values = get_values_logic(operands, True, "label")
    if values[0] != values[1]:
        PROGRAM.IP = PROGRAM.labels[operands[2]]

def DEFVAR(operands):
    """
    Interprets the DEFVAR instructiion. Terminates with an error when the operand is not a variable, when
    the the variable is already defined (52) or when the assigned frame does not exist (55).

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    global FRAMES
    if operands[1] != "var":
        os._exit(Error.SEMANTIC_ERR.value)

    var = operands[2]
    if var[:2] == "GF":
        if var in FRAMES.global_frame:
            os._exit(Error.SEMANTIC_ERR.value)
        FRAMES.global_frame[var] = ["", ""]
        return
    elif var[:2] == "LF" and FRAMES.LF:
        if var in FRAMES.current_frame:
            os._exit(Error.SEMANTIC_ERR.value)
        FRAMES.current_frame[var] = ["", ""]
        return
    elif var[:2] == "TF" and FRAMES.TF:
        if var in FRAMES.temporary_frame:
            os._exit(Error.SEMANTIC_ERR.value)
        FRAMES.temporary_frame[var] = ["", ""]
        return

    os._exit(Error.FRAME_ERR.value)

def MOVE(operands):
    """
    Interprets the MOVE instructiion. Terminates with an error on operands data type missmatch (53).

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """

    if operands[1] != "var" or operands[3] == "label" or operands[3] == "type":
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    if operands[3] == "var":
        value = get_var_value(operands[4])
        assign_var_value(operands[2], value[0], value[1])
    else:
        assign_var_value(operands[2], operands[3], operands[4])
    
def ADD(operands):
    """
    Interprets the ADD instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """

    values = get_values_math(operands)
    assign_var_value(operands[2], values[0], values[1] + values[2])

def SUB(operands):
    """
    Interprets the SUB instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """

    values = get_values_math(operands)
    assign_var_value(operands[2], values[0], values[1] - values[2])

def MUL(operands):
    """
    Interprets the MUL instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """

    values = get_values_math(operands)
    assign_var_value(operands[2], values[0], values[1] * values[2])

def IDIV(operands):
    """
    Interprets the IDIV instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """

    values = get_values_math(operands)

    if values[0] != "int":
        os._exit(Error.OPERAND_TYPE_ERR.value)

    if int(values[2]) == 0:
        os._exit(Error.OPERAND_VALUE_ERR.value)

    assign_var_value(operands[2], values[0], int(values[1] / values[2])) #TODO

def DIV(operands):
    """
    Interprets the DIV instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """

    values = get_values_math(operands)

    if values[0] != "float":
        os._exit(Error.OPERAND_TYPE_ERR.value)

    if values[2] == 0.0:
        os._exit(Error.OPERAND_VALUE_ERR.value)

    assign_var_value(operands[2], values[0], values[1] / values[2]) 

def WRITE(operands):
    """
    Interprets the WRITE instructiion. Terminates with an error when there is an operand type missmatch (53).

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """

    if operands[1] == "label" or operands[1] == "type":
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    if operands[1] == "var":
        value = get_var_value(operands[2])
        if value[0] == "bool":
            if value[1]:
                print("true", end="")
            else:
                print("false", end="")
        elif value[0] == "float":
            print(float.hex(value[1]), end='')
        elif value[0] != "nil":
            print(value[1], end="")
    elif operands[1] == "bool":
        if operands[2] == "false":
            print("false", end="")
        elif operands[2]:
            print("true", end="")
        else:
            print("false", end="")
    elif operands[1] == "float":
        print(float.hex(operands[2]), end="")
    elif operands[1] != "nil":
        print(operands[2], end="")

def READ(operands):
    """
    Interprets the READ instructiion. Terminates with an error when there is an operand type missmatch (53).

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """

    if operands[1] != "var" or operands[3] != "type":
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    typ = operands[4]
    
    try:
        if IN_BUFFER == None:
            line = input()
        else:
            line = IN_BUFFER.pop(0)
    except:
        if typ == "bool":
            line = "false"
        else:      
            typ = "nil"
            line = None
    
    try:
        if typ == "int":
            line = int(line)
        elif typ == "bool":
            line = line.lower() == "true"
        elif typ == "float":
            line = float.fromhex(line)
    except:
        line = None
        typ = "nil"
    
    assign_var_value(operands[2], typ, line)

def CONCAT(operands):
    """
    Interprets the CONCAT instructiion. Terminates with an error when there is an operand type missmatch (53).

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """

    if operands[1] != "var":
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    if operands[3] == "var":
        value1 = get_var_value(operands[4])
    else:
        value1 = [operands[3], operands[4]]
    
    if operands[5] == "var":
        value2 = get_var_value(operands[6])
    else:
        value2 = [operands[5], operands[6]]
    
    if value1[0] != value2[0] or value1[0] != "string":
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    assign_var_value(operands[2], "string", value1[1] + value2[1])

def LT(operands):
    """
    Interprets the LT instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """

    values = get_values_logic(operands)
    assign_var_value(operands[2], "bool", values[0] < values[1])

def GT(operands):
    """
    Interprets the GT instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """

    values = get_values_logic(operands)
    assign_var_value(operands[2], "bool", values[0] > values[1])

def EQ(operands):
    """
    Interprets the EQ instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    values = get_values_logic(operands, True)
    assign_var_value(operands[2], "bool", values[0] == values[1])

def AND(operands):
    """
    Interprets the AND instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """

    values = get_values_bool(operands)
    assign_var_value(operands[2], "bool", values[0] and values[1])

def OR(operands):
    """
    Interprets the OR instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """

    values = get_values_bool(operands)
    assign_var_value(operands[2], "bool", values[0] or values[1])

def STRLEN(operands):
    """
    Interprets the STRLEN instructiion. Terminates with an error when there is an operand type missmatch (53).

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """

    if operands[1] != "var":
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    if operands[3] == "var":
        value = get_var_value(operands[4])
        if value[0] != "string":
            os._exit(Error.OPERAND_TYPE_ERR.value)
        string = value[1]
    elif operands[3] == "string":
        string = operands[4]
    else:
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    assign_var_value(operands[2], "int", len(string))

def NOT(operands):
    """
    Interprets the NOT instructiion. Terminates with an error when there is an operand type missmatch (53).

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """

    if operands[1] != "var":
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    if operands[3] == "var":
        value = get_var_value(operands[4])
        if value[0] != "bool":
            os._exit(Error.OPERAND_TYPE_ERR.value)
        value = value[1]
    elif operands[3] == "bool":
        value = operands[4]
    else:
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    assign_var_value(operands[2], "bool", not value)

def INT2CHAR(operands):
    """
    Interprets the INT2CHAR instructiion. Terminates with an error when there is an operand type missmatch (53) or when
    the integer value cannot be converted to a character (57).

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """

    if operands[1] != "var":
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    if operands[3] == "var":
        value = get_var_value(operands[4])
        if value[0] != "int":
            os._exit(Error.OPERAND_TYPE_ERR.value)
        value = value[1]
    elif operands[3] == "int":
        value = int(operands[4])
    else:
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    try:
        assign_var_value(operands[2], "string", chr(value))
    except:
        os._exit(Error.STRING_ERR.value)

def STRI2INT(operands):
    """
    Interprets the STR2INT instructiion. Terminates with an error when there is an operand type missmatch (53) or when
    the string index is out of bounds (58).

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """

    if operands[1] != "var":
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    if operands[3] == "var":
        value = get_var_value(operands[4])
        if value[0] != "string":
            os._exit(Error.OPERAND_TYPE_ERR.value)
        string = value[1]
    elif operands[3] == "string":
        string = operands[4]
    else:
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    if operands[5] == "var":
        value = get_var_value(operands[6])
        if value[0] != "int":
            os._exit(Error.OPERAND_TYPE_ERR.value)
        index = value[1]
    elif operands[5] == "int":
        index = int(operands[6])
    else:
        os._exit(Error.OPERAND_TYPE_ERR.value)

    if index < 0:
        os._exit(Error.STRING_ERR.value)    
    try:
        assign_var_value(operands[2], "int", ord(string[index]))
    except:
        os._exit(Error.STRING_ERR.value)

def GETCHAR(operands):
    """
    Interprets the GETCHAR instructiion. Terminates with an error when there is an operand type missmatch (53) or when
    the string index is out of bounds (58).

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """

    if operands[1] != "var":
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    if operands[3] == "var":
        value = get_var_value(operands[4])
        if value[0] != "string":
            os._exit(Error.OPERAND_TYPE_ERR.value)
        string = value[1]
    elif operands[3] == "string":
        string = operands[4]
    else:
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    if operands[5] == "var":
        value = get_var_value(operands[6])
        if value[0] != "int":
            os._exit(Error.OPERAND_TYPE_ERR.value)
        index = value[1]
    elif operands[5] == "int":
        index = int(operands[6])
    else:
        os._exit(Error.OPERAND_TYPE_ERR.value)

    if index < 0 or index >= len(string):
        os._exit(Error.STRING_ERR.value) 
    try:
        assign_var_value(operands[2], "string", string[index])
    except:
        os._exit(Error.STRING_ERR.value)

def SETCHAR(operands):
    """
    Interprets the SETCHAR instructiion. Terminates with an error when there is an operand type missmatch (53) or when
    the string index is out of bounds (58).

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """

    if operands[1] != "var":
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    var = get_var_value(operands[2])
    if var[0] != "string":
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    string = var[1]
    
    if operands[3] == "var":
        value = get_var_value(operands[4])
        if value[0] != "int":
            os._exit(Error.OPERAND_TYPE_ERR.value)
        index = value[1]
    elif operands[3] == "int":
        index = int(operands[4])
    else:
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    if operands[5] == "var":
        value = get_var_value(operands[6])
        if value[0] != "string":
            os._exit(Error.OPERAND_TYPE_ERR.value)
        replacement = value[1]
    elif operands[5] == "string":
        replacement = operands[6]
    else:
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    if len(string) == 0 or index < 0 or len(string) <= index:
        os._exit(Error.STRING_ERR.value)
    try:
        string = string[0:index] + replacement[0] + string[index + 1:]
        assign_var_value(operands[2], "string", string)
    except:
        os._exit(Error.STRING_ERR.value)
    
def TYPE(operands):
    """
    Interprets the TYPE instructiion. Terminates with an error when there is an operand type missmatch (53).

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """

    if operands[1] != "var":
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    if operands[3] == "var":
        typ = get_var_type(operands[4])
    elif operands[3] == "int" or operands[3] == "string" or operands[3] == "bool" or operands[3] == "nil":
        typ = operands[3]
    
    assign_var_value(operands[2], "string", typ)

def EXIT(operands):
    """
    Interprets the EXIT instructiion. Terminates with an error when there is an operand type missmatch (53) or when
    the exit value is out of bounds.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    if operands[1] == "var":
        value = get_var_value(operands[2])
        if value[0] != "int":
            os._exit(Error.OPERAND_TYPE_ERR.value)
        value = value[1]
    elif operands[1] == "int":
        value = int(operands[2])
    else:
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    if value >= 0 and value < 50:
        exit(value)
    else:
        os._exit(Error.OPERAND_VALUE_ERR.value)

def DPRINT(operands):
    if operands[1] == "var":
        value = get_var_value(operands[2])
    else:
        value = [operands[1], operands[2]]
    
    if value[0] == "bool":
        if value[1] == "true":
            print("true", file=sys.stderr)
        elif value[1] == "false":
            print("false", file=sys.stderr)
        elif value[1]:
            print("true", file=sys.stderr)
        else:
            print("false", file=sys.stderr)
    elif value[0] == "int" or value[0] == "string":
        print(value[1], file=sys.stderr)
    

def BREAK(operands):
    global PROGRAM, FRAMES
    print("Number of executed isntructions including this one:", PROGRAM.IC, file=sys.stderr)
    print(file=sys.stderr)

    print("Values pushed on the stack from the top to bottom:", file=sys.stderr)
    for value in reversed(PROGRAM.data_stack):
        print("type: ", value[0], ", value: ", value[1], sep='', file=sys.stderr)
    print(file=sys.stderr)

    if len(FRAMES.global_frame) > 0:
        print("Variables on the global frame:", file=sys.stderr)
        for key in FRAMES.global_frame:
            print("name: ", key, ", type: ", FRAMES.global_frame[key][0], ", value: ", FRAMES.global_frame[key][1], sep='', file=sys.stderr)
        
        print(file=sys.stderr)
    else:
        print("There are no variables on the global frame.", file=sys.stderr)

    if FRAMES.LF:
        print("Variables on the local frame:", file=sys.stderr)
        i = 1
        print("Local frame immersion level 1:", file=sys.stderr)
        for key in FRAMES.current_frame:
            print("name: ", key, ", type: ", FRAMES.current_frame[key][0], ", value: ", FRAMES.current_frame[key][1], sep='', file=sys.stderr)
        
        for frame in reversed(FRAMES.local_frame):
            i += 1
            if len(frame):
                print("Local frame immersion level ", i, ":", sep="", file=sys.stderr)
                for key in frame:
                    print("name: ", key, ", type: ", frame[key][0], ", value: ", frame[key][1], sep='', file=sys.stderr)
        
        print(file=sys.stderr)
    else:
        print("There are no variables on the local frame.", file=sys.stderr)
    
    if FRAMES.TF:
        print("Variables on the temporary frame:", file=sys.stderr)
        for key in FRAMES.temporary_frame:
            print("name: ", key, ", type: ", FRAMES.temporary_frame[key][0], ", value: ", FRAMES.temporary_frame[key][1], sep='', file=sys.stderr)
    else:
        print("There are no variables on the temporary frame.", file=sys.stderr)

def INT2FLOAT(operands):
    if operands[1] != "var":
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    if operands[3] == "var":
        value = get_var_value(operands[4])
        if value[0] != "int":
            os._exit(Error.OPERAND_TYPE_ERR.value)
        value = value[1]
    elif operands[3] == "int":
        value = int(operands[4])
    else:
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    assign_var_value(operands[2], "float", float(value))

def FLOAT2INT(operands):
    if operands[1] != "var":
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    if operands[3] == "var":
        value = get_var_value(operands[4])
        if value[0] != "float":
            os._exit(Error.OPERAND_TYPE_ERR.value)
        value = value[1]
    elif operands[3] == "float":
        value = float(operands[4])
    else:
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    assign_var_value(operands[2], "int", int(value))

def CLEARS(operands):
    """
    Interprets the CLEARS instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    global PROGRAM
    PROGRAM.data_stack.clear()

def ADDS(operands):
    """
    Interprets the ADDS instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    global PROGRAM
    vals = get_stack_values_math()

    PROGRAM.data_stack.append([vals[0], vals[1] + vals[2]])

def SUBS(operands):
    """
    Interprets the SUBS instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    global PROGRAM
    vals = get_stack_values_math()
    
    PROGRAM.data_stack.append([vals[0], vals[1] - vals[2]])

def MULS(operands):
    """
    Interprets the MULS instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    global PROGRAM
    vals = get_stack_values_math()
    
    PROGRAM.data_stack.append([vals[0], vals[1] * vals[2]])

def IDIVS(operands):
    """
    Interprets the IDIVS instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    global PROGRAM
    vals = get_stack_values_math()
    
    if vals[0] != "int":
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    if vals[2] == 0:
        os._exit(Error.OPERAND_VALUE_ERR.value)

    PROGRAM.data_stack.append([vals[0], int(vals[1] / vals[2])])

def DIVS(operands):
    """
    Interprets the DIVS instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    global PROGRAM
    vals = get_stack_values_math()
    
    if vals[0] != "float":
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    if vals[2] == 0.0:
        os._exit(Error.OPERAND_VALUE_ERR.value)

    PROGRAM.data_stack.append([vals[0], vals[1] / vals[2]])

def LTS(operands):
    """
    Interprets the LTS instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    global PROGRAM
    vals = get_satack_values_logic()
    
    PROGRAM.data_stack.append(["bool", vals[0] < vals[1]])

def GTS(operands):
    """
    Interprets the GTS instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    global PROGRAM
    vals = get_satack_values_logic()
    
    PROGRAM.data_stack.append(["bool", vals[0] > vals[1]])

def EQS(operands):
    """
    Interprets the EQS instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    global PROGRAM
    vals = get_satack_values_logic(True)
    
    PROGRAM.data_stack.append(["bool", vals[0] == vals[1]])

def ANDS(operands):
    """
    Interprets the ANDS instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    global PROGRAM
    vals = get_satack_values_bool()
    
    PROGRAM.data_stack.append(["bool", vals[0] and vals[1]])

def ORS(operands):
    """
    Interprets the ORS instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    global PROGRAM
    vals = get_satack_values_bool()
    
    PROGRAM.data_stack.append(["bool", vals[0] or vals[1]])

def NOTS(operands):
    """
    Interprets the NOTS instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    global PROGRAM
    if len(PROGRAM.data_stack) == 0:
        os._exit(Error.MISSING_VALUE_ERR.value)

    if PROGRAM.data_stack[-1][0] != "bool":
        os._exit(Error.OPERAND_TYPE_ERR.value)

    PROGRAM.data_stack[-1][1] = not PROGRAM.data_stack[-1][1]

def STRI2INTS(operands):
    """
    Interprets the STRI2INTS instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    global PROGRAM
    if len(PROGRAM.data_stack) < 2:
        os._exit(Error.MISSING_VALUE_ERR.value)

    val2 = PROGRAM.data_stack.pop()
    val1 = PROGRAM.data_stack.pop()

    if val1[0] != "string" or val2[0] != "int":
        os._exit(Error.OPERAND_TYPE_ERR.value)
    
    try:
        PROGRAM.data_stack.append(["int", ord(val1[1][val2[1]])])
    except:
        os._exit(Error.STRING_ERR.value)
    

def INT2CHARS(operands):
    """
    Interprets the INT2CHARS instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    global PROGRAM
    if len(PROGRAM.data_stack) == 0:
        os._exit(Error.MISSING_VALUE_ERR.value)

    if PROGRAM.data_stack[-1][0] != "int":
        os._exit(Error.OPERAND_TYPE_ERR.value)

    PROGRAM.data_stack[-1][0] = "string"
    try:
        PROGRAM.data_stack[-1][1] = chr(PROGRAM.data_stack[-1][1])
    except:
        os._exit(Error.STRING_ERR.value)

def JUMPIFEQS(operands):
    """
    Interprets the JUMPIFEQS instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    global PROGRAM
    if operands[1] != "label":
        os._exit(Error.OPERAND_TYPE_ERR.value)

    values = get_satack_values_logic(True)
    if values[0] == values[1]:
        PROGRAM.IP = PROGRAM.labels[operands[2]]

def JUMPIFNEQS(operands):
    """
    Interprets the JUMPIFNEQS instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    global PROGRAM
    if operands[1] != "label":
        os._exit(Error.OPERAND_TYPE_ERR.value)

    values = get_satack_values_logic(True)
    if values[0] != values[1]:
        PROGRAM.IP = PROGRAM.labels[operands[2]]

def INT2FLOATS(operands):
    """
    Interprets the INT2FLOATS instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    global PROGRAM
    if len(PROGRAM.data_stack) == 0:
        os._exit(Error.MISSING_VALUE_ERR.value)

    if PROGRAM.data_stack[-1][0] != "int":
        os._exit(Error.OPERAND_TYPE_ERR.value)

    PROGRAM.data_stack[-1][0] = "float"
    PROGRAM.data_stack[-1][1] = float(PROGRAM.data_stack[-1][1])

def FLOAT2INTS(operands):
    """
    Interprets the FLOATS2INT instructiion.

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    global PROGRAM
    if len(PROGRAM.data_stack) == 0:
        os._exit(Error.MISSING_VALUE_ERR.value)

    if PROGRAM.data_stack[-1][0] != "float":
        os._exit(Error.OPERAND_TYPE_ERR.value)

    PROGRAM.data_stack[-1][0] = "int"
    PROGRAM.data_stack[-1][1] = int(PROGRAM.data_stack[-1][1])

def NOP(operands):
    """
    Interprets missing intruction

    Parameters
    ----------
    operands: list
        A list of operands in a specific format.
    """
    pass

# ========================================= end functions ============================================

# instruction mapping
functions = {"MOVE" : MOVE, "DEFVAR" : DEFVAR, "ADD" : ADD, "SUB": SUB, "MUL": MUL, "IDIV": IDIV, "WRITE" : WRITE, "READ": READ,
             "CONCAT": CONCAT, "LT" : LT, "GT": GT, "EQ": EQ, "AND": AND, "OR": OR, "INT2CHAR": INT2CHAR, "STRI2INT": STRI2INT,
             "NOT": NOT, "GETCHAR": GETCHAR, "SETCHAR": SETCHAR, "TYPE": TYPE, "CALL": CALL, "RETURN": RETURN, "JUMP": JUMP, 
             "LABEL": LABEL, "JUMPIFEQ": JUMPIFEQ, "JUMPIFNEQ": JUMPIFNEQ, "CREATEFRAME": CREATEFRAME, "PUSHFRAME": PUSHFRAME, 
             "POPFRAME": POPFRAME, "EXIT": EXIT, "PUSHS": PUSHS, "POPS": POPS, "STRLEN": STRLEN, "BREAK": BREAK, 
             "DPRINT": DPRINT, "NOP": NOP, "ADDS": ADDS, "SUBS": SUBS, "MULS": MULS, "IDIVS": IDIVS, "ANDS": ANDS, "ORS": ORS,
             "NOTS": NOTS, "JUMPIFEQS": JUMPIFEQS, "JUMPIFNEQS": JUMPIFNEQS, "STRI2INTS": STRI2INTS, "INT2CHARS": INT2CHARS,
             "CLEARS": CLEARS, "DIV": DIV, "DIVS": DIVS, "FLOAT2INTS": FLOAT2INTS, "INT2FLOATS": INT2FLOATS, "LTS": LTS,
             "GTS": GTS, "EQS": EQS, "FLOAT2INT": FLOAT2INT, "INT2FLOAT": INT2FLOAT}

xml_input = parse_prog_arguments()

instructions = parse_XML_input(xml_input)

while PROGRAM.IP < len(instructions):
    PROGRAM.IC += 1
    functions[instructions[PROGRAM.IP][0]](instructions[PROGRAM.IP])
    PROGRAM.IP += 1
