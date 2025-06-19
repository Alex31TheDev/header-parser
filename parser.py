import sys
from os import path
import argparse

import clang.cindex
from clang.cindex import TranslationUnit, CursorKind

severity = {
    0: 'IGNORED',
    1: 'NOTE',
    2: 'WARNING',
    3: 'ERROR',
    4: 'FATAL'
}

def print_diagnostics(tu):
    if not tu:
        return

    print('Diagnostics:\n---')
    for diag in tu.diagnostics:
        level = severity.get(diag.severity, 'UNKNOWN')
        file_path = diag.location.file.name if diag.location.file else '<unknown file>'
        line_num = diag.location.line if diag.location.line else 0

        message = f'[{level}] {diag.spelling} ({file_path}:{line_num})'

        if diag.severity >= 3:
            print(message, file=sys.stderr)
        else:
            print(message)

    print('---\n')

def clang_parse(header_path):
    index = clang.cindex.Index.create()
    tu = index.parse(header_path,
                     options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
    print_diagnostics(tu)

    return tu

def extract_defs(header_path, tu):
    typedefs = []
    functions = []
    structs = []
    enums = []
    macros = []

    for node in tu.cursor.get_children():
        node_file = node.location.file

        if node_file is not None and path.abspath(node_file.name) != path.abspath(header_path):
            continue

        if node.kind == CursorKind.TYPEDEF_DECL:
            typedef_name = node.spelling
            typedef_type = node.underlying_typedef_type.spelling or 'none'

            if not typedef_name.startswith('_') and not typedef_type.startswith('struct '):
                typedefs.append(f'typedef {typedef_type} {typedef_name};')

        elif node.kind == CursorKind.FUNCTION_DECL:
            func_name = node.spelling

            if not func_name.startswith('_'):
                ret_type = node.result_type.spelling or 'none'
                params = []

                for param in node.get_arguments():
                    param_type = param.type.spelling or 'none'
                    param_name = param.spelling or 'none'
                    params.append(f'{param_type} {param_name}')

                functions.append(f'{ret_type} {func_name}({', '.join(params)});')

        elif node.kind == CursorKind.STRUCT_DECL:
            struct_name = node.spelling

            if not struct_name.startswith('_'):
                struct_def = f'struct {struct_name} {{\n'

                for struct_field in node.get_children():
                    if struct_field.kind == CursorKind.FIELD_DECL:
                        field_type = struct_field.type.spelling or 'none'
                        field_name = struct_field.spelling or 'none'
                        struct_def += f'    {field_type} {field_name};\n'

                struct_def += '};'
                structs.append(struct_def)

        elif node.kind == CursorKind.ENUM_DECL:
            enum_name = node.spelling

            if not enum_name.startswith('_'):
                enum_def = f'{enum_name} {{\n'

                for enum_value in node.get_children():
                    if enum_value.kind == CursorKind.ENUM_CONSTANT_DECL:
                        enum_value_name = enum_value.spelling
                        enum_value_const = enum_value.enum_value

                        if enum_value_const is not None:
                            enum_def += f'    {enum_value_name} = {enum_value_const},\n'
                        else:
                            enum_def += f'    {enum_value_name},\n'

                enum_def = enum_def.rstrip(',\n') + '\n};'
                enums.append(enum_def)

        elif node.kind == CursorKind.MACRO_DEFINITION:
            macro_name = node.spelling

            if not macro_name.startswith('_'):
                tokens = [t.spelling for t in node.get_tokens()]

                macro_value = ' '.join(tokens[1:]) if len(tokens) > 1 else ''
                macros.append(f'#define {macro_name} {macro_value}'.strip())

    return typedefs, functions, structs, enums, macros

def process_header(header_path):
    if not path.isfile(header_path):
        print(f"ERROR: File '{header_path}' not found", file=sys.stderr)
        sys.exit(1)

    tu = clang_parse(header_path)
    typedefs, functions, structs, enums, macros = extract_defs(header_path, tu)

    sections = [
        ('Typedefs', typedefs),
        ('Functions', functions),
        ('Structs', structs),
        ('Enums', enums),
        ('Macros', macros),
    ]
    output = []

    for title, items in sections:
        output.append(f'{title}:\n---')
        output.extend(items)
        output.append('---\n')

    return '\n'.join(output)

def parse_args():
    parser = argparse.ArgumentParser(description='Parse C header for definitions')
    parser.add_argument('header', help='C header path')
    parser.add_argument('--clang-path', help='Custom path to the Clang library (optional)', default=None)
    parser.add_argument('--out', help='Output file path (optional)', default=None)

    return parser.parse_args()

def main():
    args = parse_args()

    try:
        if args.clang_path:
            if path.isfile(args.clang_path):
                clang.cindex.Config.set_library_file(args.clang_path)
            else:
                clang.cindex.Config.set_library_path(args.clang_path)
    except clang.cindex.LibclangError as err:
        print(f'ERROR: Failed to load libclang: {err}', file=sys.stderr)
        print('Try setting --clang-path to the folder or full path of the libclang shared library.')
        sys.exit(1)
    try:
        output = process_header(args.header)
    except Exception as err:
        print(f'ERROR: {err}', file=sys.stderr)
        sys.exit(1)

    if args.out:
        with open(args.out, 'w') as f:
            f.write(output)
    else:
        print(output)

if __name__ == '__main__':
    main()