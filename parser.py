import clang.cindex
import argparse
import os
import sys

def extract_defs(header_file):
    index = clang.cindex.Index.create()
    translation_unit = index.parse(header_file, options=clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)

    typedefs = []
    functions = []
    structs = []
    enums = []
    macros = []

    for node in translation_unit.cursor.get_children():
        node_file = node.location.file
        if node_file is not None and os.path.basename(node_file.name) != header_file:
            continue

        if node.kind == clang.cindex.CursorKind.TYPEDEF_DECL:
            typedef_name = node.spelling
            underlying_type = node.underlying_typedef_type.spelling or 'none'

            if not typedef_name.startswith('_') and not underlying_type.startswith('struct '):
                typedefs.append(f'typedef {underlying_type} {typedef_name};')

        elif node.kind == clang.cindex.CursorKind.FUNCTION_DECL:
            function_name = node.spelling
            if not function_name.startswith('_'):
                return_type = node.result_type.spelling or 'none'

                params = []
                for param in node.get_arguments():
                    param_type = param.type.spelling or 'none'
                    param_name = param.spelling or 'none'
                    params.append(f'{param_type} {param_name}')

                formatted_function = f'{return_type} {function_name}({", ".join(params)});'
                functions.append(formatted_function)

        elif node.kind == clang.cindex.CursorKind.STRUCT_DECL:
            struct_name = node.spelling
            if not struct_name.startswith('_'):
                struct_def = f'struct {struct_name} {{\n'

                for struct_field in node.get_children():
                    if struct_field.kind == clang.cindex.CursorKind.FIELD_DECL:
                        field_type = struct_field.type.spelling or 'none'
                        field_name = struct_field.spelling or 'none'
                        struct_def += f'    {field_type} {field_name};\n'

                struct_def += '};'
                structs.append(struct_def)

        elif node.kind == clang.cindex.CursorKind.ENUM_DECL:
            enum_name = node.spelling
            if not enum_name.startswith('_'):
                enum_def = f'{enum_name} {{\n'

                for enum_value in node.get_children():
                    if enum_value.kind == clang.cindex.CursorKind.ENUM_CONSTANT_DECL:
                        enum_value_name = enum_value.spelling
                        enum_value_const = enum_value.enum_value

                        if enum_value_const is not None:
                            enum_def += f'    {enum_value_name} = {enum_value_const},\n'
                        else:
                            enum_def += f'    {enum_value_name},\n'

                enum_def = enum_def.rstrip(',\n') + '\n};'
                enums.append(enum_def)

        elif node.kind == clang.cindex.CursorKind.MACRO_DEFINITION:
            macro_name = node.spelling
            if not macro_name.startswith('_'):
                tokens = [t.spelling for t in node.get_tokens()]
                macro_value = ' '.join(tokens[1:]) if len(tokens) > 1 else ''
                macros.append(f'#define {macro_name} {macro_value}'.strip())

    return typedefs, functions, structs, enums, macros

def parse_args():
    parser = argparse.ArgumentParser(description='Parse C header for definitions')
    parser.add_argument('header', help='C header path')
    parser.add_argument('--clang-path', help='Custom path to the Clang library (optional)', default=None)
    parser.add_argument('--out', help='Output file path (optional)', default=None)

    return parser.parse_args()

def process_header(header_path):
    typedefs, functions, structs, enums, macros = extract_defs(header_path)

    sections = [
        ('Typedefs', typedefs),
        ('Functions', functions),
        ('Structs', structs),
        ('Enums', enums),
        ('Macros', macros),
    ]

    output = []

    for title, items in sections:
        output.append(f'{title}:\n')
        output.extend(items)
        output.append('')

    return '\n'.join(output)

def main():
    args = parse_args()

    try:
        if args.clang_path:
            if os.path.isfile(args.clang_path):
                clang.cindex.Config.set_library_file(args.clang_path)
            else:
                clang.cindex.Config.set_library_path(args.clang_path)

        output = process_header(args.header)

    except clang.cindex.LibclangError as e:
        print('[ERROR] libclang could not be loaded.', file=sys.stderr)
        print('Try setting --clang-path to the folder or full path of the libclang shared library.')
        sys.exit(1)

    if args.out:
        with open(args.out, 'w') as f:
            f.write(output)
    else:
        print(output)

if __name__ == '__main__':
    main()