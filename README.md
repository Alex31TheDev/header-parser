# header-parser

Python script for parsing a C header and extracting typedef, function, struct, enum and macro definitions.

# Usage

Run `python parser.py --help` to view the command line help:

    usage: parser.py [-h] [--clang-path CLANG_PATH] [--out OUT] header

    Parse C header for definitions.

    positional arguments:
      header                C header path

    options:
      -h, --help            show this help message and exit
      --clang-path CLANG_PATH
                            Custom path to the Clang library (optional)
      --out OUT             Output file path (optional)

# Dependencies

**Clang (libclang)** must be installed and available on your system.

-   **Debian/Ubuntu:**
    ```bash
    sudo apt-get install clang libclang-dev
    ```
-   **macOS (Homebrew):**
    ```bash
    brew install llvm
    ```
-   **Windows:**
    1. Download and run the LLVM installer from https://llvm.org/releases/.
    2. Ensure the LLVM `bin` directory (`C:\Program Files\LLVM\bin`) is on your `PATH`.
