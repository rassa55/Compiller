import ctypes
import sys
import time
from interpritator import compile_llvm
import llvmlite.binding as llvm
from codegeneration import Block, GenerateCode, prTr
from parser import build_tree, getTable
from lexer import Lexer
import traceback

def optimize_double_assignment(llvm_ir):
    optimized_ir = ""

    lines = llvm_ir.split('\n')
    num_lines = len(lines)
    i = 0

    while i < num_lines:
        line = lines[i]

        # Проверяем, является ли текущая строка присвоением переменной
        if line.startswith('%') and '=' in line:
            parts = line.split('=')
            lhs = parts[0].strip()
            rhs = parts[1].strip()

            # Проверяем, является ли rhs двойным присвоением
            if '%' in rhs and '=' in rhs:
                nested_parts = rhs.split('=')
                nested_lhs = nested_parts[0].strip()
                nested_rhs = nested_parts[1].strip()

                # Создаем новую переменную, чтобы сохранить значение rhs
                temp_var = '%' + str(i + 1)
                optimized_ir += f"{temp_var} = {nested_rhs}\n"

                # Заменяем двойное присвоение на новую переменную
                optimized_ir += f"{lhs} = {temp_var}\n"
                i += 1  # Пропускаем следующую строку, содержащую присвоение вложенной переменной
            else:
                optimized_ir += line + '\n'
        else:
            optimized_ir += line + '\n'

        i += 1

    return optimized_ir

def optimize_unused_variables(llvm_ir):
    optimized_ir = ""
    lines = llvm_ir.split('\n')
    num_lines = len(lines)
    variables = set()# Множество для хранения используемых переменных

    for line in lines:
        if line.startswith('%') and '=' in line:
            parts = line.split('=')
            lhs = parts[0].strip()
            rhs = parts[1].strip()

            # Проверяем, используется ли переменная в правой части
            if any(var in rhs for var in variables):
                variables.add(lhs)
                optimized_ir += line + '\n'
        else:
            optimized_ir += line + '\n'

    return optimized_ir

def optimize_constant_folding(llvm_ir):
    optimized_ir = ""
    lines = llvm_ir.split('\n')
    num_lines = len(lines)
    variables = {}  # Словарь для хранения значений константных выражений

    for line in lines:
        if line.startswith('%') and '=' in line:
            parts = line.split('=')
            lhs = parts[0].strip()
            rhs = parts[1].strip()

            # Проверяем, является ли rhs константным выражением
            if re.match(r'^(-?[0-9]+|true|false)$', rhs):
                value = eval(rhs)  # Вычисляем значение константы

                # Сохраняем значение в словаре variables
                variables[lhs] = value
                optimized_ir += f"{lhs} = {value}\n"
            else:
                # Проверяем, является ли rhs переменной с известным значением
                constant_vars = [var for var in variables if var in rhs]
                if constant_vars:
                    for var in constant_vars:
                        rhs = rhs.replace(var, str(variables[var]))

                    # Заменяем rhs на вычисленное константное выражение
                    optimized_ir += f"{lhs} = {rhs}\n"
                else:
                    optimized_ir += line + '\n'
        else:
            optimized_ir += line + '\n'

    return optimized_ir

def optimize_llvm_ir(llvm_ir):
    llvm.initialize()
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()

    target = llvm.Target.from_default_triple()
    target_machine = target.create_target_machine()
    mod = llvm.parse_assembly(llvm_ir)
    mod.verify()

    pmb = llvm.create_pass_manager_builder()
    pmb.opt_level = 1
    pm = llvm.create_module_pass_manager()
    pmb.populate(pm)
    pm.run(mod)

    return str(mod)



def run(llvm_ir):
    llvm.initialize()
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()

    target = llvm.Target.from_default_triple()
    target_machine = target.create_target_machine()
    mod = llvm.parse_assembly(llvm_ir)
    mod.verify()

    engine = llvm.create_mcjit_compiler(mod, target_machine)
    init_ptr = engine.get_function_address('__init')
    init_func = ctypes.CFUNCTYPE(None)(init_ptr)
    init_func()
    main_ptr = engine.get_function_address('main')
    main_func = ctypes.CFUNCTYPE(None)(main_ptr)
    main_func()


def measure_execution_time(func):
    start = time.time()
    func()
    print(f"Время выполнения программы: {time.time() - start} сек")

def main():
    if len(sys.argv) != 2:
        sys.stderr.write("Usage: python ./name_program.py filename\n")
        raise SystemExit(1)

    source = open(sys.argv[1]).read()

    Lexer.lexer.input(source)
    print("--------------------------------Токены---------------------------------------------")
    while True:
        tok = Lexer.lexer.token()
        if not tok:
            break
        print(tok)


    tree = build_tree(source)
    print("\n---------------------Абстрактное синтаксическое дерево---------------------")
    print(tree)
    print("\n---------------------Таблица символов--------------------------------------")
    tmp = getTable(tree)
    for i in tmp:
        print(f"{i} -- {tmp[i]}")

    block = Block()
    block.initname('Main')
    block = GenerateCode(block, tree, 'global', False, getTable(tree))
    print("\n---------------------Трехадресный код-------------------------------------")
    prTr(block, 1)
    llvm_code = compile_llvm(block)
    with open('Code.ll', 'wb') as f:
        f.write(llvm_code.encode('utf-8'))
        f.flush()

    print("\n---------------------Код в LLVM-------------------------------------------")
    print(llvm_code)
    print("\n---------------------Оптимизированный код----------------------------")
    optimized_code = optimize_unused_variables(llvm_code)
    optimized_code = optimize_double_assignment(optimized_code)
    optimized_code = optimize_constant_folding(optimized_code)
    optimized_llvm_code = optimize_llvm_ir(optimized_code)
    print(optimized_llvm_code)
    print("\n---------------------Результат-------------------------")
    measure_execution_time(lambda: run(llvm_code))

if __name__ == '__main__':
    main()