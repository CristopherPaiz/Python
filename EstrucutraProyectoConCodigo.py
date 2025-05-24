import os

# CONFIGURACIÓN DEL SCRIPT - EDITA ESTOS VALORES SEGÚN NECESITES
# Ruta de entrada (ya configurada con la ruta que proporcionaste)

# INPUT_PATH = r"C:\Users\crist\OneDrive\Documents\Progra\Github\NayeNailsBackend"
INPUT_PATH = r"C:\Users\crist\OneDrive\Documents\Progra\Github\NayeNailsBackend"
# Archivo de salida
OUTPUT_FILE = r"C:\Users\crist\OneDrive\Documents\Progra\zzzSalidaProyecto.txt"

# Lista de directorios a excluir
EXCLUDE_DIRS = [
    'node_modules',
    '.git',
    'dist',
    'build',
    'coverage',
    '.vscode',
    '.idea',
    'bin',
    'obj',
    '.github',
    '.next',
    'out',
    '__pycache__',
    '.nuxt',
    '.cache',
    'vendor',
    'bower_components',
    'tmp',
    'temp',
    'public',
    'static',
    'componentsSoftUI',
    'FEL',
    'Gestion',
    'Tiendas',
    'QueryManager',
    "Menu",
    "Regiones",
    "Remesas",
    'FormularioElectronico',
    "Plantilla-UI-v2"
]

# Lista de archivos (sin extensión) a excluir
EXCLUDE_FILES = [
    'package-lock',
    'yarn.lock',
    '.DS_Store',
    'thumbs',
    ".dockerignore",
    ".env",
    ".gitignore",
    "Dockerfile"
]

# Lista de extensiones a excluir
EXCLUDE_EXTENSIONS = [
    '.log',
    '.lock',
    '.gitignore',
    '.gitattributes',
    '.env',
    '.bak',
    '.tmp',
    '.swp',
    '.map',
    '.tsbuildinfo'
]

# Lista de combinaciones específicas archivo+extensión a excluir
EXCLUDE_FILE_EXTENSIONS = [
    'package-lock.json',
    'yarn.lock',
    '.npmrc',
    '.yarnrc',
    '.prettierrc',
    '.eslintrc.json',
    '.eslintrc.js',
    '.prettierignore',
    'README.md',
    'LICENSE',
    'CHANGELOG.md'
]

def generate_tree_and_code(path, output_file, exclude_dirs, exclude_files, exclude_extensions, exclude_file_extensions):
    """
    Generate a file tree and extract code from files recursively.

    Args:
        path: The root path to explore
        output_file: The file to save the output
        exclude_dirs: List of directory names to exclude
        exclude_files: List of file names (without extension) to exclude
        exclude_extensions: List of file extensions to exclude (with dot)
        exclude_file_extensions: List of specific file+extension combinations to exclude
    """
    # Convert the path to an absolute path
    root_path = os.path.abspath(path)

    # Open the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        # Generate tree structure
        f.write("File Tree Structure:\n")
        base_name = os.path.basename(root_path)
        f.write(base_name + "\n")
        generate_tree_recursive(root_path, f, "", exclude_dirs, exclude_files, exclude_extensions, exclude_file_extensions)

        f.write("\n\nFile Contents:\n\n")
        extract_code(root_path, f, exclude_dirs, exclude_files, exclude_extensions, exclude_file_extensions, root_path)

def generate_tree_recursive(path, file, prefix, exclude_dirs, exclude_files, exclude_extensions, exclude_file_extensions):
    """Generate a tree structure of the directory recursively"""
    try:
        items = sorted([item for item in os.listdir(path) if not should_exclude(item, path, exclude_dirs, exclude_files, exclude_extensions, exclude_file_extensions)])
    except Exception as e:
        file.write(f"{prefix}Error accessing directory: {str(e)}\n")
        return

    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        item_path = os.path.join(path, item)

        # Choose the correct prefix for this item
        if is_last:
            file.write(f"{prefix}└── {item}\n")
            new_prefix = prefix + "    "
        else:
            file.write(f"{prefix}├── {item}\n")
            new_prefix = prefix + "│   "

        # If it's a directory, recurse into it
        if os.path.isdir(item_path):
            generate_tree_recursive(item_path, file, new_prefix, exclude_dirs, exclude_files, exclude_extensions, exclude_file_extensions)

def extract_code(path, file, exclude_dirs, exclude_files, exclude_extensions, exclude_file_extensions, root_path):
    """Extract code from files recursively"""
    try:
        items = sorted(os.listdir(path))
    except Exception:
        return

    for item in items:
        if should_exclude(item, path, exclude_dirs, exclude_files, exclude_extensions, exclude_file_extensions):
            continue

        item_path = os.path.join(path, item)
        # Get relative path from root
        rel_path = os.path.relpath(item_path, root_path)
        # Convert to forward slashes and add leading slash
        formatted_path = '/' + rel_path.replace('\\', '/')

        if os.path.isdir(item_path):
            extract_code(item_path, file, exclude_dirs, exclude_files, exclude_extensions, exclude_file_extensions, root_path)
        else:
            try:
                with open(item_path, 'r', encoding='utf-8') as code_file:
                    content = code_file.read()

                file.write(f"Ruta: {formatted_path}\n")
                file.write("Code:\n")
                file.write(content)
                file.write("\n\n" + "-" * 10 + "\n\n")
            except Exception as e:
                file.write(f"Ruta: {formatted_path}\n")
                file.write(f"Error reading file: {str(e)}\n\n")
                file.write("-" * 10 + "\n\n")

def should_exclude(item, parent_path, exclude_dirs, exclude_files, exclude_extensions, exclude_file_extensions):
    """Check if an item should be excluded based on filters"""
    item_path = os.path.join(parent_path, item)

    # Check if it's a directory to exclude
    if os.path.isdir(item_path) and item in exclude_dirs:
        return True

    # For files, check against various exclusion criteria
    if os.path.isfile(item_path):
        filename, extension = os.path.splitext(item)

        # Check if the file name should be excluded
        if filename in exclude_files:
            return True

        # Check if the extension should be excluded
        if extension in exclude_extensions:
            return True

        # Check if the specific file+extension combination should be excluded
        if item in exclude_file_extensions:
            return True

    return False

def main():
    # Asegúrate de que las extensiones tengan un punto al inicio
    exclude_extensions = [ext if ext.startswith('.') else '.' + ext for ext in EXCLUDE_EXTENSIONS]

    print(f"Escaneando el directorio: {INPUT_PATH}")
    generate_tree_and_code(
        INPUT_PATH,
        OUTPUT_FILE,
        EXCLUDE_DIRS,
        EXCLUDE_FILES,
        exclude_extensions,
        EXCLUDE_FILE_EXTENSIONS
    )

    print(f"Escaneo completo. Resultado guardado en: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()